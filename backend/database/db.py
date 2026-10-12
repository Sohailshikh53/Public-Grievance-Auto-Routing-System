"""
Database Initialization and Connection Handler
Public Grievance Auto-Routing System
"""

import os
import sqlite3
from datetime import datetime, timezone

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "grievances.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Departments table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        head_officer TEXT NOT NULL,
        contact_email TEXT NOT NULL,
        contact_phone TEXT NOT NULL,
        sla_default_hours INTEGER NOT NULL,
        escalation_hours INTEGER NOT NULL,
        active_staff_count INTEGER NOT NULL DEFAULT 10
    );
    """)

    # Complaints table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_token TEXT UNIQUE NOT NULL,
        citizen_name TEXT NOT NULL,
        citizen_phone TEXT NOT NULL,
        citizen_email TEXT NOT NULL,
        ward_number TEXT NOT NULL,
        locality TEXT NOT NULL,
        complaint_text TEXT NOT NULL,
        urgency TEXT NOT NULL DEFAULT 'MEDIUM',
        predicted_department TEXT NOT NULL,
        confidence_score REAL NOT NULL,
        routing_type TEXT NOT NULL DEFAULT 'AUTO',
        assigned_department TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'RECEIVED',
        sla_deadline_hours INTEGER NOT NULL,
        sla_due_at TEXT NOT NULL,
        is_escalated INTEGER NOT NULL DEFAULT 0,
        escalation_level INTEGER NOT NULL DEFAULT 0,
        escalated_at TEXT,
        assigned_officer TEXT,
        resolution_notes TEXT,
        resolved_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Forward-compatible columns for richer citizen intake. SQLite migrations are
    # intentionally additive so existing demo databases continue to work.
    cursor.execute("PRAGMA table_info(complaints);")
    complaint_columns = {row[1] for row in cursor.fetchall()}
    for column_name, definition in {
        "language": "TEXT NOT NULL DEFAULT 'English'",
        "latitude": "REAL",
        "longitude": "REAL",
        "city": "TEXT NOT NULL DEFAULT 'Pune'",
    }.items():
        if column_name not in complaint_columns:
            cursor.execute(f"ALTER TABLE complaints ADD COLUMN {column_name} {definition};")
    
    # Audit Logs / Action History table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        from_status TEXT,
        to_status TEXT,
        performed_by TEXT NOT NULL,
        notes TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (complaint_id) REFERENCES complaints (id) ON DELETE CASCADE
    );
    """)

    # System settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    # One-time distribution of the original demo records across Maharashtra so
    # state and city dashboards are useful without rewriting citizen-created data.
    cursor.execute("SELECT value FROM system_settings WHERE key = 'maharashtra_city_backfill_v1';")
    if not cursor.fetchone():
        demo_cities = ["Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Chhatrapati Sambhajinagar", "Solapur", "Kolhapur", "Amravati", "Nanded"]
        cursor.execute("SELECT id FROM complaints ORDER BY id ASC LIMIT 22;")
        demo_rows = cursor.fetchall()
        for index, row in enumerate(demo_rows):
            cursor.execute("UPDATE complaints SET city = ? WHERE id = ?;", (demo_cities[index % len(demo_cities)], row["id"]))
        if demo_rows:
            cursor.execute("INSERT INTO system_settings (key, value) VALUES ('maharashtra_city_backfill_v1', 'complete');")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS citizen_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        resolution_verified INTEGER NOT NULL DEFAULT 1,
        comments TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (complaint_id) REFERENCES complaints (id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id INTEGER NOT NULL,
        predicted_department TEXT NOT NULL,
        corrected_department TEXT NOT NULL,
        correction_source TEXT NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (complaint_id) REFERENCES complaints (id) ON DELETE CASCADE
    );
    """)
    
    # Create indexes for fast lookup and dashboard metrics
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaints_token ON complaints(tracking_token);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaints_assigned_dept ON complaints(assigned_department);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaints_is_escalated ON complaints(is_escalated);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaints_routing_type ON complaints(routing_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaints_ward ON complaints(ward_number);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_complaint ON audit_logs(complaint_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_complaint ON citizen_feedback(complaint_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_feedback_complaint ON model_feedback(complaint_id);")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
