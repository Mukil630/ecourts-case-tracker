import json
import sqlite3
from typing import Optional, Dict, Any, List
from app.db.database import get_db_connection, get_current_ist_date
from app.db.seed_data import ensure_today_hearings_synchronized

def get_all_cases(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all stored cases from SQLite."""
    ensure_today_hearings_synchronized(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases ORDER BY next_hearing_date ASC, id ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_case_by_cnr(cnr_number: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Returns a single case by CNR number or formatted case number."""
    clean = cnr_number.strip().upper()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE UPPER(cnr_number) = ? OR UPPER(case_number_formatted) = ?", (clean, clean))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_case(cnr_number: str, db_path: Optional[str] = None) -> bool:
    """Deletes a case and its associated logs."""
    clean = cnr_number.strip().upper()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cases WHERE UPPER(cnr_number) = ?", (clean,))
    deleted = cursor.rowcount > 0
    cursor.execute("DELETE FROM case_history_logs WHERE UPPER(cnr_number) = ?", (clean,))
    conn.commit()
    conn.close()
    return deleted

def clear_all_cases(db_path: Optional[str] = None) -> bool:
    """Purges all cases, logs, cache, and leads to provide a clean slate."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cases")
    cursor.execute("DELETE FROM case_history_logs")
    cursor.execute("DELETE FROM api_query_cache")
    cursor.execute("DELETE FROM leads")
    conn.commit()
    conn.close()
    return True

def update_case_preferences(cnr_number: str, preferences: Dict[str, Any], db_path: Optional[str] = None) -> bool:
    """Updates custom advocate settings and status for a tracked case."""
    clean = cnr_number.strip().upper()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    status_val = preferences.get("case_status")
    next_date_val = preferences.get("next_hearing_date")
    stage_val = preferences.get("case_stage")

    cursor.execute("""
        UPDATE cases SET
            track_next_hearing = ?,
            track_orders = ?,
            track_case_status = ?,
            auto_whatsapp_enabled = ?,
            notes = ?,
            custom_advocate_header = ?,
            case_status = COALESCE(?, case_status),
            next_hearing_date = COALESCE(?, next_hearing_date),
            case_stage = COALESCE(?, case_stage)
        WHERE UPPER(cnr_number) = ? OR UPPER(case_number_formatted) = ?
    """, (
        1 if preferences.get("track_next_hearing", True) else 0,
        1 if preferences.get("track_orders", True) else 0,
        1 if preferences.get("track_case_status", True) else 0,
        1 if preferences.get("auto_whatsapp_enabled", True) else 0,
        preferences.get("notes", ""),
        preferences.get("custom_advocate_header", "Advocate Office Notice"),
        status_val,
        next_date_val,
        stage_val,
        clean,
        clean
    ))
    conn.commit()
    conn.close()
    return True

def update_case_status(cnr_number: str, new_status: str, db_path: Optional[str] = None) -> bool:
    """Updates the lifecycle status of a case (e.g. 'DISPOSED' or 'PENDING')."""
    clean = cnr_number.strip().upper()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cases SET case_status = ? 
        WHERE UPPER(cnr_number) = ? OR UPPER(case_number_formatted) = ?
    """, (new_status.strip().upper(), clean, clean))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def get_daily_cause_list(target_date: str = "", db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates the grouped Daily Cause List & Court Board for a specific hearing date.
    Returns summary counters and cases grouped by Court Complex.
    """
    today_ist = get_current_ist_date()
    if not target_date or target_date.strip() == "":
        target_date = today_ist

    ensure_today_hearings_synchronized(db_path)

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM cases 
        WHERE next_hearing_date = ? 
        ORDER BY court_name, CAST(item_number AS INTEGER), item_number
    """, (target_date,))

    cases = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Group by Court Complex
    courts_map = {}
    for c in cases:
        cname = c.get("court_name") or "Karur District Court Complex"
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
        "target_date": target_date,
        "total_hearings": len(cases),
        "total_courts": len(courts_map),
        "court_summaries": court_summaries
    }

def upsert_case(case_data: Dict[str, Any], client_name: str = "", client_phone: str = "",
                client_email: str = "", litigant_role: str = "Petitioner / Complainant",
                track_next_hearing: bool = True, track_orders: bool = True,
                track_case_status: bool = True, auto_whatsapp_enabled: bool = True,
                notes: str = "", custom_advocate_header: str = "Advocate Office Notice",
                case_number_formatted: str = "", case_stage: str = "",
                court_room: str = "", item_number: str = "", judge_name: str = "",
                db_path: Optional[str] = None) -> bool:
    """Inserts or updates a case with custom automation preferences & cause list fields."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cnr = case_data.get("cnr_number")
    new_next_hearing = case_data.get("next_hearing_date")

    cursor.execute("SELECT next_hearing_date, case_status FROM cases WHERE cnr_number = ?", (cnr,))
    existing = cursor.fetchone()

    date_changed = False

    if existing:
        old_next_hearing = existing["next_hearing_date"]
        if old_next_hearing != new_next_hearing and new_next_hearing:
            date_changed = True
            cursor.execute("""
                INSERT INTO case_history_logs (cnr_number, change_type, previous_hearing_date, new_hearing_date, details)
                VALUES (?, 'HEARING_DATE_CHANGE', ?, ?, ?)
            """, (cnr, old_next_hearing, new_next_hearing, f"Hearing changed from {old_next_hearing} to {new_next_hearing}"))

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
                notes = CASE WHEN ? != '' THEN ? ELSE notes END,
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
            notes, notes,
            custom_advocate_header,
            case_number_formatted, case_number_formatted,
            case_stage, case_stage,
            court_room, court_room,
            item_number, item_number,
            judge_name, judge_name,
            cnr
        ))
    else:
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
            case_data.get("case_status", "PENDING"),
            case_data.get("court_name"),
            case_data.get("parties"),
            case_data.get("advocates", "Advocate R. Anbaiya"),
            case_data.get("last_hearing_date"),
            new_next_hearing,
            1 if track_next_hearing else 0,
            1 if track_orders else 0,
            1 if track_case_status else 0,
            1 if auto_whatsapp_enabled else 0,
            notes,
            custom_advocate_header,
            case_number_formatted,
            case_stage,
            court_room,
            item_number,
            judge_name
        ))

    conn.commit()
    conn.close()
    return date_changed

def get_cached_case(cnr_number: str, max_age_seconds: int = 86400, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves cached response from SQLite if younger than max_age_seconds (default 24 hours)."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT raw_response, strftime('%s', 'now') - strftime('%s', cached_at) as age FROM api_query_cache WHERE cnr_number = ?", (cnr_number,))
    row = cursor.fetchone()
    conn.close()
    if row and row["raw_response"]:
        try:
            return json.loads(row["raw_response"])
        except Exception:
            return None
    return None

def set_cached_case(cnr_number: str, raw_json: Dict[str, Any], db_path: Optional[str] = None):
    """Stores API response in local SQLite cache."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO api_query_cache (cnr_number, raw_response, cached_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(cnr_number) DO UPDATE SET raw_response = excluded.raw_response, cached_at = CURRENT_TIMESTAMP
    """, (cnr_number, json.dumps(raw_json)))
    conn.commit()
    conn.close()

def get_all_leads(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all prospective client inquiries."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads ORDER BY id DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def add_lead(client_name: str, client_phone: str, matter_type: str = "Civil Dispute",
             expected_court: str = "Principal Sub Court, Karur", notes: str = "",
             db_path: Optional[str] = None) -> int:
    """Inserts a new client inquiry lead."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO leads (client_name, client_phone, matter_type, expected_court, status, notes)
        VALUES (?, ?, ?, ?, 'NEW', ?)
    """, (client_name, client_phone, matter_type, expected_court, notes))
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lead_id

def update_lead_status(lead_id: int, status: str, db_path: Optional[str] = None) -> bool:
    """Updates status of a lead."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    conn.commit()
    conn.close()
    return True

def get_case_history_logs(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetches case hearing change audit logs."""
    conn = get_db_connection(db_path)
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

def mark_log_notified(log_id: int, db_path: Optional[str] = None) -> bool:
    """Marks a case history change log as notified/dispatched."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE case_history_logs SET notified = 1 WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return True

def get_advocate_settings(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves advocate firm settings."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM advocate_settings LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {}

def update_advocate_settings(settings: Dict[str, Any], db_path: Optional[str] = None) -> bool:
    """Updates advocate firm settings and Meta WhatsApp credentials."""
    conn = get_db_connection(db_path)
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
