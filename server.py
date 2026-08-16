import os
import sys
import json
import time
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from ecourts_api import fetch_case_details, get_api_key
from db import (
    init_db, upsert_case, get_all_cases, get_case_by_cnr, delete_case, clear_all_cases,
    get_case_history_logs, mark_log_notified, update_case_preferences,
    get_advocate_settings, update_advocate_settings, get_daily_cause_list,
    import_karur_sample_data
)

from sync_engine import sync_worker, evaluate_case_check_need

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__, static_folder="static")
CORS(app)

# Initialize DB and start Background Auto-Poller on startup
init_db()
sync_worker.start()

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory("static", path)

@app.route("/api/key-status", methods=["GET"])
def key_status():
    key = get_api_key()
    has_key = bool(key and key != "your_api_key_here")
    masked = (key[:8] + "..." + key[-4:]) if has_key and len(key) > 12 else ""
    return jsonify({
        "configured": has_key,
        "masked_key": masked,
        "full_key": key if has_key else ""
    })

@app.route("/api/save-key", methods=["POST"])
def save_key():
    data = request.get_json() or {}
    new_key = data.get("api_key", "").strip()
    if not new_key:
        return jsonify({"success": False, "error": "Key cannot be empty"}), 400
    
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"# eCourts API Key Configuration\nECOURTS_API_KEY={new_key}\n")
    
    os.environ["ECOURTS_API_KEY"] = new_key
    return jsonify({"success": True, "masked_key": new_key[:8] + "..." + new_key[-4:] if len(new_key) > 12 else "***"})

@app.route("/api/cases", methods=["GET"])
def list_cases():
    """Returns all stored cases from SQLite."""
    cases = get_all_cases()
    if not cases:
        try:
            import_karur_sample_data()
            cases = get_all_cases()
        except Exception:
            pass
    return jsonify(cases)

@app.route("/api/cases/clear-all", methods=["DELETE", "POST"])
def clear_all_endpoint():
    """Purges all cases and logs for a clean database."""
    clear_all_cases()
    return jsonify({"success": True, "message": "All cases and logs cleared."})

@app.route("/api/cases/<cnr>", methods=["GET"])
def get_case(cnr):

    case = get_case_by_cnr(cnr.upper())
    if case:
        return jsonify({"success": True, "case": case})
    return jsonify({"success": False, "error": "Case not found"}), 404

@app.route("/api/cases/<cnr>", methods=["DELETE"])
def remove_case(cnr):
    deleted = delete_case(cnr.upper())
    return jsonify({"success": deleted})

@app.route("/api/cases/<cnr>/preferences", methods=["PUT"])
def update_preferences(cnr):
    data = request.get_json() or {}
    success = update_case_preferences(cnr.upper(), data)
    return jsonify({"success": success})

@app.route("/api/advocate-settings", methods=["GET", "POST"])
def advocate_settings_route():
    if request.method == "POST":
        data = request.get_json() or {}
        update_advocate_settings(data)
        return jsonify({"success": True, "settings": get_advocate_settings()})
    return jsonify(get_advocate_settings())

@app.route("/api/cause-list", methods=["GET"])
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

@app.route("/api/cause-list/import-karur", methods=["POST"])
def import_karur_endpoint():
    """Imports Uncle's 14 Karur Court hearings sample data."""
    import_karur_sample_data()
    return jsonify({"success": True, "message": "14 Karur Court hearings loaded successfully!"})

@app.route("/api/cause-list/generate-whatsapp", methods=["POST"])
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

@app.route("/api/export-cause-list")
def export_cause_list_print():
    """Generates an A4 Printable Daily Court Hearing Board for advocates matching exact court docket format."""
    target_date = request.args.get("date", "2026-08-14").strip()
    cause_list = get_daily_cause_list(target_date)
    settings = get_advocate_settings()

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Daily Court Cause List - {{ cause_list.target_date }} - {{ settings.firm_name }}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
            
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Plus Jakarta Sans', sans-serif; padding: 24px 30px; color: #0f172a; background: #fff; line-height: 1.4; }
            
            .header-banner { border-bottom: 2.5px solid #0f172a; padding-bottom: 12px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-start; }
            .firm-title { font-size: 20px; font-weight: 800; color: #0f172a; letter-spacing: -0.3px; }
            .firm-sub { font-size: 12px; color: #475569; font-weight: 600; margin-top: 2px; }
            .date-badge { background: #0f172a; color: white; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 700; text-align: right; }
            
            .summary-card { background: #f8fafc; border: 1.5px solid #cbd5e1; border-radius: 6px; padding: 12px 16px; margin-bottom: 20px; }
            .summary-title { font-size: 12px; font-weight: 800; color: #334155; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }
            .summary-table { width: 100%; border-collapse: collapse; font-size: 12px; }
            .summary-table th { text-align: left; padding: 4px 8px; font-weight: 700; color: #475569; border-bottom: 1px solid #cbd5e1; }
            .summary-table td { padding: 4px 8px; border-bottom: 1px solid #f1f5f9; }
            
            .court-section { margin-bottom: 18px; break-inside: avoid; }
            .court-header { background: #0f172a; color: #fff; padding: 6px 10px; font-size: 12px; font-weight: 800; border-radius: 4px 4px 0 0; text-transform: uppercase; letter-spacing: 0.5px; display: flex; justify-content: space-between; }
            
            .hearing-table { width: 100%; border-collapse: collapse; font-size: 11.5px; border: 1px solid #cbd5e1; border-top: none; }
            .hearing-table th { background: #f1f5f9; text-align: left; padding: 6px 8px; font-weight: 700; border-bottom: 1px solid #cbd5e1; border-right: 1px solid #e2e8f0; font-size: 10.5px; color: #475569; text-transform: uppercase; }
            .hearing-table td { padding: 8px; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #f1f5f9; vertical-align: middle; }
            
            .item-badge { display: inline-flex; align-items: center; justify-content: center; background: #0284c7; color: #fff; font-weight: 800; font-size: 13px; width: 34px; height: 34px; border-radius: 6px; }
            .case-num { font-weight: 800; font-size: 12px; color: #0f172a; }
            .cnr-tag { font-family: 'JetBrains Mono', monospace; font-size: 9.5px; color: #64748b; }
            .case-title { font-weight: 700; font-size: 12px; color: #0f172a; margin-bottom: 2px; }
            .stage-pill { display: inline-block; background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 10px; }
            .status-confirmed { color: #166534; font-weight: 800; font-size: 11px; }
            
            .no-print-bar { background: #f8fafc; border: 1px solid #cbd5e1; padding: 10px 16px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
            .btn-action { padding: 8px 16px; border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer; border: none; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
            .btn-print { background: #0284c7; color: #fff; }
            .btn-wa { background: #16a34a; color: #fff; }

            @media print {
                .no-print-bar { display: none !important; }
                body { padding: 10mm; font-size: 10.5pt; }
                .court-section { break-inside: avoid; margin-bottom: 14px; }
                @page { margin: 8mm; size: A4 portrait; }
            }
        </style>
    </head>
    <body>
        <div class="no-print-bar">
            <div>
                <strong>🖨️ Daily Court Hearing Board • A4 Docket</strong>
                <span style="font-size: 12px; color: #64748b; margin-left: 8px;">Date: {{ cause_list.target_date }} &bull; Total Confirmed Hearings: <strong>{{ cause_list.total_hearings }}</strong></span>
            </div>
            <div style="display: flex; gap: 10px;">
                <button onclick="window.print()" class="btn-action btn-print">🖨️ Print / Save as PDF</button>
            </div>
        </div>

        <div class="header-banner">
            <div>
                <div class="firm-title">⚖️ {{ settings.firm_name or 'R. ANBAIYA & ASSOCIATES' }}</div>
                <div class="firm-sub">{{ settings.lawyer_name or 'Advocate R. Anbaiya' }} &bull; Advocates & Legal Consultants, Karur &bull; Daily Court Hearing Board</div>
            </div>
            <div class="date-badge">
                <div>📅 Hearings for {{ cause_list.target_date }}</div>
                <div style="font-size: 11px; opacity: 0.85; margin-top: 2px;">{{ cause_list.total_hearings }} Hearings Confirmed</div>
            </div>
        </div>

        <!-- 1. SUMMARY BREAKDOWN TABLE -->
        <div class="summary-card">
            <div class="summary-title">📊 SUMMARY &bull; COURT COMPLEX BREAKDOWN</div>
            <table class="summary-table">
                <thead>
                    <tr>
                        <th style="width: 45px;">S.NO</th>
                        <th>COURT NAME</th>
                        <th style="width: 100px; text-align: right;">CONFIRMED</th>
                    </tr>
                </thead>
                <tbody>
                    {% for court in cause_list.court_summaries %}
                    <tr>
                        <td><strong>{{ loop.index }}</strong></td>
                        <td>{{ court.court_name }}</td>
                        <td style="text-align: right; font-weight: 800; color: #0284c7;">{{ court.hearings_count }}</td>
                    </tr>
                    {% endfor %}
                    <tr style="font-weight: 800; background: #e2e8f0;">
                        <td colspan="2" style="text-align: right;">TOTAL CONFIRMED HEARINGS:</td>
                        <td style="text-align: right; color: #0f172a;">{{ cause_list.total_hearings }}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- 2. DETAILED COURT SECTIONS -->
        {% for court in cause_list.court_summaries %}
        <div class="court-section">
            <div class="court-header">
                <span>🏛️ {{ court.court_name }}</span>
                <span>{{ court.hearings_count }} Confirmed Hearing{% if court.hearings_count > 1 %}s{% endif %}</span>
            </div>
            <table class="hearing-table">
                <thead>
                    <tr>
                        <th style="width: 50px; text-align: center;">ITEM</th>
                        <th style="width: 90px;">ROOM</th>
                        <th style="width: 130px;">FILE NUMBER</th>
                        <th>CASE TITLE & CLIENT</th>
                        <th style="width: 150px;">JUDGE</th>
                        <th style="width: 130px;">STAGE</th>
                        <th style="width: 75px; text-align: right;">STATUS</th>
                    </tr>
                </thead>
                <tbody>
                    {% for c in court.cases %}
                    <tr>
                        <td style="text-align: center;">
                            <span class="item-badge">{{ c.item_number or '-' }}</span>
                        </td>
                        <td>
                            <strong>{{ c.court_room or '-' }}</strong>
                        </td>
                        <td>
                            <div class="case-num">{{ c.case_number_formatted or c.cnr_number }}</div>
                            <div class="cnr-tag">{{ c.cnr_number }}</div>
                        </td>
                        <td>
                            <div class="case-title">{{ c.case_title }}</div>
                            <div style="font-size: 11px; color: #475569;">
                                👤 <strong>{{ c.client_name or 'Client' }}</strong> ({{ c.client_phone or '-' }})
                                {% if c.notes %}
                                &bull; <span style="color: #b45309; font-weight: 600;">Note: {{ c.notes }}</span>
                                {% endif %}
                            </div>
                        </td>
                        <td style="font-size: 11px; color: #334155;">
                            {{ c.judge_name or '-' }}
                        </td>
                        <td>
                            <span class="stage-pill">{{ c.case_stage or 'Evidence' }}</span>
                        </td>
                        <td style="text-align: right;">
                            <span class="status-confirmed">✓ Confirmed</span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endfor %}

        <div style="margin-top: 24px; border-top: 1.5px solid #cbd5e1; padding-top: 8px; font-size: 10.5px; color: #64748b; display: flex; justify-content: space-between;">
            <span>Prepared for: <strong>{{ settings.lawyer_name or 'Advocate R. Anbaiya' }}</strong> (Karur Bar)</span>
            <span>Generated via Autonomous eCourts Platform &bull; Date: {{ cause_list.target_date }}</span>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, cause_list=cause_list, settings=settings)


@app.route("/api/check-case", methods=["POST"])
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
    
    # Case Number Formatted vs CNR
    case_number_formatted = data.get("case_number_formatted") or raw_input_no
    cnr = raw_input_no.replace(" ", "").replace("/", "-")
    
    client_email = data.get("client_email", "")
    litigant_role = data.get("litigant_role", "Petitioner / Complainant")
    court_name = data.get("court_name") or "Principal Sub Court, Karur"
    court_room = data.get("court_room") or "Room 1"
    item_number = data.get("item_number") or "1"
    case_stage = data.get("case_stage") or "Evidence"
    notes = data.get("notes") or ""
    next_hearing_date = data.get("next_hearing_date") or "2026-08-14"
    force_live = bool(data.get("force_live", False))

    api_key = get_api_key()

    # Try live eCourts if 16-char CNR
    if api_key and len(cnr) == 16 and not "-" in cnr:
        try:
            api_result = fetch_case_details(cnr, force_live=force_live)
            if api_result.get("success"):
                db_payload = {
                    "cnr_number": api_result.get("cnr_number") or cnr,
                    "case_title": api_result.get("case_title") or f"{client_name} Matter",
                    "case_status": api_result.get("case_status") or "PENDING",
                    "court_name": api_result.get("court_name") or court_name,
                    "parties": f"Petitioner: {', '.join(api_result.get('petitioners', []))} | Respondent: {', '.join(api_result.get('respondents', []))}",
                    "advocates": f"Petitioner Adv: {', '.join(api_result.get('petitioner_advocates', []))} | Respondent Adv: {', '.join(api_result.get('respondent_advocates', []))}",
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
                    case_number_formatted=case_number_formatted,
                    case_stage=case_stage,
                    court_room=court_room,
                    item_number=item_number
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

@app.route("/api/search-advocate-cases", methods=["GET", "POST"])
def search_advocate_cases_endpoint():
    """Searches cases registered under Advocate Name on eCourts / Karur."""
    if request.method == "POST":
        data = request.get_json() or {}
        advocate_name = data.get("advocate_name", "Advocate R. Anbaiya")
        district = data.get("district", "Karur")
    else:
        advocate_name = request.args.get("name", "Advocate R. Anbaiya")
        district = request.args.get("district", "Karur")

    from ecourts_api import search_cases_by_advocate
    results = search_cases_by_advocate(advocate_name, district=district)
    return jsonify(results)

@app.route("/api/ai-briefing")
def ai_briefing_endpoint():
    """Returns AI-generated executive morning briefing for Advocate."""
    from ai_agent import get_ai_daily_briefing
    date_str = request.args.get("date", "2026-08-14")
    return jsonify(get_ai_daily_briefing(date_str))

@app.route("/api/ai-assistant", methods=["POST"])
def ai_assistant_endpoint():
    """Interactive JARVIS Agentic Legal Assistant query handler."""
    data = request.get_json() or {}
    prompt = data.get("prompt", "")
    from ai_agent import query_agentic_ai
    return jsonify(query_agentic_ai(prompt))

@app.route("/api/leads", methods=["GET", "POST"])
def leads_endpoint():
    """Retrieves or adds prospective client inquiries."""
    from db import get_all_leads, add_lead, update_lead_status
    if request.method == "POST":
        data = request.get_json() or {}
        client_name = data.get("client_name", "New Lead")
        client_phone = data.get("client_phone", "")
        matter_type = data.get("matter_type", "Civil Dispute")
        expected_court = data.get("expected_court", "Principal Sub Court, Karur")
        notes = data.get("notes", "")
        lead_id = add_lead(client_name, client_phone, matter_type, expected_court, notes)
        return jsonify({"success": True, "lead_id": lead_id, "message": "Lead registered successfully"})
    else:
        return jsonify(get_all_leads())

@app.route("/api/live-status")
def live_status_endpoint():
    """Lightweight endpoint for zero-refresh real-time live sync polling."""
    from db import get_all_cases, get_daily_cause_list
    all_c = get_all_cases()
    today_data = get_daily_cause_list("2026-08-14")
    return jsonify({
        "timestamp": int(time.time()),
        "total_cases": len(all_c),
        "today_hearings": today_data.get("total_hearings", 0),
        "last_updated": time.strftime("%H:%M:%S")
    })





    # Fallback Sample Data for demo mode
    sample_case = {
        "success": True,
        "cnr_number": cnr,
        "case_title": "Mr. Arun Jaitley vs Mr. Arvind Kejriwal",
        "case_status": "DISPOSED",
        "court_name": "Chief Metropolitan Magistrate, New Delhi, PHC",
        "district": "New Delhi",
        "state": "DL",
        "next_hearing_date": "2026-08-28",
        "last_hearing_date": "2026-07-07",
        "hearing_count": 25,
        "order_count": 10,
        "is_mock": True,
        "is_cached": True,
        "cache_note": "Demo Mode (0 credits used)"
    }

    db_payload = {
        "cnr_number": cnr,
        "case_title": sample_case["case_title"],
        "case_status": sample_case["case_status"],
        "court_name": sample_case["court_name"],
        "parties": "Petitioner: Arun Jaitley | Respondent: Arvind Kejriwal",
        "advocates": "Adv. S. Sharma",
        "last_hearing_date": sample_case["last_hearing_date"],
        "next_hearing_date": sample_case["next_hearing_date"]
    }
    date_changed = upsert_case(
        db_payload,
        client_name=client_name,
        client_phone=client_phone,
        client_email=client_email,
        litigant_role=litigant_role,
        track_next_hearing=track_hearing,
        track_orders=track_orders,
        track_case_status=track_status,
        auto_whatsapp_enabled=auto_wa,
        notes=notes,
        custom_advocate_header=custom_header
    )


    return jsonify({
        "success": True,
        "date_changed": date_changed,
        "is_cached": True,
        "case_data": sample_case
    })

@app.route("/api/scheduler/evaluation", methods=["GET"])
def scheduler_evaluation():
    """Evaluates all portfolio cases and returns sleeping vs active check status with credit calculation."""
    cases = get_all_cases()
    today = time.strftime("%Y-%m-%d")
    
    evaluations = []
    sleeping_count = 0
    checked_count = 0
    disposed_count = 0

    for c in cases:
        ev = evaluate_case_check_need(c)
        ev["client_name"] = c.get("client_name")
        ev["case_title"] = c.get("case_title")
        ev["court_name"] = c.get("court_name")
        ev["next_hearing_date"] = c.get("next_hearing_date")
        ev["item_number"] = c.get("item_number")
        ev["court_room"] = c.get("court_room")
        evaluations.append(ev)

        if ev["status_code"] == "DISPOSED":
            disposed_count += 1
        elif not ev["should_check"]:
            sleeping_count += 1
        else:
            checked_count += 1

    return jsonify({
        "today": today,
        "total_cases": len(cases),
        "sleeping_cases": sleeping_count,
        "disposed_cases": disposed_count,
        "due_cases": checked_count,
        "credits_needed_today": checked_count * 1.5,
        "credits_saved_today": (sleeping_count + disposed_count) * 1.5,
        "evaluations": evaluations
    })

@app.route("/api/scheduler/smart-sync", methods=["POST"])
def scheduler_smart_sync():
    """Triggers the Smart Predictive Polling engine (Sleep far away -> Check near -> Compare -> Alert)."""
    result = sync_worker.smart_sync_cases(force_all=False)
    return jsonify(result)

@app.route("/api/sync-all", methods=["POST"])
def sync_all():
    """Triggers batch re-check of all tracked cases."""
    data = request.get_json() or {}
    force_live = bool(data.get("force_live", False))
    result = sync_worker.smart_sync_cases(force_all=force_live)
    return jsonify(result)


@app.route("/api/sync-status", methods=["GET"])
def sync_status():
    """Returns status of background auto-poller and credits saved."""
    return jsonify({
        "running": sync_worker.running,
        "interval_seconds": sync_worker.interval_seconds,
        "last_sync_time": sync_worker.last_sync_time,
        "last_sync_result": sync_worker.last_sync_result,
        "total_credits_saved": sync_worker.total_credits_saved
    })

@app.route("/api/history", methods=["GET"])
def get_history():
    """Returns change audit trail."""
    logs = get_case_history_logs(limit=50)
    return jsonify(logs)

@app.route("/api/dispatch-alert", methods=["POST"])
def dispatch_alert():
    """Simulates/records alert dispatch to client."""
    data = request.get_json() or {}
    cnr = data.get("cnr", "")
    phone = data.get("phone", "")
    message = data.get("message", "")
    log_id = data.get("log_id")

    if log_id:
        mark_log_notified(log_id)

    return jsonify({
        "success": True,
        "status": "DISPATCHED",
        "recipient": phone,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "channel": "WhatsApp"
    })

@app.route("/api/export-case/<cnr>")
def export_case(cnr):
    """Renders an ultra-detailed, prestigious legal case dossier brief for Advocate R. Anbaiya & Associates."""
    case = get_case_by_cnr(cnr.upper())
    if not case:
        return "<h3>Case not found in database. Please track it first.</h3>", 404

    settings = get_advocate_settings()

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Case Dossier Brief - {{ case.case_number_formatted or case.cnr_number }} - {{ settings.firm_name }}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Plus Jakarta Sans', sans-serif; padding: 30px 40px; color: #0f172a; background: #fff; line-height: 1.5; }
            
            .header { border-bottom: 2.5px solid #0f172a; padding-bottom: 14px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-start; }
            .firm-name { font-size: 22px; font-weight: 800; color: #0f172a; letter-spacing: -0.3px; }
            .firm-subtitle { font-size: 12px; color: #475569; font-weight: 600; margin-top: 2px; }
            
            .badge { background: #0f172a; color: white; padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; }
            .badge-stage { background: #0284c7; color: #fff; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 700; }
            
            .section { margin-bottom: 16px; }
            .section-title { font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: #64748b; font-weight: 800; margin-bottom: 6px; border-bottom: 1px solid #e2e8f0; padding-bottom: 3px; }
            
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
            .card { background: #f8fafc; border: 1.5px solid #e2e8f0; padding: 14px; border-radius: 6px; }
            .highlight-card { background: #f0f9ff; border: 1.5px solid #bae6fd; }
            
            .hearing-date { font-size: 22px; font-weight: 800; color: #0284c7; margin-top: 2px; }
            .item-badge { display: inline-flex; align-items: center; justify-content: center; background: #0284c7; color: #fff; font-weight: 800; font-size: 15px; width: 36px; height: 36px; border-radius: 6px; }
            
            .footer { margin-top: 30px; border-top: 1.5px solid #cbd5e1; padding-top: 12px; font-size: 11px; color: #64748b; display: flex; justify-content: space-between; }
            
            .no-print { background: #f8fafc; border: 1px solid #cbd5e1; padding: 10px 16px; border-radius: 6px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
            @media print {
                .no-print { display: none !important; }
                body { padding: 10mm; font-size: 11pt; }
                @page { margin: 10mm; size: A4 portrait; }
            }
        </style>
    </head>
    <body>
        <div class="no-print">
            <div>
                <strong>🖨️ Advocate Case Brief Dossier</strong>
                <span style="font-size: 12px; color: #64748b; margin-left: 8px;">Case: {{ case.case_number_formatted or case.cnr_number }}</span>
            </div>
            <button onclick="window.print()" style="padding: 8px 16px; background: #0284c7; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: 700; font-size: 12px;">🖨️ Print / Save as PDF</button>
        </div>

        <!-- Law Chamber Header -->
        <div class="header">
            <div>
                <div class="firm-name">⚖️ {{ settings.firm_name or 'R. ANBAIYA & ASSOCIATES' }}</div>
                <div class="firm-subtitle">{{ settings.lawyer_name or 'Advocate R. Anbaiya' }} &bull; Advocates & Legal Consultants &bull; Karur Bar Association</div>
                <div style="font-size: 11px; color: #64748b; margin-top: 2px;">Office Helpline: {{ settings.lawyer_phone or '+919842112233' }}</div>
            </div>
            <div style="text-align: right;">
                <span class="badge">{{ case.case_status or 'PENDING' }}</span>
                <div style="font-size: 11px; color: #64748b; margin-top: 4px;">Record Key: {{ case.id }}</div>
            </div>
        </div>

        <!-- 1. Case Identity Header -->
        <div class="card section" style="background: #ffffff; border: 1.5px solid #0f172a;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 18px; font-weight: 800; color: #0f172a;">{{ case.case_title }}</div>
                    <div style="font-size: 13px; font-weight: 700; color: #0284c7; margin-top: 2px;">
                        Case No: {{ case.case_number_formatted or '-' }} &bull; 
                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #475569;">CNR: {{ case.cnr_number }}</span>
                    </div>
                </div>
                <div style="text-align: center;">
                    <div class="item-badge">#{{ case.item_number or '-' }}</div>
                    <div style="font-size: 10px; font-weight: 700; color: #64748b; margin-top: 2px;">DAILY ITEM</div>
                </div>
            </div>
        </div>

        <!-- 2. Hearing Schedule & Stage -->
        <div class="grid section">
            <div class="card highlight-card">
                <div class="section-title">📅 NEXT SCHEDULED HEARING</div>
                <div class="hearing-date">{{ case.next_hearing_date or 'Awaiting Schedule' }}</div>
                <div style="margin-top: 6px;">
                    <span class="badge-stage">{{ case.case_stage or 'Evidence' }}</span>
                </div>
            </div>
            <div class="card">
                <div class="section-title">🏛️ COURT ROOM & PRESIDING JUDGE</div>
                <div style="font-size: 15px; font-weight: 800; color: #0f172a;">{{ case.court_name }}</div>
                <div style="font-size: 13px; font-weight: 700; color: #0284c7; margin-top: 2px;">Court Room: {{ case.court_room or '-' }}</div>
                <div style="font-size: 12px; color: #475569; margin-top: 2px;">Presiding: <strong>{{ case.judge_name or '-' }}</strong></div>
            </div>
        </div>

        <!-- 3. Client & Litigant Representation -->
        <div class="grid section">
            <div class="card">
                <div class="section-title">👤 CLIENT INFORMATION</div>
                <div style="font-size: 15px; font-weight: 800; color: #0f172a;">{{ case.client_name or 'Client' }}</div>
                <div style="font-size: 12px; color: #475569; margin-top: 2px;">Role: <strong>{{ case.litigant_role or 'Petitioner / Complainant' }}</strong></div>
                <div style="font-size: 12px; color: #0284c7; margin-top: 2px; font-weight: 700;">WhatsApp: {{ case.client_phone or '-' }}</div>
            </div>
            <div class="card">
                <div class="section-title">⚖️ PARTIES & ADVOCATES</div>
                <div style="font-size: 12px; color: #334155; margin-bottom: 4px;"><strong>Parties:</strong> {{ case.parties or case.case_title }}</div>
                <div style="font-size: 12px; color: #334155;"><strong>Advocate:</strong> {{ case.advocates or settings.lawyer_name or 'Advocate R. Anbaiya' }}</div>
            </div>
        </div>

        <!-- 4. Advocate Confidential Strategy Notes -->
        {% if case.notes %}
        <div class="card section" style="background: #fffbeb; border: 1.5px solid #fef3c7;">
            <div class="section-title" style="color: #b45309;">📝 ADVOCATE CONFIDENTIAL STRATEGY NOTES</div>
            <div style="font-size: 13px; font-weight: 700; color: #92400e;">{{ case.notes }}</div>
        </div>
        {% endif %}

        <!-- 5. Footer & Chamber Signature -->
        <div class="footer">
            <div>
                <div>{{ settings.default_whatsapp_footer }}</div>
                <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">Last Verified on eCourts: {{ case.last_checked_at }}</div>
            </div>
            <div style="text-align: right;">
                <div style="height: 30px;"></div>
                <div style="border-top: 1px solid #0f172a; font-weight: 800; font-size: 11px;">Advocate Signature & Seal</div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, case=case, settings=settings)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Advocate Case Automation Web Server starting on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)

