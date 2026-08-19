import sqlite3
import os
import datetime
from typing import Optional
from app.config import Config

def get_current_ist_date() -> str:
    """Returns today's date in Indian Standard Time (UTC+05:30) as YYYY-MM-DD."""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    ist_now = utc_now + ist_offset
    return ist_now.strftime("%Y-%m-%d")

def get_effective_practice_date() -> str:
    """
    Returns active court practice date in IST (UTC+05:30).
    Rule: After 7:30 PM (19:30), courts have concluded for today.
    The active practice date rolls forward to Tomorrow (T+1) and stays locked
    until Tomorrow 7:30 PM!
    """
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    ist_now = utc_now + ist_offset
    if ist_now.hour > 19 or (ist_now.hour == 19 and ist_now.minute >= 30):
        ist_now += datetime.timedelta(days=1)
    return ist_now.strftime("%Y-%m-%d")

def get_db_connection(db_path: Optional[str] = None, timeout: float = 20.0) -> sqlite3.Connection:
    """Creates a thread-safe, high-concurrency SQLite connection with WAL mode enabled."""
    if db_path is None:
        try:
            from flask import current_app, has_app_context
            if has_app_context() and current_app and current_app.config.get("DB_PATH"):
                target_path = current_app.config.get("DB_PATH")
            else:
                target_path = Config.DB_PATH
        except Exception:
            target_path = Config.DB_PATH
    else:
        target_path = db_path

    conn = sqlite3.connect(target_path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    if target_path != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db(db_path: Optional[str] = None, auto_seed: bool = False):
    """Initializes and migrates the database schema without inserting fake data."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Cases Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnr_number TEXT UNIQUE NOT NULL,
            case_number_formatted TEXT DEFAULT '',
            case_stage TEXT DEFAULT 'Trial / Evidence',
            court_room TEXT DEFAULT '',
            item_number TEXT DEFAULT '',
            judge_name TEXT DEFAULT '',
            client_name TEXT,
            client_phone TEXT,
            client_email TEXT DEFAULT '',
            litigant_role TEXT DEFAULT 'Petitioner / Complainant',
            case_title TEXT,
            case_status TEXT,
            court_name TEXT,
            parties TEXT,
            advocates TEXT,
            last_hearing_date TEXT,
            next_hearing_date TEXT,
            track_next_hearing BOOLEAN DEFAULT 1,
            track_orders BOOLEAN DEFAULT 1,
            track_case_status BOOLEAN DEFAULT 1,
            auto_whatsapp_enabled BOOLEAN DEFAULT 1,
            notes TEXT DEFAULT '',
            custom_advocate_header TEXT DEFAULT 'Advocate Office Notice',
            last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Case History Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_history_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnr_number TEXT NOT NULL,
            change_type TEXT DEFAULT 'HEARING_DATE',
            previous_hearing_date TEXT,
            new_hearing_date TEXT,
            details TEXT DEFAULT '',
            notified BOOLEAN DEFAULT 0,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. API Query Cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_query_cache (
            cnr_number TEXT PRIMARY KEY,
            raw_response TEXT NOT NULL,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ttl_seconds INTEGER DEFAULT 86400
        )
    """)

    # 4. Advocate Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS advocate_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lawyer_name TEXT DEFAULT 'Advocate R. Anbaiya',
            firm_name TEXT DEFAULT 'R. ANBAIYA & ASSOCIATES',
            lawyer_phone TEXT DEFAULT '+919842112233',
            default_whatsapp_footer TEXT DEFAULT 'Sent on behalf of R. Anbaiya & Associates, Advocates & Legal Consultants, Karur',
            meta_phone_number_id TEXT DEFAULT '',
            meta_access_token TEXT DEFAULT '',
            meta_waba_id TEXT DEFAULT '',
            auto_dispatch_meta BOOLEAN DEFAULT 0
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM advocate_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO advocate_settings (
                lawyer_name, firm_name, lawyer_phone, default_whatsapp_footer,
                meta_phone_number_id, meta_access_token, meta_waba_id, auto_dispatch_meta
            ) VALUES (
                'Advocate R. Anbaiya', 'R. ANBAIYA & ASSOCIATES', '+919842112233',
                'Sent on behalf of R. Anbaiya & Associates, Advocates & Legal Consultants, Karur',
                '', '', '', 0
            )
        """)

    # 5. Client Leads Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            client_phone TEXT NOT NULL,
            matter_type TEXT DEFAULT 'Civil Dispute',
            expected_court TEXT DEFAULT 'Principal Sub Court, Karur',
            status TEXT DEFAULT 'NEW',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM cases")
    case_count = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    if auto_seed or case_count == 0:
        from app.db.seed_data import import_karur_sample_data
        import_karur_sample_data(db_path)
