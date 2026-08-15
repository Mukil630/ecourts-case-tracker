import sqlite3
import os
from typing import Optional, Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(__file__), "cases.db")

def init_db():
    """Initializes the database table for tracking cases."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnr_number TEXT UNIQUE NOT NULL,
            client_name TEXT,
            client_phone TEXT,
            case_title TEXT,
            case_status TEXT,
            court_name TEXT,
            parties TEXT,
            advocates TEXT,
            last_hearing_date TEXT,
            next_hearing_date TEXT,
            last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_history_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnr_number TEXT NOT NULL,
            previous_hearing_date TEXT,
            new_hearing_date TEXT,
            notified BOOLEAN DEFAULT 0,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def upsert_case(case_data: Dict[str, Any], client_name: str = "", client_phone: str = "") -> bool:
    """Inserts or updates a case. Returns True if next_hearing_date has changed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cnr = case_data.get("cnr_number")
    new_next_hearing = case_data.get("next_hearing_date")

    # Check existing case
    cursor.execute("SELECT next_hearing_date FROM cases WHERE cnr_number = ?", (cnr,))
    existing = cursor.fetchone()

    date_changed = False

    if existing:
        old_next_hearing = existing[0]
        if old_next_hearing != new_next_hearing:
            date_changed = True
            # Log date change
            cursor.execute("""
                INSERT INTO case_history_logs (cnr_number, previous_hearing_date, new_hearing_date)
                VALUES (?, ?, ?)
            """, (cnr, old_next_hearing, new_next_hearing))

        # Update case record
        cursor.execute("""
            UPDATE cases SET
                case_title = ?,
                case_status = ?,
                court_name = ?,
                parties = ?,
                advocates = ?,
                last_hearing_date = ?,
                next_hearing_date = ?,
                last_checked_at = CURRENT_TIMESTAMP
            WHERE cnr_number = ?
        """, (
            case_data.get("case_title"),
            case_data.get("case_status"),
            case_data.get("court_name"),
            case_data.get("parties"),
            case_data.get("advocates"),
            case_data.get("last_hearing_date"),
            new_next_hearing,
            cnr
        ))
    else:
        # Insert new case record
        cursor.execute("""
            INSERT INTO cases (
                cnr_number, client_name, client_phone, case_title, case_status,
                court_name, parties, advocates, last_hearing_date, next_hearing_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cnr,
            client_name,
            client_phone,
            case_data.get("case_title"),
            case_data.get("case_status"),
            case_data.get("court_name"),
            case_data.get("parties"),
            case_data.get("advocates"),
            case_data.get("last_hearing_date"),
            new_next_hearing
        ))

    conn.commit()
    conn.close()
    return date_changed

def get_all_cases() -> List[Dict[str, Any]]:
    """Fetches all tracked cases."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
