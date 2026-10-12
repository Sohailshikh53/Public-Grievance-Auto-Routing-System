"""
Seed initial departments and realistic complaint records
Public Grievance Auto-Routing System
"""

import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from backend.database.db import get_db, init_db
from backend.config import CONFIDENCE_THRESHOLD, MAHARASHTRA_CITIES

DEPARTMENTS = [
    {
        "code": "roads",
        "name": "Roads & Footpaths",
        "description": "Maintenance of asphalt roads, potholes, pedestrian sidewalks, dividers, and road markings.",
        "head_officer": "Er. Vikram Deshmukh (Superintending Engineer)",
        "contact_email": "roads.redressal@mc.gov.in",
        "contact_phone": "+91-20-25501011",
        "sla_default_hours": 48,
        "escalation_hours": 24,
        "active_staff_count": 28
    },
    {
        "code": "water_supply",
        "name": "Water Supply & Pipelines",
        "description": "Drinking water distribution, pipeline leakages, water contamination, tanker dispatch, and pressure issues.",
        "head_officer": "Er. S. R. Kulkarni (Chief Water Works Engineer)",
        "contact_email": "waterworks.support@mc.gov.in",
        "contact_phone": "+91-20-25501022",
        "sla_default_hours": 36,
        "escalation_hours": 18,
        "active_staff_count": 34
    },
    {
        "code": "electricity",
        "name": "Electricity & Streetlighting",
        "description": "Streetlight repairs, hanging live cables, transformer faults, pole hazards, and public lighting.",
        "head_officer": "Er. Anjali Mehra (Executive Electrical Engineer)",
        "contact_email": "electricity.cell@mc.gov.in",
        "contact_phone": "+91-20-25501033",
        "sla_default_hours": 24,
        "escalation_hours": 12,
        "active_staff_count": 22
    },
    {
        "code": "sanitation",
        "name": "Solid Waste & Sanitation",
        "description": "Garbage clearing, community bin emptying, street sweeping, dead animal disposal, and open dumping.",
        "head_officer": "Dr. Pradeep Patil (Chief Sanitation Officer)",
        "contact_email": "swm.grievance@mc.gov.in",
        "contact_phone": "+91-20-25501044",
        "sla_default_hours": 24,
        "escalation_hours": 12,
        "active_staff_count": 45
    },
    {
        "code": "drainage",
        "name": "Drainage & Sewerage",
        "description": "Underground sewer chokes, stormwater drainage blockages, missing manhole covers, and sewage overflow.",
        "head_officer": "Er. Nitin Shinde (Executive Drainage Engineer)",
        "contact_email": "drainage.cell@mc.gov.in",
        "contact_phone": "+91-20-25501055",
        "sla_default_hours": 36,
        "escalation_hours": 18,
        "active_staff_count": 26
    },
    {
        "code": "public_health",
        "name": "Public Health & Pest Control",
        "description": "Vector control fogging, dengue/malaria outbreak mitigation, stray dog control, and hygienic sanitation.",
        "head_officer": "Dr. Meenakshi Joshi (District Health Officer)",
        "contact_email": "publichealth.officer@mc.gov.in",
        "contact_phone": "+91-20-25501066",
        "sla_default_hours": 24,
        "escalation_hours": 12,
        "active_staff_count": 19
    },
    {
        "code": "encroachment",
        "name": "Encroachments & Town Planning",
        "description": "Illegal structures, footpath occupations, unauthorized market stalls, and obstruction of public thoroughfares.",
        "head_officer": "Shri Arvind Rao (Deputy Commissioner Encroachments)",
        "contact_email": "encroachment.cell@mc.gov.in",
        "contact_phone": "+91-20-25501077",
        "sla_default_hours": 72,
        "escalation_hours": 36,
        "active_staff_count": 16
    }
]

SAMPLE_COMPLAINTS = [
    # Roads
    {
        "citizen_name": "Ramesh Chandra Sharma",
        "citizen_phone": "+91 98220 14892",
        "citizen_email": "ramesh.sharma@example.com",
        "ward_number": "Ward 3",
        "locality": "Station Road near Tilak Statue",
        "text": "Deep pothole right in front of bus shelter on Station Road. Multiple two-wheelers have skidded and fallen, especially at night.",
        "urgency": "HIGH",
        "dept": "roads",
        "confidence": 0.94,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 18,
        "officer": "K. S. Jadhav (Ward 3 Road Inspector)"
    },
    {
        "citizen_name": "Sunita Kulkarni",
        "citizen_phone": "+91 98501 32910",
        "citizen_email": "sunita.k@example.com",
        "ward_number": "Ward 7",
        "locality": "Gokhale Nagar, Lane 4",
        "text": "Footpath paver blocks dug up during pipeline repair three weeks ago and abandoned. Elderly citizens cannot walk safely.",
        "urgency": "MEDIUM",
        "dept": "roads",
        "confidence": 0.89,
        "routing": "AUTO",
        "status": "ROUTED",
        "hours_ago": 6,
        "officer": None
    },
    {
        "citizen_name": "Mohammed Farooq",
        "citizen_phone": "+91 97654 81023",
        "citizen_email": "mfarooq.biz@example.com",
        "ward_number": "Ward 11",
        "locality": "Shivaji Market Ring Road",
        "text": "Heavy road surface caved in near bypass junction. Dangerous 2-foot depression formed on main carriage way.",
        "urgency": "HIGH",
        "dept": "roads",
        "confidence": 0.96,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 65,  # Overdue (SLA 48h) -> ESCALATED Level 1
        "officer": "R. D. Shinde (Junior Engineer)"
    },
    {
        "citizen_name": "Kavita Nair",
        "citizen_phone": "+91 99234 50124",
        "citizen_email": "kavita.nair@example.com",
        "ward_number": "Ward 2",
        "locality": "Subhash Park Avenue",
        "text": "Damaged asphalt surface near primary school gate with sharp exposed metal gravel. Repaving needed urgently.",
        "urgency": "MEDIUM",
        "dept": "roads",
        "confidence": 0.92,
        "routing": "AUTO",
        "status": "RESOLVED",
        "hours_ago": 90,
        "resolved_hours_ago": 12,
        "officer": "V. B. Patil (Road Inspector)",
        "notes": "Emergency cold-mix asphalt patch completed. Surface leveled and inspected by Assistant Engineer."
    },

    # Water Supply
    {
        "citizen_name": "Prakash G. Joshi",
        "citizen_phone": "+91 98231 66720",
        "citizen_email": "pgjoshi@example.com",
        "ward_number": "Ward 5",
        "locality": "Shastri Nagar Sector 2",
        "text": "Contaminated brownish muddy water coming from kitchen municipal tap since yesterday morning. Emitting foul chemical odor.",
        "urgency": "HIGH",
        "dept": "water_supply",
        "confidence": 0.95,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 14,
        "officer": "S. M. Dighe (Junior Water Works Engineer)"
    },
    {
        "citizen_name": "Amina Begum",
        "citizen_phone": "+91 98902 44102",
        "citizen_email": "amina.b@example.com",
        "ward_number": "Ward 9",
        "locality": "Indira Nagar Slum Colony",
        "text": "No water supply for 4 consecutive days. Municipal water tanker not dispatched despite repeated calls to helpline.",
        "urgency": "HIGH",
        "dept": "water_supply",
        "confidence": 0.93,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 48,  # Overdue (SLA 36h) -> ESCALATED Level 1
        "officer": "T. N. Gokhale (Distribution Superintendent)"
    },
    {
        "citizen_name": "Dinesh Parekh",
        "citizen_phone": "+91 94220 89100",
        "citizen_email": "dinesh.p@example.com",
        "ward_number": "Ward 1",
        "locality": "Navi Peth Cross Lane",
        "text": "Main underground drinking water pipe burst near municipal pump house. Heavy volume of water flooding onto the road.",
        "urgency": "HIGH",
        "dept": "water_supply",
        "confidence": 0.97,
        "routing": "AUTO",
        "status": "RESOLVED",
        "hours_ago": 50,
        "resolved_hours_ago": 20,
        "officer": "S. M. Dighe (Junior Water Works Engineer)",
        "notes": "Main distribution line valve isolated and damaged 150mm pipe section replaced. Normal pressure restored."
    },

    # Electricity
    {
        "citizen_name": "Anand R. Verma",
        "citizen_phone": "+91 98224 55301",
        "citizen_email": "anand.verma@example.com",
        "ward_number": "Ward 4",
        "locality": "Mayur Colony Main Street",
        "text": "Live electrical wire snapped and dangling 4 feet above pedestrian sidewalk near Anand Sweets. Extremely hazardous.",
        "urgency": "HIGH",
        "dept": "electricity",
        "confidence": 0.96,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 4,
        "officer": "A. P. Sawant (Linesman In-Charge)"
    },
    {
        "citizen_name": "Deepa Singhania",
        "citizen_phone": "+91 97631 22890",
        "citizen_email": "deepa.s@example.com",
        "ward_number": "Ward 8",
        "locality": "Airport Road Sector 6",
        "text": "Streetlight pole numbers 12, 13, and 14 not working for past 5 days. Complete darkness causing safety concern for women commuters.",
        "urgency": "MEDIUM",
        "dept": "electricity",
        "confidence": 0.94,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 30,  # Overdue (SLA 24h) -> ESCALATED Level 1
        "officer": "C. L. Rathore (Junior Electrical Engineer)"
    },
    {
        "citizen_name": "Mahesh Bhat",
        "citizen_phone": "+91 98810 99401",
        "citizen_email": "mahesh.bhat@example.com",
        "ward_number": "Ward 6",
        "locality": "Vivekanand Nagar",
        "text": "Distribution transformer sparking loudly with heavy smoke during evening peak load hours.",
        "urgency": "HIGH",
        "dept": "electricity",
        "confidence": 0.97,
        "routing": "AUTO",
        "status": "RESOLVED",
        "hours_ago": 40,
        "resolved_hours_ago": 26,
        "officer": "A. P. Sawant (Linesman In-Charge)",
        "notes": "Faulty HT fuse assembly replaced and load rebalanced on secondary distributor. Transformer functioning normally."
    },

    # Sanitation
    {
        "citizen_name": "Sarita Deshpande",
        "citizen_phone": "+91 98229 11488",
        "citizen_email": "sarita.d@example.com",
        "ward_number": "Ward 12",
        "locality": "Karve Road Mandai Area",
        "text": "Community garbage bin overflowing onto street. Stray cows and dogs scattering wet rotten food waste across 50 meters.",
        "urgency": "HIGH",
        "dept": "sanitation",
        "confidence": 0.95,
        "routing": "AUTO",
        "status": "ROUTED",
        "hours_ago": 8,
        "officer": None
    },
    {
        "citizen_name": "Girish Mhatre",
        "citizen_phone": "+91 98200 44510",
        "citizen_email": "girish.m@example.com",
        "ward_number": "Ward 10",
        "locality": "Kalyani Nagar Bridge",
        "text": "Dead dog carcass lying on the side of roadway for over 36 hours. Extreme stench and fly infestation.",
        "urgency": "HIGH",
        "dept": "sanitation",
        "confidence": 0.93,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 32,  # Overdue (SLA 24h) -> ESCALATED Level 1
        "officer": "S. G. More (Sanitation Supervisor)"
    },
    {
        "citizen_name": "Nandita Sen",
        "citizen_phone": "+91 99302 77123",
        "citizen_email": "nandita.sen@example.com",
        "ward_number": "Ward 3",
        "locality": "Bhandarkar Road",
        "text": "Door-to-door garbage collection vehicle missed our lane for 3 consecutive days. Waste accumulating in residential premises.",
        "urgency": "MEDIUM",
        "dept": "sanitation",
        "confidence": 0.91,
        "routing": "AUTO",
        "status": "RESOLVED",
        "hours_ago": 35,
        "resolved_hours_ago": 15,
        "officer": "B. K. Kamble (Sanitation Inspector)",
        "notes": "Special collection van deployed to clear backlog. Regular route driver reprimanded and substitute assigned."
    },

    # Drainage
    {
        "citizen_name": "Rajiv Tandon",
        "citizen_phone": "+91 98221 44099",
        "citizen_email": "rtandon@example.com",
        "ward_number": "Ward 14",
        "locality": "Aundh Main Chowk",
        "text": "Open sewer manhole cover missing on busy junction road. Poses severe fatal risk to cyclists and vehicles in night.",
        "urgency": "HIGH",
        "dept": "drainage",
        "confidence": 0.96,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 10,
        "officer": "P. B. Gaikwad (Junior Drainage Engineer)"
    },
    {
        "citizen_name": "Meera Swaminathan",
        "citizen_phone": "+91 98401 77234",
        "citizen_email": "meera.s@example.com",
        "ward_number": "Ward 7",
        "locality": "Kothrud Dahanukar Colony",
        "text": "Underground sewer line choked and dirty black sewage overflowing into society courtyard and pedestrian pathway.",
        "urgency": "HIGH",
        "dept": "drainage",
        "confidence": 0.97,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 60,  # Overdue (SLA 36h) -> ESCALATED Level 2 (severely overdue!)
        "officer": "H. R. Kulkarni (Drainage Superintendent)"
    },

    # Public Health
    {
        "citizen_name": "Dr. Hemant Barve",
        "citizen_phone": "+91 98230 88200",
        "citizen_email": "dr.barve@example.com",
        "ward_number": "Ward 2",
        "locality": "Prabhat Road Lane 9",
        "text": "Severe mosquito infestation due to stagnant water in open plot. Three confirmed dengue cases in our apartment building, urgent fogging requested.",
        "urgency": "HIGH",
        "dept": "public_health",
        "confidence": 0.96,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 12,
        "officer": "Dr. Sunita Kadam (Medical Officer Health)"
    },
    {
        "citizen_name": "Shruti Dixit",
        "citizen_phone": "+91 97640 11988",
        "citizen_email": "shruti.d@example.com",
        "ward_number": "Ward 13",
        "locality": "Hadapsar Gadital Market",
        "text": "Pack of aggressive stray dogs chasing two-wheelers and bit two school children this morning outside zilla parishad school.",
        "urgency": "HIGH",
        "dept": "public_health",
        "confidence": 0.93,
        "routing": "AUTO",
        "status": "ROUTED",
        "hours_ago": 5,
        "officer": None
    },

    # Encroachment
    {
        "citizen_name": "Vikram Sethi",
        "citizen_phone": "+91 98211 44882",
        "citizen_email": "vikram.sethi@example.com",
        "ward_number": "Ward 5",
        "locality": "FC Road Commercial Stretch",
        "text": "Unauthorized illegal tea stalls and food carts constructed permanent iron sheds occupying 80% of pedestrian sidewalk.",
        "urgency": "MEDIUM",
        "dept": "encroachment",
        "confidence": 0.94,
        "routing": "AUTO",
        "status": "IN_PROGRESS",
        "hours_ago": 22,
        "officer": "A. S. Pawar (Encroachment Inspector)"
    },

    # LOW CONFIDENCE / AMBIGUOUS COMPLAINTS (Triaged into Manual Review Queue!)
    {
        "citizen_name": "Balwant Singh",
        "citizen_phone": "+91 98110 33400",
        "citizen_email": "bsingh@example.com",
        "ward_number": "Ward 8",
        "locality": "Katraj Ghat Road",
        "text": "There is a terrible problem near my house since three days, please send someone to inspect immediately.",
        "urgency": "MEDIUM",
        "dept": "unassigned",
        "predicted_dept": "roads",
        "confidence": 0.44,  # Below 0.65 threshold!
        "routing": "MANUAL_REVIEW",
        "status": "RECEIVED",
        "hours_ago": 15,
        "officer": None
    },
    {
        "citizen_name": "Geeta Raman",
        "citizen_phone": "+91 98450 66100",
        "citizen_email": "geeta.raman@example.com",
        "ward_number": "Ward 6",
        "locality": "Senapati Bapat Road Corner",
        "text": "Dirty water coming onto the street near the big pothole and iron stall, causing huge trouble for passersby.",
        "urgency": "HIGH",
        "dept": "unassigned",
        "predicted_dept": "drainage",
        "confidence": 0.52,  # Cross-domain ambiguous (water/drainage/roads/encroachment) -> Below threshold!
        "routing": "MANUAL_REVIEW",
        "status": "RECEIVED",
        "hours_ago": 9,
        "officer": None
    },
    {
        "citizen_name": "Arun Kumar Gupta",
        "citizen_phone": "+91 98201 55900",
        "citizen_email": "arun.gupta@example.com",
        "ward_number": "Ward 11",
        "locality": "Viman Nagar Central Park",
        "text": "Electric wire is touching the iron hoarding of the illegal fruit seller near the open drain.",
        "urgency": "HIGH",
        "dept": "unassigned",
        "predicted_dept": "electricity",
        "confidence": 0.58,  # Below threshold!
        "routing": "MANUAL_REVIEW",
        "status": "RECEIVED",
        "hours_ago": 7,
        "officer": None
    },
    {
        "citizen_name": "Lata Mangesh",
        "citizen_phone": "+91 98231 99011",
        "citizen_email": "lata.m@example.com",
        "ward_number": "Ward 4",
        "locality": "Bhosale Nagar Cross",
        "text": "Very bad situation outside our society gate, kindly take prompt municipal action.",
        "urgency": "LOW",
        "dept": "unassigned",
        "predicted_dept": "sanitation",
        "confidence": 0.41,  # Vague -> Below threshold!
        "routing": "MANUAL_REVIEW",
        "status": "RECEIVED",
        "hours_ago": 3,
        "officer": None
    }
]

def seed_database(force: bool = False):
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    if force:
        cursor.execute("DELETE FROM citizen_feedback;")
        cursor.execute("DELETE FROM model_feedback;")
        cursor.execute("DELETE FROM audit_logs;")
        cursor.execute("DELETE FROM complaints;")
        conn.commit()
    
    # Check if departments exist
    cursor.execute("SELECT COUNT(*) FROM departments;")
    dept_count = cursor.fetchone()[0]
    if dept_count == 0:
        for dept in DEPARTMENTS:
            cursor.execute("""
            INSERT INTO departments (code, name, description, head_officer, contact_email, contact_phone, sla_default_hours, escalation_hours, active_staff_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                dept["code"], dept["name"], dept["description"], dept["head_officer"],
                dept["contact_email"], dept["contact_phone"], dept["sla_default_hours"],
                dept["escalation_hours"], dept["active_staff_count"]
            ))
        print(f"Seeded {len(DEPARTMENTS)} civic departments.")
        
    # Department SLA lookup
    cursor.execute("SELECT code, sla_default_hours, escalation_hours FROM departments;")
    dept_sla = {row["code"]: (row["sla_default_hours"], row["escalation_hours"]) for row in cursor.fetchall()}
    
    # Check if complaints exist
    cursor.execute("SELECT COUNT(*) FROM complaints;")
    complaint_count = cursor.fetchone()[0]
    
    if complaint_count == 0:
        now = datetime.now(timezone.utc)
        
        for idx, item in enumerate(SAMPLE_COMPLAINTS, start=1001):
            token = f"GRV-2026-{idx:05d}"
            hours_ago = item["hours_ago"]
            created_at = now - timedelta(hours=hours_ago)
            
            target_dept = item["dept"]
            if target_dept == "unassigned":
                assigned_dept = "unassigned"
                pred_dept = item.get("predicted_dept", "roads")
                sla_hrs = 48
            else:
                assigned_dept = target_dept
                pred_dept = target_dept
                sla_hrs, esc_hrs = dept_sla.get(target_dept, (48, 24))
                
            sla_due_at = created_at + timedelta(hours=sla_hrs)
            
            # Escalation logic based on hours overdue
            is_escalated = 0
            escalation_level = 0
            escalated_at = None
            
            if item["status"] not in ["RESOLVED", "REJECTED"]:
                if now > sla_due_at:
                    overdue_hrs = (now - sla_due_at).total_seconds() / 3600
                    is_escalated = 1
                    if overdue_hrs >= 24:
                        escalation_level = 2
                        escalated_at = (sla_due_at + timedelta(hours=24)).isoformat()
                    else:
                        escalation_level = 1
                        escalated_at = sla_due_at.isoformat()
                        
            resolved_at = None
            if item["status"] == "RESOLVED":
                res_hrs_ago = item.get("resolved_hours_ago", 4)
                resolved_at = (now - timedelta(hours=res_hrs_ago)).isoformat()
                
            cursor.execute("""
            INSERT INTO complaints (
                tracking_token, citizen_name, citizen_phone, citizen_email,
                ward_number, locality, complaint_text, urgency,
                predicted_department, confidence_score, routing_type,
                assigned_department, status, sla_deadline_hours, sla_due_at,
                is_escalated, escalation_level, escalated_at, assigned_officer,
                resolution_notes, resolved_at, city, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                token, item["citizen_name"], item["citizen_phone"], item["citizen_email"],
                item["ward_number"], item["locality"], item["text"], item["urgency"],
                pred_dept, item["confidence"], item["routing"],
                assigned_dept, item["status"], sla_hrs, sla_due_at.isoformat(),
                is_escalated, escalation_level, escalated_at, item["officer"],
                item.get("notes"), resolved_at, MAHARASHTRA_CITIES[(idx - 1001) % len(MAHARASHTRA_CITIES)],
                created_at.isoformat(), now.isoformat()
            ))
            
            complaint_id = cursor.lastrowid
            
            # Insert audit logs
            cursor.execute("""
            INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (
                complaint_id, "LODGED", None, "RECEIVED", "Citizen Portal",
                f"Complaint lodged by {item['citizen_name']} via Web Portal.",
                created_at.isoformat()
            ))
            
            if item["routing"] == "AUTO":
                cursor.execute("""
                INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    complaint_id, "AUTO_ROUTED", "RECEIVED", "ROUTED", "NLP Classifier Engine v1.0",
                    f"Auto-routed to {pred_dept.replace('_', ' ').title()} with {int(item['confidence']*100)}% confidence score (threshold: {round(CONFIDENCE_THRESHOLD * 100)}%).",
                    (created_at + timedelta(seconds=2)).isoformat()
                ))
            else:
                cursor.execute("""
                INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    complaint_id, "SENT_TO_MANUAL_REVIEW", "RECEIVED", "RECEIVED", "NLP Classifier Engine v1.0",
                    f"Confidence score {int(item['confidence']*100)}% is below {round(CONFIDENCE_THRESHOLD * 100)}% threshold. Flagged for Manual Review / Triage Desk operator confirmation.",
                    (created_at + timedelta(seconds=2)).isoformat()
                ))
                
            if item["status"] in ["IN_PROGRESS", "RESOLVED"]:
                cursor.execute("""
                INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    complaint_id, "ASSIGNED", "ROUTED", "IN_PROGRESS", "Department Dispatch System",
                    f"Assigned to {item['officer']} for ground inspection and action.",
                    (created_at + timedelta(hours=2)).isoformat()
                ))
                
            if is_escalated == 1:
                cursor.execute("""
                INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    complaint_id, "SLA_BREACH_ESCALATION", item["status"], item["status"], "SLA Watchdog Daemon",
                    f"SLA deadline breached (> {sla_hrs} hours). Auto-escalated to Level {escalation_level} (Executive Engineer / Cell Director).",
                    escalated_at
                ))
                
            if item["status"] == "RESOLVED":
                cursor.execute("""
                INSERT INTO audit_logs (complaint_id, action, from_status, to_status, performed_by, notes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    complaint_id, "RESOLVED", "IN_PROGRESS", "RESOLVED", item["officer"],
                    f"Redressal verified: {item.get('notes', 'Resolved successfully.')}",
                    resolved_at
                ))
                
        conn.commit()
        print(f"Seeded {len(SAMPLE_COMPLAINTS)} authentic complaint records with complete audit trails.")
        
    conn.close()

if __name__ == "__main__":
    seed_database()
