import sqlite3
import os
import json
import time
from typing import Optional, Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(__file__), "cases.db")

def get_db_connection(timeout: float = 20.0) -> sqlite3.Connection:
    """Creates a thread-safe, high-concurrency SQLite connection with WAL mode."""
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def init_db():
    """Initializes and migrates the database table for tracking cases, daily cause lists, and automation rules."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Main Cases Table
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

    # Dynamic Column Migration for cases
    cursor.execute("PRAGMA table_info(cases)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    
    cols_to_add = [
        ("client_email", "TEXT DEFAULT ''"),
        ("litigant_role", "TEXT DEFAULT 'Petitioner / Complainant'"),
        ("case_number_formatted", "TEXT DEFAULT ''"),
        ("case_stage", "TEXT DEFAULT 'Trial / Evidence'"),
        ("court_room", "TEXT DEFAULT ''"),
        ("item_number", "TEXT DEFAULT ''"),
        ("judge_name", "TEXT DEFAULT ''"),
        ("track_next_hearing", "BOOLEAN DEFAULT 1"),
        ("track_orders", "BOOLEAN DEFAULT 1"),
        ("track_case_status", "BOOLEAN DEFAULT 1"),
        ("auto_whatsapp_enabled", "BOOLEAN DEFAULT 1"),
        ("notes", "TEXT DEFAULT ''"),
        ("custom_advocate_header", "TEXT DEFAULT 'Advocate Office Notice'")
    ]

    for col_name, col_type in cols_to_add:
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE cases ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

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

    cursor.execute("PRAGMA table_info(case_history_logs)")
    existing_log_cols = [row[1] for row in cursor.fetchall()]
    log_cols_to_add = [
        ("change_type", "TEXT DEFAULT 'HEARING_DATE'"),
        ("details", "TEXT DEFAULT ''")
    ]
    for col_name, col_type in log_cols_to_add:
        if col_name not in existing_log_cols:
            try:
                cursor.execute(f"ALTER TABLE case_history_logs ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    # 3. Smart API Query Cache Table (Saves Credits!)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_query_cache (
            cnr_number TEXT PRIMARY KEY,
            raw_response TEXT NOT NULL,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ttl_seconds INTEGER DEFAULT 7200
        )
    """)

    # 4. Global Settings Table
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

    # Dynamic Column Migration for advocate_settings
    cursor.execute("PRAGMA table_info(advocate_settings)")
    existing_adv_cols = [row[1] for row in cursor.fetchall()]
    adv_cols_to_add = [
        ("meta_phone_number_id", "TEXT DEFAULT ''"),
        ("meta_access_token", "TEXT DEFAULT ''"),
        ("meta_waba_id", "TEXT DEFAULT ''"),
        ("auto_dispatch_meta", "BOOLEAN DEFAULT 0")
    ]
    for col_name, col_type in adv_cols_to_add:
        if col_name not in existing_adv_cols:
            try:
                cursor.execute(f"ALTER TABLE advocate_settings ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass

    cursor.execute("SELECT COUNT(*) FROM advocate_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO advocate_settings (lawyer_name, firm_name, lawyer_phone, default_whatsapp_footer, meta_phone_number_id, meta_access_token, meta_waba_id, auto_dispatch_meta)
            VALUES ('Advocate R. Anbaiya', 'R. ANBAIYA & ASSOCIATES', '+919842112233', 'Sent on behalf of R. Anbaiya & Associates, Advocates & Legal Consultants, Karur', '', '', '', 0)
        """)
    else:
        cursor.execute("""
            UPDATE advocate_settings SET
                lawyer_name = COALESCE(lawyer_name, 'Advocate R. Anbaiya'),
                firm_name = COALESCE(firm_name, 'R. ANBAIYA & ASSOCIATES'),
                default_whatsapp_footer = COALESCE(default_whatsapp_footer, 'Sent on behalf of R. Anbaiya & Associates, Advocates & Legal Consultants, Karur')
            WHERE id = 1
        """)


    # 5. Case Leads & Inquiries Table
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

    # Check if database is empty and auto-seed Karur sample dataset
    cursor.execute("SELECT COUNT(*) FROM cases")
    case_count = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    if case_count == 0:
        try:
            import_karur_sample_data()
        except Exception:
            pass


def get_all_leads() -> List[Dict[str, Any]]:
    """Returns all prospective client inquiries."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_lead(client_name: str, client_phone: str, matter_type: str = "Civil Dispute",
             expected_court: str = "Principal Sub Court, Karur", notes: str = "") -> int:
    """Inserts a new client inquiry lead."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO leads (client_name, client_phone, matter_type, expected_court, status, notes)
        VALUES (?, ?, ?, ?, 'NEW', ?)
    """, (client_name, client_phone, matter_type, expected_court, notes))
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lead_id

def update_lead_status(lead_id: int, status: str) -> bool:
    """Updates status of a lead."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    conn.commit()
    conn.close()
    return True

# Cache methods to save credits

def get_cached_case(cnr_number: str, max_age_seconds: int = 7200) -> Optional[Dict[str, Any]]:
    """Retrieves cached response from SQLite if younger than max_age_seconds (default 2 hours)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT raw_response, strftime('%s', 'now') - strftime('%s', cached_at) as age FROM api_query_cache WHERE cnr_number = ?", (cnr_number,))
    row = cursor.fetchone()
    conn.close()
    if row and row[1] is not None and row[1] < max_age_seconds:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None

def set_cached_case(cnr_number: str, raw_json: Dict[str, Any]):
    """Stores API response in local SQLite cache."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO api_query_cache (cnr_number, raw_response, cached_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(cnr_number) DO UPDATE SET raw_response = excluded.raw_response, cached_at = CURRENT_TIMESTAMP
    """, (cnr_number, json.dumps(raw_json)))
    conn.commit()
    conn.close()

def upsert_case(case_data: Dict[str, Any], client_name: str = "", client_phone: str = "",
                client_email: str = "", litigant_role: str = "Petitioner / Complainant",
                track_next_hearing: bool = True, track_orders: bool = True,
                track_case_status: bool = True, auto_whatsapp_enabled: bool = True,
                notes: str = "", custom_advocate_header: str = "Advocate Office Notice",
                case_number_formatted: str = "", case_stage: str = "",
                court_room: str = "", item_number: str = "", judge_name: str = "") -> bool:
    """Inserts or updates a case with Uncle's custom automation preferences & cause list fields."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cnr = case_data.get("cnr_number")
    new_next_hearing = case_data.get("next_hearing_date")

    # Check existing case
    cursor.execute("SELECT next_hearing_date, case_status FROM cases WHERE cnr_number = ?", (cnr,))
    existing = cursor.fetchone()

    date_changed = False

    if existing:
        old_next_hearing = existing[0]
        
        # Detect Next Hearing Date Change
        if old_next_hearing != new_next_hearing and new_next_hearing:
            date_changed = True
            cursor.execute("""
                INSERT INTO case_history_logs (cnr_number, change_type, previous_hearing_date, new_hearing_date, details)
                VALUES (?, 'HEARING_DATE_CHANGE', ?, ?, ?)
            """, (cnr, old_next_hearing, new_next_hearing, f"Hearing changed from {old_next_hearing} to {new_next_hearing}"))

        # Update case record
        cursor.execute("""
            UPDATE cases SET
                case_title = COALESCE(?, case_title),
                case_status = COALESCE(?, case_status),
                court_name = COALESCE(?, court_name),
                parties = COALESCE(?, parties),
                advocates = COALESCE(?, advocates),
                last_hearing_date = COALESCE(?, last_hearing_date),
                next_hearing_date = COALESCE(?, next_hearing_date),
                client_name = CASE WHEN ? != '' THEN ? ELSE client_name END,
                client_phone = CASE WHEN ? != '' THEN ? ELSE client_phone END,
                client_email = CASE WHEN ? != '' THEN ? ELSE client_email END,
                litigant_role = CASE WHEN ? != '' THEN ? ELSE litigant_role END,
                track_next_hearing = ?,
                track_orders = ?,
                track_case_status = ?,
                auto_whatsapp_enabled = ?,
                notes = ?,
                custom_advocate_header = ?,
                case_number_formatted = CASE WHEN ? != '' THEN ? ELSE case_number_formatted END,
                case_stage = CASE WHEN ? != '' THEN ? ELSE case_stage END,
                court_room = CASE WHEN ? != '' THEN ? ELSE court_room END,
                item_number = CASE WHEN ? != '' THEN ? ELSE item_number END,
                judge_name = CASE WHEN ? != '' THEN ? ELSE judge_name END,
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
            client_name, client_name,
            client_phone, client_phone,
            client_email, client_email,
            litigant_role, litigant_role,
            1 if track_next_hearing else 0,
            1 if track_orders else 0,
            1 if track_case_status else 0,
            1 if auto_whatsapp_enabled else 0,
            notes,
            custom_advocate_header,
            case_number_formatted, case_number_formatted,
            case_stage, case_stage,
            court_room, court_room,
            item_number, item_number,
            judge_name, judge_name,
            cnr
        ))
    else:
        # Insert new case record
        cursor.execute("""
            INSERT INTO cases (
                cnr_number, client_name, client_phone, client_email, litigant_role, case_title, case_status,
                court_name, parties, advocates, last_hearing_date, next_hearing_date,
                track_next_hearing, track_orders, track_case_status, auto_whatsapp_enabled,
                notes, custom_advocate_header, case_number_formatted, case_stage,
                court_room, item_number, judge_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cnr,
            client_name,
            client_phone,
            client_email,
            litigant_role,
            case_data.get("case_title"),
            case_data.get("case_status"),
            case_data.get("court_name"),
            case_data.get("parties"),
            case_data.get("advocates"),
            case_data.get("last_hearing_date"),
            new_next_hearing,
            1 if track_next_hearing else 0,
            1 if track_orders else 0,
            1 if track_case_status else 0,
            1 if auto_whatsapp_enabled else 0,
            notes,
            custom_advocate_header,
            case_number_formatted,
            case_stage or "Trial / Evidence",
            court_room,
            item_number,
            judge_name
        ))


    conn.commit()
    conn.close()
    return date_changed

def update_case_preferences(cnr_number: str, prefs: Dict[str, Any]) -> bool:
    """Updates automation toggles, client profile, and notes for a specific case."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cases SET
            client_name = COALESCE(?, client_name),
            client_phone = COALESCE(?, client_phone),
            client_email = COALESCE(?, client_email),
            litigant_role = COALESCE(?, litigant_role),
            track_next_hearing = ?,
            track_orders = ?,
            track_case_status = ?,
            auto_whatsapp_enabled = ?,
            notes = ?,
            custom_advocate_header = ?,
            case_number_formatted = COALESCE(?, case_number_formatted),
            case_stage = COALESCE(?, case_stage),
            court_room = COALESCE(?, court_room),
            item_number = COALESCE(?, item_number),
            judge_name = COALESCE(?, judge_name)
        WHERE cnr_number = ?
    """, (
        prefs.get("client_name"),
        prefs.get("client_phone"),
        prefs.get("client_email"),
        prefs.get("litigant_role"),
        1 if prefs.get("track_next_hearing", True) else 0,
        1 if prefs.get("track_orders", True) else 0,
        1 if prefs.get("track_case_status", True) else 0,
        1 if prefs.get("auto_whatsapp_enabled", True) else 0,
        prefs.get("notes", ""),
        prefs.get("custom_advocate_header", "Advocate Office Notice"),
        prefs.get("case_number_formatted"),
        prefs.get("case_stage"),
        prefs.get("court_room"),
        prefs.get("item_number"),
        prefs.get("judge_name"),
        cnr_number
    ))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return updated


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

    """Deletes a case and its history logs."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cases WHERE cnr_number = ?", (cnr_number,))
    cursor.execute("DELETE FROM case_history_logs WHERE cnr_number = ?", (cnr_number,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def clear_all_cases() -> bool:
    """Purges all cases and logs to provide a clean slate."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cases")
    cursor.execute("DELETE FROM case_history_logs")
    cursor.execute("DELETE FROM api_query_cache")
    conn.commit()
    conn.close()
    return True


def get_daily_cause_list(target_date: str = "") -> Dict[str, Any]:
    """
    Generates the grouped Daily Cause List & Court Board for a specific hearing date.
    Returns summary counters and cases grouped by Court Complex.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if target_date:
        cursor.execute("SELECT * FROM cases WHERE next_hearing_date = ? ORDER BY court_name, CAST(item_number AS INTEGER)", (target_date,))
    else:
        # Get all cases that have a next hearing date
        cursor.execute("SELECT * FROM cases WHERE next_hearing_date != '' AND next_hearing_date IS NOT NULL ORDER BY next_hearing_date ASC, court_name, CAST(item_number AS INTEGER)")

    cases = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Group by Court Complex
    courts_map = {}
    for c in cases:
        cname = c.get("court_name") or "District Court Complex"
        if cname not in courts_map:
            courts_map[cname] = []
        courts_map[cname].append(c)

    court_summaries = []
    for court_name, items in courts_map.items():
        court_summaries.append({
            "court_name": court_name,
            "hearings_count": len(items),
            "cases": items
        })

    return {
        "target_date": target_date or "All Scheduled Dates",
        "total_hearings": len(cases),
        "total_courts": len(courts_map),
        "court_summaries": court_summaries
    }



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

def get_advocate_settings() -> Dict[str, Any]:
    """Retrieves Uncle's global advocate firm settings."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM advocate_settings LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

def update_advocate_settings(settings: Dict[str, Any]) -> bool:
    """Updates Uncle's global advocate firm settings and Meta WhatsApp credentials."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE advocate_settings SET
            lawyer_name = ?,
            firm_name = ?,
            lawyer_phone = ?,
            default_whatsapp_footer = ?,
            meta_phone_number_id = COALESCE(?, meta_phone_number_id),
            meta_access_token = COALESCE(?, meta_access_token),
            meta_waba_id = COALESCE(?, meta_waba_id),
            auto_dispatch_meta = COALESCE(?, auto_dispatch_meta)
        WHERE id = 1
    """, (
        settings.get("lawyer_name", "Advocate R. Anbaiya"),
        settings.get("firm_name", "R. ANBAIYA & ASSOCIATES"),
        settings.get("lawyer_phone", "+919842112233"),
        settings.get("default_whatsapp_footer", "Sent on behalf of R. Anbaiya & Associates, Advocates & Legal Consultants, Karur"),
        settings.get("meta_phone_number_id"),
        settings.get("meta_access_token"),
        settings.get("meta_waba_id"),
        1 if settings.get("auto_dispatch_meta") else 0
    ))
    conn.commit()
    conn.close()
    return True

def import_karur_sample_data():
    """Pre-populates the exact 14 Karur Court hearings from Uncle's sample."""
    sample_hearings = [
        {
            "cnr_number": "TNKR010010352023",
            "case_number_formatted": "STC/1035/2023",
            "case_title": "M Palanisamy vs M Velmurugan",
            "court_name": "Chief Judicial Magistrate Court, Karur",
            "court_room": "Room 8",
            "item_number": "4",
            "judge_name": "M. CHARLES ALBERT, Judicial Magistrate No.II",
            "case_stage": "Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "M Palanisamy",
            "client_phone": "+919443322110",
            "notes": "Complainant evidence cross examination"
        },
        {
            "cnr_number": "TNKR020003832025",
            "case_number_formatted": "STC/383/2025",
            "case_title": "G Eniyavan vs D Jeevanandham",
            "court_name": "Fast Track Court at Magisterial Level, Karur",
            "court_room": "Room 10",
            "item_number": "174",
            "judge_name": "Thiru R.Mahesh, B.A., LL.B(Hons)., LL.M.",
            "case_stage": "Service Pending - Warrant",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "G Eniyavan",
            "client_phone": "+919842112233",
            "notes": "NBW execution pending"
        },
        {
            "cnr_number": "TNKR030000252025",
            "case_number_formatted": "EP/25/2025",
            "case_title": "Shalini vs Managing Director TNSTC & 3 Ors",
            "court_name": "Mahila Court, Karur",
            "court_room": "Room 9",
            "item_number": "2",
            "judge_name": "Thiru P.Thangavel, B.Sc., LL.M., Sessions Judge",
            "case_stage": "For Attachment / Arrest / Deposit",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "Shalini",
            "client_phone": "+919789012345",
            "notes": "Execution petition for deposit"
        },
        {
            "cnr_number": "TNKR040003612025",
            "case_number_formatted": "OS/361/2025",
            "case_title": "S Nirmala vs C Velusamy & 10 Ors",
            "court_name": "Principal District Court, Karur",
            "court_room": "Room 1",
            "item_number": "108",
            "judge_name": "Tmt. S.SUMATHY, M.L., District Judge",
            "case_stage": "IA Pending",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "S Nirmala",
            "client_phone": "+919655443322",
            "notes": "Injunction application hearing"
        },
        {
            "cnr_number": "TNKR050003592024",
            "case_number_formatted": "OS/359/2024",
            "case_title": "State Bank of India vs M/s Kathiravan Tea Stall",
            "court_name": "Principal District Munsif Court, Karur",
            "court_room": "Room 5",
            "item_number": "16",
            "judge_name": "Thiru. N.Nilaveshwaran, B.A., B.L.",
            "case_stage": "Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "SBI Vangal Branch",
            "client_phone": "+919445566778",
            "notes": "Bank manager witness examination"
        },
        {
            "cnr_number": "TNKR050001392021",
            "case_number_formatted": "OS/139/2021",
            "case_title": "A Palaniyappan vs R Manokaran & 5 Ors",
            "court_name": "Principal District Munsif Court, Karur",
            "court_room": "Room 5",
            "item_number": "23",
            "judge_name": "Thiru. N.Nilaveshwaran, B.A., B.L.",
            "case_stage": "Trial",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "A Palaniyappan",
            "client_phone": "+919842555666",
            "notes": "Final trial arguments"
        },
        {
            "cnr_number": "TNKR060000692024",
            "case_number_formatted": "COS/69/2024",
            "case_title": "Shobika Impex Private LTD vs Sundar A N Sundarapandiyan",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "1",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "Shobika Impex Ltd",
            "client_phone": "+919843011223",
            "notes": "Commercial dispute evidence"
        },
        {
            "cnr_number": "TNKR060001392025",
            "case_number_formatted": "OS/139/2025",
            "case_title": "Bank of Baroda Karur vs P Kalyani & Anr",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "31",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Ex-parte Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "Bank of Baroda Main",
            "client_phone": "+919444111222",
            "notes": "Proof affidavit filing"
        },
        {
            "cnr_number": "TNKR060003952025",
            "case_number_formatted": "OS/395/2025",
            "case_title": "Bank of Baroda vs B Priyadharshini & 2 Ors",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "35",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Ex-parte Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "BOB Aravakurichi",
            "client_phone": "+919444333444",
            "notes": "Recovery suit exparte"
        },
        {
            "cnr_number": "TNKR060008312025",
            "case_number_formatted": "OS/831/2025",
            "case_title": "State Bank of India vs P Arumugam",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "37",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Ex-parte Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "SBI Aravakurichi",
            "client_phone": "+919445112233",
            "notes": "Exparte order hearing"
        },
        {
            "cnr_number": "TNKR060005552023",
            "case_number_formatted": "OS/555/2023",
            "case_title": "SBI Kovai Road vs D Yasotha",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "46",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Steps",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "SBI Kovai Road",
            "client_phone": "+919445998877",
            "notes": "Legal heir steps petition"
        },
        {
            "cnr_number": "TNKR060000942025",
            "case_number_formatted": "OS/94/2025",
            "case_title": "Bank of Baroda vs V Kumar",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 4",
            "item_number": "42",
            "judge_name": "Thiru. BALAMURUGAN V.S., Addl Subordinate Judge",
            "case_stage": "Ex-parte Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "BOB Karur Main",
            "client_phone": "+919444111222",
            "notes": "Proof affidavit"
        },
        {
            "cnr_number": "TNKR060004662025",
            "case_number_formatted": "OS/466/2025",
            "case_title": "T Shankar vs A A Thangavelu & 10 Ors",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 4",
            "item_number": "43",
            "judge_name": "Thiru. BALAMURUGAN V.S., Addl Subordinate Judge",
            "case_stage": "Ex-parte Evidence",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "T Shankar",
            "client_phone": "+919842199887",
            "notes": "Partition suit exparte"
        },
        {
            "cnr_number": "TNKR060000722021",
            "case_number_formatted": "OS/72/2021",
            "case_title": "K Lakshmi vs V Vadivel",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 4",
            "item_number": "106",
            "judge_name": "Thiru. BALAMURUGAN V.S., Addl Subordinate Judge",
            "case_stage": "IA Pending",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-14",
            "client_name": "K Lakshmi",
            "client_phone": "+919842333221",
            "notes": "Commissioner report objection"
        },
        {
            "cnr_number": "TNKR040008422024",
            "case_number_formatted": "OS/842/2024",
            "case_title": "Karthik vs Rajesh Kumar",
            "court_name": "Principal District Court, Karur",
            "court_room": "Room 2",
            "item_number": "12",
            "judge_name": "Tmt. S.SUMATHY, M.L., District Judge",
            "case_stage": "Arguments",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-15",
            "client_name": "Karthik",
            "client_phone": "+919443112233",
            "notes": "Final trial arguments"
        },
        {
            "cnr_number": "TNKR030002452024",
            "case_number_formatted": "HMA/245/2024",
            "case_title": "Sangeetha vs Suresh",
            "court_name": "Mahila Court, Karur",
            "court_room": "Room 9",
            "item_number": "5",
            "judge_name": "Thiru P.Thangavel, B.Sc., LL.M., Sessions Judge",
            "case_stage": "Final Hearing",
            "case_status": "PENDING",
            "next_hearing_date": "2026-08-16",
            "client_name": "Sangeetha",
            "client_phone": "+919789112244",
            "notes": "Maintenance dispute final hearing"
        },
        {
            "cnr_number": "TNKR060001562023",
            "case_number_formatted": "CRP/156/2023",
            "case_title": "Venkatesh vs State",
            "court_name": "Principal Sub Court, Karur",
            "court_room": "Room 3",
            "item_number": "8",
            "judge_name": "Tmt K.L.Priyanga, B.A., B.L.(Hons)",
            "case_stage": "Judgment Pronounced",
            "case_status": "DISPOSED",
            "next_hearing_date": "2026-08-10",
            "client_name": "Venkatesh",
            "client_phone": "+919842778899",
            "notes": "Decree granted in favor of petitioner"
        }
    ]

    for h in sample_hearings:
        db_payload = {
            "cnr_number": h["cnr_number"],
            "case_title": h["case_title"],
            "case_status": h["case_status"],
            "court_name": h["court_name"],
            "parties": h["case_title"].replace(" vs ", " | "),
            "advocates": "Advocate R. Anbaiya",
            "last_hearing_date": "2026-07-15",
            "next_hearing_date": h["next_hearing_date"]
        }
        upsert_case(
            db_payload,
            client_name=h["client_name"],
            client_phone=h["client_phone"],
            track_next_hearing=True,
            track_orders=True,
            track_case_status=True,
            auto_whatsapp_enabled=True,
            notes=h["notes"],
            case_number_formatted=h["case_number_formatted"],
            case_stage=h["case_stage"],
            court_room=h["court_room"],
            item_number=h["item_number"],
            judge_name=h["judge_name"]
        )

    # Log sample alerts
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO case_history_logs (cnr_number, change_type, previous_hearing_date, new_hearing_date, details)
        VALUES (?, 'WARRANT_ISSUED', ?, ?, ?)
    """, ("TNKR020003832025", "2026-08-01", "2026-08-14", "Service Pending - Non-Bailable Warrant execution pending"))
    cursor.execute("""
        INSERT INTO case_history_logs (cnr_number, change_type, previous_hearing_date, new_hearing_date, details)
        VALUES (?, 'HEARING_DATE_CHANGE', ?, ?, ?)
    """, ("TNKR010010352023", "2026-07-28", "2026-08-14", "Hearing date updated for Evidence cross examination"))
    conn.commit()
    conn.close()



if __name__ == "__main__":
    init_db()
    import_karur_sample_data()
    print("Database and Karur Cause List pre-loaded successfully at:", DB_PATH)
