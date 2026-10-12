"""
Complaints API Routes
Public Grievance Auto-Routing System
"""

import random
import re
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.database.db import get_db
from backend.services.nlp_service import classifier
from backend.config import CONFIDENCE_THRESHOLD, TRACKING_YEAR
from backend.config import MAHARASHTRA_CITIES

router = APIRouter(prefix="/api/complaints", tags=["complaints"])

class ComplaintSubmitRequest(BaseModel):
    citizen_name: str = Field(..., min_length=2)
    citizen_phone: str = Field(..., min_length=8)
    citizen_email: str = Field(...)
    ward_number: str = Field(...)
    city: str = Field("Pune")
    locality: str = Field(..., min_length=3)
    complaint_text: str = Field(..., min_length=10)
    language: Optional[str] = Field(None, max_length=40)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

class PredictRequest(BaseModel):
    text: str = Field(..., min_length=5)

class StatusUpdateRequest(BaseModel):
    status: Literal["RECEIVED", "ROUTED", "IN_PROGRESS", "RESOLVED", "REJECTED"]
    officer_name: Optional[str] = None
    notes: Optional[str] = None

class TriageActionRequest(BaseModel):
    assigned_department: str = Field(...)
    operator_name: Optional[str] = "Triage Desk Operator"
    notes: Optional[str] = "Department confirmed upon manual triage review."

class ReassignRequest(BaseModel):
    new_department: str = Field(...)
    officer_name: Optional[str] = "Department Officer"
    reason: str = Field(..., min_length=5)

class CitizenFeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    resolution_verified: bool = True
    comments: Optional[str] = Field(None, max_length=1000)

@router.post("/predict")
def predict_grievance(req: PredictRequest):
    """Real-time NLP prediction test endpoint without saving to database."""
    res = classifier.predict(req.text)
    return res

@router.post("/submit")
def submit_complaint(req: ComplaintSubmitRequest):
    """
    Submits a new citizen complaint.
    Executes automated text classification, checks confidence threshold,
    determines routing path (AUTO vs MANUAL_REVIEW), sets SLA, and records audit trail.
    """
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    if req.city not in MAHARASHTRA_CITIES:
        conn.close()
        raise HTTPException(status_code=400, detail="Unsupported Maharashtra city")
    
    # 1. Run NLP Classification
    nlp_res = classifier.predict(req.complaint_text)
    pred_dept = nlp_res["predicted_department"]
    conf_score = nlp_res["confidence_score"]
    routing_type = nlp_res["routing_type"]
    urgency = nlp_res["urgency"]
    
    # 2. Determine assignment and SLA
    if routing_type == "AUTO":
        assigned_dept = pred_dept
        initial_status = "ROUTED"
    else:
        assigned_dept = "unassigned"
        initial_status = "RECEIVED"
        
    # Get SLA hours for department
    cursor.execute("SELECT sla_default_hours FROM departments WHERE code = ?;", (pred_dept,))
    dept_row = cursor.fetchone()
    sla_hours = dept_row["sla_default_hours"] if dept_row else 48
    sla_due_at = (now + timedelta(hours=sla_hours)).isoformat()
    
    # 3. Generate unique sequential tracking token
    cursor.execute("SELECT MAX(id) FROM complaints;")
    max_id_row = cursor.fetchone()
    next_id = (max_id_row[0] or 1000) + 1
    tracking_token = f"GRV-{TRACKING_YEAR}-{next_id:05d}"
    
    # 4. Insert complaint record
    cursor.execute("""
    INSERT INTO complaints (
        tracking_token, citizen_name, citizen_phone, citizen_email,
        ward_number, locality, complaint_text, urgency,
        predicted_department, confidence_score, routing_type,
        assigned_department, status, sla_deadline_hours, sla_due_at,
        is_escalated, escalation_level, escalated_at, assigned_officer,
        resolution_notes, resolved_at, language, latitude, longitude, city, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, NULL, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?);
    """, (
        tracking_token, req.citizen_name.strip(), req.citizen_phone.strip(), req.citizen_email.strip(),
        req.ward_number.strip(), req.locality.strip(), req.complaint_text.strip(), urgency,
        pred_dept, conf_score, routing_type, assigned_dept, initial_status,
        sla_hours, sla_due_at, req.language or nlp_res.get("detected_language", "English"),
        req.latitude, req.longitude, req.city, now_iso, now_iso
    ))
    complaint_id = cursor.lastrowid
    
    # 5. Insert initial audit logs
    cursor.execute("""
    INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (
        complaint_id, "LODGED", None, "RECEIVED", "Citizen Web Portal",
        f"Grievance lodged by {req.citizen_name} from {req.locality} ({req.ward_number}).",
        now_iso
    ))
    
    if routing_type == "AUTO":
        cursor.execute("""
        INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            complaint_id, "AUTO_ROUTED", "RECEIVED", "ROUTED", "NLP Classifier Engine v1.0",
            f"Auto-routed directly to {nlp_res['department_name']} with {round(conf_score * 100, 1)}% confidence score.",
            (now + timedelta(seconds=1)).isoformat()
        ))
    else:
        cursor.execute("""
        INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            complaint_id, "SENT_TO_MANUAL_REVIEW", "RECEIVED", "RECEIVED", "NLP Classifier Engine v1.0",
            f"Confidence score ({round(conf_score * 100, 1)}%) below {round(CONFIDENCE_THRESHOLD * 100)}% threshold. Diverted to Manual Review Triage Desk.",
            (now + timedelta(seconds=1)).isoformat()
        ))
        
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "complaint_id": complaint_id,
        "tracking_token": tracking_token,
        "routing_type": routing_type,
        "assigned_department": assigned_dept,
        "department_name": nlp_res["department_name"],
        "confidence_score": conf_score,
        "urgency": urgency,
        "sla_deadline_hours": sla_hours,
        "sla_due_at": sla_due_at,
        "probabilities": nlp_res["probabilities"],
        "reasoning": nlp_res["reasoning"]
    }

@router.get("/track/{token}")
def track_complaint(token: str):
    """Public tracking endpoint by Tracking Token (e.g. GRV-2026-01001)."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT c.*, d.name AS department_name, d.head_officer, d.contact_email AS dept_email, d.contact_phone AS dept_phone
    FROM complaints c
    LEFT JOIN departments d ON c.assigned_department = d.code
    WHERE c.tracking_token = ?;
    """, (token.strip(),))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No grievance found with tracking token '{token}'.")
        
    complaint = dict(row)
    
    # Fetch audit timeline
    cursor.execute("""
    SELECT action, from_status, to_status, performed_by, notes, timestamp
    FROM audit_logs
    WHERE complaint_id = ?
    ORDER BY id ASC;
    """, (complaint["id"],))
    audit_rows = [dict(r) for r in cursor.fetchall()]
    complaint["audit_logs"] = audit_rows

    cursor.execute("""
    SELECT rating, resolution_verified, comments, created_at
    FROM citizen_feedback WHERE complaint_id = ? ORDER BY id DESC LIMIT 1;
    """, (complaint["id"],))
    feedback = cursor.fetchone()
    complaint["citizen_feedback"] = dict(feedback) if feedback else None
    
    conn.close()
    return complaint

@router.get("")
def list_complaints(
    status: Optional[str] = None,
    department: Optional[str] = None,
    routing_type: Optional[str] = None,
    escalated: Optional[int] = None,
    ward: Optional[str] = None,
    city: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0
):
    """Filtered list of complaints with search and sorting."""
    conn = get_db()
    cursor = conn.cursor()
    
    query = """
    SELECT c.id, c.tracking_token, c.citizen_name, c.ward_number, c.locality,
           c.complaint_text, c.urgency, c.predicted_department, c.confidence_score,
           c.routing_type, c.assigned_department, c.status, c.sla_deadline_hours,
           c.sla_due_at, c.is_escalated, c.escalation_level, c.assigned_officer,
           c.resolved_at, c.created_at, c.updated_at, c.language, c.city,
           d.name AS department_name, d.head_officer
    FROM complaints c
    LEFT JOIN departments d ON c.assigned_department = d.code
    WHERE 1=1
    """
    params = []
    
    if status and status != "ALL":
        query += " AND c.status = ?"
        params.append(status)
    if department and department != "ALL":
        query += " AND c.assigned_department = ?"
        params.append(department)
    if routing_type and routing_type != "ALL":
        query += " AND c.routing_type = ?"
        params.append(routing_type)
    if escalated is not None:
        query += " AND c.is_escalated = ?"
        params.append(escalated)
    if ward and ward != "ALL":
        query += " AND c.ward_number = ?"
        params.append(ward)
    if city and city != "ALL":
        query += " AND c.city = ?"
        params.append(city)
    if search:
        search_term = f"%{search.strip()}%"
        query += " AND (c.tracking_token LIKE ? OR c.complaint_text LIKE ? OR c.citizen_name LIKE ? OR c.locality LIKE ?)"
        params.extend([search_term, search_term, search_term, search_term])
        
    query += " ORDER BY c.id DESC LIMIT ? OFFSET ?;"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"count": len(rows), "complaints": rows}

@router.get("/similar/search")
def find_similar_complaints(
    text: str = Query(..., min_length=10),
    ward: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = Query(5, ge=1, le=10)
):
    """Find likely duplicate grievances using lexical overlap and ward context."""
    stopwords = {"the", "is", "a", "an", "to", "of", "and", "in", "near", "for", "from", "my", "our", "there"}
    tokens = {token for token in re.findall(r"\w+", text.lower()) if len(token) > 2 and token not in stopwords}
    if not tokens:
        return {"matches": []}

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, tracking_token, ward_number, city, locality, complaint_text, assigned_department, status
    FROM complaints WHERE status NOT IN ('RESOLVED', 'REJECTED') ORDER BY id DESC LIMIT 300;
    """)
    matches = []
    for row in cursor.fetchall():
        if city and row["city"] != city:
            continue
        other_tokens = {token for token in re.findall(r"\w+", row["complaint_text"].lower()) if len(token) > 2 and token not in stopwords}
        union = tokens | other_tokens
        score = len(tokens & other_tokens) / len(union) if union else 0
        if ward and row["ward_number"] == ward:
            score = min(1.0, score + 0.12)
        if score >= 0.22:
            matches.append({
                "tracking_token": row["tracking_token"],
                "ward_number": row["ward_number"],
                "city": row["city"],
                "locality": row["locality"],
                "department": row["assigned_department"],
                "status": row["status"],
                "similarity": round(score, 3),
                "summary": row["complaint_text"][:160],
            })
    conn.close()
    matches.sort(key=lambda item: item["similarity"], reverse=True)
    return {"matches": matches[:limit]}

@router.post("/track/{token}/feedback")
def submit_citizen_feedback(token: str, req: CitizenFeedbackRequest):
    """Verify a resolution or reopen it when the reported issue persists."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM complaints WHERE tracking_token = ?;", (token.strip(),))
    complaint = cursor.fetchone()
    if not complaint:
        conn.close()
        raise HTTPException(status_code=404, detail="Complaint not found")
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
    INSERT INTO citizen_feedback (complaint_id, rating, resolution_verified, comments, created_at)
    VALUES (?, ?, ?, ?, ?);
    """, (complaint["id"], req.rating, int(req.resolution_verified), req.comments, now_iso))

    reopened = not req.resolution_verified and complaint["status"] == "RESOLVED"
    if reopened:
        cursor.execute("""
        UPDATE complaints SET status = 'IN_PROGRESS', resolved_at = NULL, updated_at = ? WHERE id = ?;
        """, (now_iso, complaint["id"]))
        cursor.execute("""
        INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
        VALUES (?, 'REOPENED_BY_CITIZEN', 'RESOLVED', 'IN_PROGRESS', 'Citizen Verification', ?, ?);
        """, (complaint["id"], req.comments or "Citizen reported that the issue remains unresolved.", now_iso))
    else:
        cursor.execute("""
        INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
        VALUES (?, 'CITIZEN_FEEDBACK', ?, ?, 'Citizen Verification', ?, ?);
        """, (complaint["id"], complaint["status"], complaint["status"], f"Citizen rating: {req.rating}/5. {req.comments or ''}".strip(), now_iso))
    conn.commit()
    conn.close()
    return {"success": True, "reopened": reopened}

@router.get("/{complaint_id}")
def get_complaint_detail(complaint_id: int):
    """Single complaint detail with full timeline history."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT c.*, d.name AS department_name, d.head_officer, d.contact_email AS dept_email, d.contact_phone AS dept_phone
    FROM complaints c
    LEFT JOIN departments d ON c.assigned_department = d.code
    WHERE c.id = ?;
    """, (complaint_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    complaint = dict(row)
    
    cursor.execute("""
    SELECT action, from_status, to_status, performed_by, notes, timestamp
    FROM audit_logs
    WHERE complaint_id = ?
    ORDER BY id ASC;
    """, (complaint_id,))
    complaint["audit_logs"] = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return complaint

@router.patch("/{complaint_id}/status")
def update_complaint_status(complaint_id: int, req: StatusUpdateRequest):
    """Update complaint status by department officer (e.g., In Progress, Resolved)."""
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("SELECT status, assigned_department FROM complaints WHERE id = ?;", (complaint_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    old_status = existing["status"]
    new_status = req.status.upper()

    allowed_transitions = {
        "RECEIVED": {"ROUTED", "REJECTED"},
        "ROUTED": {"IN_PROGRESS", "REJECTED"},
        "IN_PROGRESS": {"ROUTED", "RESOLVED", "REJECTED"},
        "RESOLVED": {"IN_PROGRESS"},
        "REJECTED": {"RECEIVED"},
    }
    if new_status != old_status and new_status not in allowed_transitions.get(old_status, set()):
        conn.close()
        raise HTTPException(status_code=409, detail=f"Invalid status transition from {old_status} to {new_status}")
    
    resolved_at = now_iso if new_status == "RESOLVED" else None
    
    cursor.execute("""
    UPDATE complaints
    SET status = ?,
        assigned_officer = COALESCE(?, assigned_officer),
        resolution_notes = COALESCE(?, resolution_notes),
        resolved_at = COALESCE(?, resolved_at),
        updated_at = ?
    WHERE id = ?;
    """, (new_status, req.officer_name, req.notes, resolved_at, now_iso, complaint_id))
    
    cursor.execute("""
    INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (
        complaint_id,
        "STATUS_UPDATED",
        old_status,
        new_status,
        req.officer_name or "Department Officer",
        req.notes or f"Status transitioned from {old_status} to {new_status}.",
        now_iso
    ))
    
    conn.commit()
    conn.close()
    return {"success": True, "old_status": old_status, "new_status": new_status}

@router.post("/{complaint_id}/triage")
def triage_manual_review(complaint_id: int, req: TriageActionRequest):
    """Manual review triage desk operator assigns department to low-confidence grievance."""
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    cursor.execute("SELECT status, routing_type, predicted_department FROM complaints WHERE id = ?;", (complaint_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Get department SLA
    cursor.execute("SELECT sla_default_hours, name FROM departments WHERE code = ?;", (req.assigned_department,))
    dept_row = cursor.fetchone()
    if not dept_row:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid department code")
        
    sla_hours = dept_row["sla_default_hours"]
    sla_due_at = (now + timedelta(hours=sla_hours)).isoformat()
    dept_name = dept_row["name"]
    
    cursor.execute("""
    UPDATE complaints
    SET assigned_department = ?,
        routing_type = 'MANUAL_CONFIRMED',
        status = 'ROUTED',
        sla_deadline_hours = ?,
        sla_due_at = ?,
        updated_at = ?
    WHERE id = ?;
    """, (req.assigned_department, sla_hours, sla_due_at, now_iso, complaint_id))
    
    cursor.execute("""
    INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (
        complaint_id,
        "MANUALLY_TRIAGED",
        "RECEIVED",
        "ROUTED",
        req.operator_name or "Triage Desk Operator",
        f"Manually assigned to {dept_name}. Operator remarks: {req.notes}",
        now_iso
    ))

    if existing["predicted_department"] != req.assigned_department:
        cursor.execute("""
        INSERT INTO model_feedback (complaint_id, predicted_department, corrected_department, correction_source, notes, created_at)
        VALUES (?, ?, ?, 'MANUAL_TRIAGE', ?, ?);
        """, (complaint_id, existing["predicted_department"], req.assigned_department, req.notes, now_iso))
    
    conn.commit()
    conn.close()
    return {"success": True, "assigned_department": req.assigned_department, "status": "ROUTED"}

@router.post("/{complaint_id}/reassign")
def reassign_department(complaint_id: int, req: ReassignRequest):
    """Reroute a misrouted complaint to the correct department."""
    conn = get_db()
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    
    cursor.execute("SELECT assigned_department, predicted_department, status FROM complaints WHERE id = ?;", (complaint_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    old_dept = existing["assigned_department"]
    
    cursor.execute("SELECT name, sla_default_hours FROM departments WHERE code = ?;", (req.new_department,))
    new_dept_row = cursor.fetchone()
    if not new_dept_row:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid target department code")
        
    new_sla_due_at = (datetime.now(timezone.utc) + timedelta(hours=new_dept_row["sla_default_hours"])).isoformat()
    cursor.execute("""
    UPDATE complaints
    SET assigned_department = ?,
        status = 'ROUTED',
        sla_deadline_hours = ?,
        sla_due_at = ?,
        is_escalated = 0,
        escalation_level = 0,
        updated_at = ?
    WHERE id = ?;
    """, (req.new_department, new_dept_row["sla_default_hours"], new_sla_due_at, now_iso, complaint_id))
    
    cursor.execute("""
    INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (
        complaint_id,
        "DEPARTMENT_REASSIGNED",
        existing["status"],
        "ROUTED",
        req.officer_name,
        f"Transferred from {old_dept} to {new_dept_row['name']}. Reason: {req.reason}",
        now_iso
    ))

    cursor.execute("""
    INSERT INTO model_feedback (complaint_id, predicted_department, corrected_department, correction_source, notes, created_at)
    VALUES (?, ?, ?, 'DEPARTMENT_REASSIGNMENT', ?, ?);
    """, (complaint_id, existing["predicted_department"], req.new_department, req.reason, now_iso))
    
    conn.commit()
    conn.close()
    return {"success": True, "old_department": old_dept, "new_department": req.new_department}
