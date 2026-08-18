import time
from flask import Blueprint, jsonify, request, render_template
from app.db.repository import (
    get_daily_cause_list,
    get_all_cases,
    get_advocate_settings,
)
from app.db.seed_data import import_karur_sample_data

cause_list_bp = Blueprint("cause_list", __name__)

@cause_list_bp.route("/api/cause-list", methods=["GET"])
def cause_list_endpoint():
    """Returns the grouped Daily Cause List & Court Hearing Board."""
    target_date = request.args.get("date", "").strip()
    cause_list = get_daily_cause_list(target_date)
    if cause_list.get("total_hearings", 0) == 0 and len(get_all_cases()) == 0:
        try:
            import_karur_sample_data()
            cause_list = get_daily_cause_list(target_date)
        except Exception:
            pass
    return jsonify(cause_list)

@cause_list_bp.route("/api/cause-list/import-karur", methods=["POST"])
def import_karur_endpoint():
    """Imports Uncle's 14 Karur Court hearings sample data."""
    import_karur_sample_data()
    return jsonify({"success": True, "message": "14 Karur Court hearings loaded successfully!"})

@cause_list_bp.route("/api/cause-list/generate-whatsapp", methods=["POST"])
def cause_list_whatsapp():
    """Generates formatted WhatsApp Morning Docket for the advocate."""
    data = request.get_json() or {}
    target_date = data.get("date", "").strip()
    cause_list = get_daily_cause_list(target_date)
    settings = get_advocate_settings()

    firm_name = settings.get("firm_name", "Advocate Chambers").upper()
    lawyer_name = settings.get("lawyer_name", "Senior Advocate")

    msg_lines = [
        f"⚖️ *{firm_name}*",
        f"📋 *DAILY CAUSE LIST & HEARING BOARD*",
        f"📅 *Date:* {cause_list.get('target_date')}",
        f"⚡ *Total Hearings:* {cause_list.get('total_hearings')} across {cause_list.get('total_courts')} Courts",
        "---------------------------------------"
    ]

    for summary in cause_list.get("court_summaries", []):
        msg_lines.append(f"\n🏛️ *{summary.get('court_name').upper()}* ({summary.get('hearings_count')} Cases)")
        for c in summary.get("cases", []):
            item_no = c.get("item_number") or "-"
            room = c.get("court_room") or "-"
            case_no = c.get("case_number_formatted") or c.get("cnr_number")
            stage = c.get("case_stage") or "Hearing"
            judge = c.get("judge_name") or ""

            msg_lines.append(f"• *Item {item_no}* ({room}): {c.get('case_title')}")
            msg_lines.append(f"  └ [{case_no}] Stage: *{stage}*")
            if judge:
                msg_lines.append(f"  └ Judge: {judge}")

    msg_lines.append("\n---------------------------------------")
    msg_lines.append(f"Prepared for: *{lawyer_name}*")

    full_text = "\n".join(msg_lines)
    raw_phone = settings.get("lawyer_phone", "")
    clean_phone = "".join(c for c in raw_phone if c.isdigit())
    wa_link = f"https://wa.me/{clean_phone}?text={full_text}"

    return jsonify({
        "success": True,
        "text": full_text,
        "wa_link": wa_link
    })

@cause_list_bp.route("/api/export-cause-list")
def export_cause_list_print():
    """Generates an A4 Printable Daily Court Hearing Board for advocates matching exact court docket format."""
    target_date = (request.args.get("date") or time.strftime("%Y-%m-%d")).strip()
    cause_list = get_daily_cause_list(target_date)
    settings = get_advocate_settings()
    return render_template("cause_list_print.html", cause_list=cause_list, settings=settings)
