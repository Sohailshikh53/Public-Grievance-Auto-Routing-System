"""
SLA Tracking and Auto-Escalation Engine
Public Grievance Auto-Routing System
"""

from datetime import datetime, timezone
from backend.database.db import get_db

def evaluate_sla_and_escalate():
    """
    Checks all non-resolved complaints against their SLA deadlines.
    Escalates overdue complaints and logs audit records.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    cursor.execute("""
    SELECT id, tracking_token, assigned_department, status, sla_due_at,
           is_escalated, escalation_level, sla_deadline_hours
    FROM complaints
    WHERE status NOT IN ('RESOLVED', 'REJECTED');
    """)
    rows = cursor.fetchall()
    
    escalated_count = 0
    updated_records = []
    
    for row in rows:
        c_id = row["id"]
        token = row["tracking_token"]
        dept = row["assigned_department"]
        status = row["status"]
        sla_due_str = row["sla_due_at"]
        current_is_esc = row["is_escalated"]
        current_level = row["escalation_level"]
        sla_hours = row["sla_deadline_hours"]
        
        try:
            # Parse ISO string
            due_dt = datetime.fromisoformat(sla_due_str)
            if due_dt.tzinfo is None:
                due_dt = due_dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
            
        if now > due_dt:
            overdue_hours = (now - due_dt).total_seconds() / 3600
            new_level = 2 if overdue_hours >= 24 else 1
            
            # Check if escalation level increased or if it wasn't escalated yet
            if current_is_esc == 0 or new_level > current_level:
                cursor.execute("""
                UPDATE complaints
                SET is_escalated = 1,
                    escalation_level = ?,
                    escalated_at = ?,
                    updated_at = ?
                WHERE id = ?;
                """, (new_level, now_iso, now_iso, c_id))
                
                target_authority = (
                    "Municipal Commissioner & Grievance Cell Director"
                    if new_level == 2
                    else "Superintending / Executive Engineer"
                )
                
                cursor.execute("""
                INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    c_id,
                    f"AUTO_ESCALATED_L{new_level}",
                    status,
                    status,
                    "Automated SLA Daemon",
                    f"SLA deadline breached by {round(overdue_hours, 1)} hours. Auto-escalated to Level {new_level} ({target_authority}).",
                    now_iso
                ))
                
                escalated_count += 1
                updated_records.append({
                    "tracking_token": token,
                    "department": dept,
                    "overdue_hours": round(overdue_hours, 1),
                    "new_level": new_level
                })
                
    conn.commit()
    conn.close()
    
    return {
        "checked_at": now_iso,
        "total_active_checked": len(rows),
        "newly_escalated": escalated_count,
        "escalations": updated_records
    }
