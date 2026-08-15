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
    cursor.execute("SELECT * FROM cases ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_case_by_cnr(cnr_number: str) -> Optional[Dict[str, Any]]:
    """Fetches a single case by its CNR number."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE cnr_number = ?", (cnr_number,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_case(cnr_number: str) -> bool:
    """Deletes a case and its related logs from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cases WHERE cnr_number = ?", (cnr_number,))
    cursor.execute("DELETE FROM case_history_logs WHERE cnr_number = ?", (cnr_number,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def get_case_history_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Fetches case hearing change audit logs."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, c.case_title, c.client_name, c.client_phone 
        FROM case_history_logs l
        LEFT JOIN cases c ON l.cnr_number = c.cnr_number
        ORDER BY l.id DESC LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def mark_log_notified(log_id: int) -> bool:
    """Marks a case history change log as notified/dispatched."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE case_history_logs SET notified = 1 WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return True

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
