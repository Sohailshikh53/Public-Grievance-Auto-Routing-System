"""
Analytics and Evaluation API Routes
Public Grievance Auto-Routing System
"""

import json
import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from backend.database.db import get_db
from backend.services.intelligence_service import build_issue_intelligence

router = APIRouter(prefix="/api", tags=["analytics"])

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
EVAL_FILE = os.path.join(MODELS_DIR, "model_evaluation.json")

@router.get("/analytics/summary")
def get_summary_metrics(city: str | None = Query(None)):
    """Calculates live metrics and KPI counters directly from the database."""
    conn = get_db()
    cursor = conn.cursor()
    
    city_clause = " AND city = ?" if city else ""
    city_params = (city,) if city else ()

    # Total counts
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE 1=1" + city_clause + ";", city_params)
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE routing_type = 'AUTO'" + city_clause + ";", city_params)
    auto_routed = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE routing_type = 'MANUAL_REVIEW' AND status = 'RECEIVED'" + city_clause + ";", city_params)
    manual_review_pending = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'IN_PROGRESS'" + city_clause + ";", city_params)
    in_progress = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'RESOLVED'" + city_clause + ";", city_params)
    resolved = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE is_escalated = 1 AND status NOT IN ('RESOLVED', 'REJECTED')" + city_clause + ";", city_params)
    escalated_active = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE escalation_level = 1 AND status NOT IN ('RESOLVED', 'REJECTED')" + city_clause + ";", city_params)
    level1_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE escalation_level = 2 AND status NOT IN ('RESOLVED', 'REJECTED')" + city_clause + ";", city_params)
    level2_count = cursor.fetchone()[0]
    
    # Department-wise breakdown
    cursor.execute("""
    SELECT 
        d.code, d.name, d.sla_default_hours,
        COUNT(c.id) AS total_count,
        SUM(CASE WHEN c.status = 'IN_PROGRESS' THEN 1 ELSE 0 END) AS in_progress_count,
        SUM(CASE WHEN c.status = 'RESOLVED' THEN 1 ELSE 0 END) AS resolved_count,
        SUM(CASE WHEN c.is_escalated = 1 AND c.status NOT IN ('RESOLVED', 'REJECTED') THEN 1 ELSE 0 END) AS escalated_count
    FROM departments d
    LEFT JOIN complaints c ON d.code = c.assigned_department AND (? IS NULL OR c.city = ?)
    GROUP BY d.code, d.name, d.sla_default_hours
    ORDER BY total_count DESC;
    """, (city, city))
    dept_rows = [dict(r) for r in cursor.fetchall()]
    
    # Ward-wise breakdown
    cursor.execute("""
    SELECT ward_number, COUNT(*) as count,
           SUM(CASE WHEN is_escalated = 1 THEN 1 ELSE 0 END) as escalated_count
    FROM complaints
    WHERE (? IS NULL OR city = ?)
    GROUP BY ward_number
    ORDER BY count DESC;
    """, (city, city))
    ward_rows = [dict(r) for r in cursor.fetchall()]
    
    # SLA Compliance rate: of all resolved complaints, how many were resolved on or before sla_due_at
    cursor.execute("""
    SELECT COUNT(*) FROM complaints 
    WHERE status = 'RESOLVED' AND resolved_at <= sla_due_at
      AND (? IS NULL OR city = ?);
    """, (city, city))
    resolved_within_sla = cursor.fetchone()[0]
    sla_compliance_rate = round((resolved_within_sla / resolved * 100), 1) if resolved > 0 else 100.0
    
    cursor.execute("""
    SELECT city, COUNT(*) AS total_count,
           SUM(CASE WHEN status = 'RESOLVED' THEN 1 ELSE 0 END) AS resolved_count,
           SUM(CASE WHEN is_escalated = 1 AND status NOT IN ('RESOLVED','REJECTED') THEN 1 ELSE 0 END) AS escalated_count,
           SUM(CASE WHEN routing_type = 'MANUAL_REVIEW' AND status = 'RECEIVED' THEN 1 ELSE 0 END) AS triage_count
    FROM complaints GROUP BY city ORDER BY total_count DESC;
    """)
    city_rows = [dict(row) for row in cursor.fetchall()]

    conn.close()
    
    return {
        "total_complaints": total,
        "auto_routed_count": auto_routed,
        "auto_routed_percentage": round((auto_routed / total * 100), 1) if total > 0 else 0,
        "manual_review_pending": manual_review_pending,
        "in_progress_count": in_progress,
        "resolved_count": resolved,
        "escalated_active": escalated_active,
        "level1_escalations": level1_count,
        "level2_escalations": level2_count,
        "sla_compliance_rate": sla_compliance_rate,
        "department_breakdown": dept_rows,
        "ward_breakdown": ward_rows
        ,"city_breakdown": city_rows,
        "scope_city": city,
    }

@router.get("/analytics/model")
def get_model_evaluation():
    """Returns actual measured ML model performance metrics, classification report, and confusion matrix."""
    if not os.path.exists(EVAL_FILE):
        raise HTTPException(status_code=404, detail="Model evaluation file not found")
        
    with open(EVAL_FILE, "r") as f:
        data = json.load(f)
        
    return data

@router.get("/analytics/intelligence")
def get_issue_intelligence(city: str | None = Query(None), limit: int = Query(8, ge=3, le=20)):
    """Rank top issue clusters and operationally critical grievances."""
    return build_issue_intelligence(city=city, limit=limit)

@router.get("/departments")
def list_departments():
    """List all registered civic departments with their SLA specifications."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM departments ORDER BY id ASC;")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
