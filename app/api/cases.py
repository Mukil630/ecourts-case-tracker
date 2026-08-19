import time
from flask import Blueprint, jsonify, request, render_template
from app.db.repository import (
    get_all_cases,
    get_case_by_cnr,
    delete_case,
    clear_all_cases,
    update_case_preferences,
    upsert_case,
    get_advocate_settings,
)
from app.db.seed_data import import_karur_sample_data
from app.services.ecourts_service import fetch_case_details, get_api_key, search_cases_by_advocate

cases_bp = Blueprint("cases", __name__)

@cases_bp.route("/api/cases", methods=["GET"])
def list_cases():
    """Returns all stored cases from SQLite."""
    return jsonify(get_all_cases())

@cases_bp.route("/api/cases/clear-all", methods=["DELETE", "POST"])
def clear_all_endpoint():
    """Purges all cases and logs for a clean database."""
    clear_all_cases()
    return jsonify({"success": True, "message": "All cases and logs cleared."})

@cases_bp.route("/api/cases/<cnr>", methods=["GET"])
def get_case(cnr):
    """Retrieves single case details by CNR number."""
    case = get_case_by_cnr(cnr.upper())
    if case:
        return jsonify({"success": True, "case": case})
    return jsonify({"success": False, "error": "Case not found"}), 404

@cases_bp.route("/api/cases/<cnr>", methods=["DELETE"])
def remove_case(cnr):
    """Deletes a single case by CNR number."""
    deleted = delete_case(cnr.upper())
    return jsonify({"success": deleted})

@cases_bp.route("/api/cases/<cnr>/preferences", methods=["PUT"])
def update_preferences(cnr):
    """Updates automation preferences and advocate strategy notes for a case."""
    data = request.get_json() or {}
    success = update_case_preferences(cnr.upper(), data)
    return jsonify({"success": success})

@cases_bp.route("/api/cases/<cnr>/status", methods=["PUT", "POST"])
def update_status_route(cnr):
    """Updates case lifecycle status (e.g. 'DISPOSED' or 'PENDING') to freeze or unfreeze API checks."""
    from app.db.repository import update_case_status
    data = request.get_json() or {}
    new_status = data.get("status", "DISPOSED")
    success = update_case_status(cnr.upper(), new_status)
    return jsonify({"success": success, "status": new_status.upper()})

@cases_bp.route("/api/check-case", methods=["POST"])
def check_case():
    """
    Directly adds/updates client case with eCourts live sync or instant local private vault tracking.
    """
    data = request.get_json() or {}

    # 1. Clean Client Name & Phone
    client_name = (data.get("client_name") or "New Client").strip()
    raw_phone = str(data.get("client_phone") or "").strip()
    digits = "".join(c for c in raw_phone if c.isdigit())
    if len(digits) == 10:
        client_phone = f"+91{digits}"
    elif digits.startswith("91") and len(digits) == 12:
        client_phone = f"+{digits}"
    elif digits:
        client_phone = f"+{digits}" if not raw_phone.startswith("+") else raw_phone
    else:
        client_phone = "+919443322110"

    # 2. Clean CNR & Case Number
    raw_input_no = (data.get("cnr") or data.get("case_number") or data.get("case_number_formatted") or "").strip().upper()
    if not raw_input_no:
        raw_input_no = f"TNKR-{int(time.time())}"

    case_number_formatted = data.get("case_number_formatted") or raw_input_no
    cnr = raw_input_no.replace(" ", "").replace("/", "-")

    client_email = data.get("client_email", "")
    litigant_role = data.get("litigant_role", "Petitioner / Complainant")
    court_name = data.get("court_name") or "Principal Sub Court, Karur"
    court_room = data.get("court_room") or "Room 1"
    item_number = data.get("item_number") or "1"
    case_stage = data.get("case_stage") or "Evidence"
    notes = data.get("notes") or ""
    next_hearing_date = data.get("next_hearing_date") or time.strftime("%Y-%m-%d")
    force_live = bool(data.get("force_live", False))

    api_key = get_api_key()

    # Try live eCourts if 16-char CNR without hyphens
    if api_key and len(cnr) == 16 and "-" not in cnr:
        try:
            api_result = fetch_case_details(cnr, force_live=force_live)
            if api_result.get("success"):
                db_payload = {
                    "cnr_number": api_result.get("cnr_number") or cnr,
                    "case_title": api_result.get("case_title") or f"{client_name} Matter",
                    "case_status": api_result.get("case_status") or "PENDING",
                    "court_name": api_result.get("court_name") or court_name,
                    "parties": api_result.get("parties") or f"Petitioner: {', '.join(api_result.get('petitioners', []))} | Respondent: {', '.join(api_result.get('respondents', []))}",
                    "advocates": api_result.get("advocates") or f"Petitioner Adv: {', '.join(api_result.get('petitioner_advocates', []))} | Respondent Adv: {', '.join(api_result.get('respondent_advocates', []))}",
                    "last_hearing_date": api_result.get("last_hearing_date") or "",
                    "next_hearing_date": api_result.get("next_hearing_date") or next_hearing_date
                }
                date_changed = upsert_case(
                    db_payload,
                    client_name=client_name,
                    client_phone=client_phone,
                    client_email=client_email,
                    litigant_role=litigant_role,
                    track_next_hearing=True,
                    track_orders=True,
                    track_case_status=True,
                    auto_whatsapp_enabled=True,
                    notes=notes,
                    case_number_formatted=api_result.get("case_number_formatted") or case_number_formatted,
                    case_stage=api_result.get("case_stage") or case_stage,
                    court_room=api_result.get("court_room") or court_room,
                    item_number=item_number,
                    judge_name=api_result.get("judge_name") or ""
                )
                return jsonify({
                    "success": True,
                    "date_changed": date_changed,
                    "is_cached": api_result.get("is_cached", False),
                    "cache_note": "Synced with eCourts live record",
                    "case_data": api_result
                })
        except Exception:
            pass

    # Instant Direct Private Chamber Enrollment
    db_payload = {
        "cnr_number": cnr,
        "case_title": data.get("case_title") or f"{client_name} vs Opposing Party",
        "case_status": data.get("case_status") or "PENDING",
        "court_name": court_name,
        "parties": f"{client_name} | Opposing Party",
        "advocates": "Advocate R. Anbaiya",
        "last_hearing_date": "2026-07-15",
        "next_hearing_date": next_hearing_date
    }
    date_changed = upsert_case(
        db_payload,
        client_name=client_name,
        client_phone=client_phone,
        client_email=client_email,
        litigant_role=litigant_role,
        track_next_hearing=True,
        track_orders=True,
        track_case_status=True,
        auto_whatsapp_enabled=True,
        notes=notes,
        case_number_formatted=case_number_formatted,
        case_stage=case_stage,
        court_room=court_room,
        item_number=item_number,
        judge_name=data.get("judge_name", "")
    )
    return jsonify({
        "success": True,
        "date_changed": date_changed,
        "is_cached": True,
        "cache_note": "Enrolled in Private Chamber Vault",
        "case_data": db_payload
    })

@cases_bp.route("/api/search-advocate-cases", methods=["GET", "POST"])
def search_advocate_cases_endpoint():
    """Searches cases registered under Advocate Name on eCourts / Karur."""
    if request.method == "POST":
        data = request.get_json() or {}
        advocate_name = data.get("advocate_name", "Advocate R. Anbaiya")
        district = data.get("district", "Karur")
    else:
        advocate_name = request.args.get("name", "Advocate R. Anbaiya")
        district = request.args.get("district", "Karur")

    results = search_cases_by_advocate(advocate_name, district=district)
    return jsonify(results)

@cases_bp.route("/api/export-case/<cnr>")
def export_case(cnr):
    """Renders an ultra-detailed, prestigious legal case dossier brief."""
    case = get_case_by_cnr(cnr.upper())
    if not case:
        return "<h3>Case not found in database. Please track it first.</h3>", 404

    settings = get_advocate_settings()
    return render_template("case_dossier.html", case=case, settings=settings)
