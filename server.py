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
    """Generates an A4 Printable Daily Court Hearing Board for advocates."""
    target_date = request.args.get("date", "").strip()
    cause_list = get_daily_cause_list(target_date)
    settings = get_advocate_settings()

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Daily Cause List Board - {{ cause_list.target_date }}</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; color: #0f172a; background: #fff; line-height: 1.5; }
            .header { border-bottom: 3px solid #0f172a; padding-bottom: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
            .firm-name { font-size: 22px; font-weight: 800; }
            .firm-subtitle { font-size: 13px; color: #475569; }
            .badge { background: #0f172a; color: white; padding: 4px 12px; border-radius: 6px; font-size: 13px; font-weight: 700; }
            .court-section { margin-bottom: 24px; break-inside: avoid; }
            .court-title { font-size: 15px; font-weight: 800; background: #f1f5f9; padding: 8px 12px; border-left: 4px solid #0284c7; margin-bottom: 8px; }
            table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 12px; }
            th { background: #e2e8f0; text-align: left; padding: 8px 10px; font-weight: 700; border: 1px solid #cbd5e1; }
            td { padding: 8px 10px; border: 1px solid #cbd5e1; vertical-align: top; }
            .stage-tag { background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 11px; }
            @media print { .no-print { display: none; } body { padding: 0; } }
        </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom: 20px; display: flex; justify-content: space-between;">
            <button onclick="window.print()" style="padding: 10px 20px; background: #0284c7; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Print Daily A4 Board</button>
            <span style="color: #64748b; font-size: 13px;">Daily Court Hearing Docket</span>
        </div>

        <div class="header">
            <div>
                <div class="firm-name">⚖️ {{ settings.firm_name or 'Advocate Chambers' }}</div>
                <div class="firm-subtitle">{{ settings.lawyer_name or 'Senior Advocate' }} &bull; Daily Court Hearing Docket</div>
            </div>
            <div style="text-align: right;">
                <div class="badge">📅 Date: {{ cause_list.target_date }}</div>
                <div style="font-size: 12px; color: #64748b; margin-top: 4px;">Total Hearings: <strong>{{ cause_list.total_hearings }}</strong></div>
            </div>
        </div>

        {% for court in cause_list.court_summaries %}
        <div class="court-section">
            <div class="court-title">🏛️ {{ court.court_name }} ({{ court.hearings_count }} Hearings)</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 60px;">Item</th>
                        <th style="width: 80px;">Room</th>
                        <th style="width: 130px;">Case No / CNR</th>
                        <th>Case Title & Litigant</th>
                        <th style="width: 140px;">Stage</th>
                        <th style="width: 180px;">Presiding Judge</th>
                    </tr>
                </thead>
                <tbody>
                    {% for c in court.cases %}
                    <tr>
                        <td style="font-weight: 800; font-size: 14px; color: #0284c7; text-align: center;">{{ c.item_number or '-' }}</td>
                        <td>{{ c.court_room or '-' }}</td>
                        <td>
                            <strong>{{ c.case_number_formatted or '-' }}</strong><br>
                            <span style="font-family: monospace; font-size: 10px; color: #64748b;">{{ c.cnr_number }}</span>
                        </td>
                        <td>
                            <strong>{{ c.case_title }}</strong><br>
                            <span style="font-size: 11px; color: #475569;">Client: {{ c.client_name or 'Client' }} ({{ c.client_phone or '-' }})</span>
                            {% if c.notes %}
                            <div style="font-size: 10px; color: #b45309; margin-top: 2px;">Note: {{ c.notes }}</div>
                            {% endif %}
                        </td>
                        <td><span class="stage-tag">{{ c.case_stage or 'Hearing' }}</span></td>
                        <td style="font-size: 11px;">{{ c.judge_name or '-' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endfor %}

        <div style="margin-top: 30px; border-top: 1px solid #cbd5e1; padding-top: 10px; font-size: 11px; color: #94a3b8; text-align: center;">
            Generated via Advocate Autonomous Case Engine &bull; Timestamp: {{ cause_list.target_date }}
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, cause_list=cause_list, settings=settings)

@app.route("/api/check-case", methods=["POST"])
def check_case():
    """
    Fetches case from eCourts API (with smart credit-saving cache)
    and saves with Uncle's custom tracking rules.
    """
    data = request.get_json() or {}
    cnr = (data.get("cnr") or "DLND020047882015").strip().upper()
    client_name = data.get("client_name", "Client")
    client_phone = data.get("client_phone", "+919876543210")
    client_email = data.get("client_email", "")
    litigant_role = data.get("litigant_role", "Petitioner / Complainant")
    force_live = bool(data.get("force_live", False))
    
    track_hearing = bool(data.get("track_next_hearing", True))
    track_orders = bool(data.get("track_orders", True))
    track_status = bool(data.get("track_case_status", True))
    auto_wa = bool(data.get("auto_whatsapp_enabled", True))
    notes = data.get("notes", "")
    custom_header = data.get("custom_advocate_header", "Advocate Office Notice")

    api_key = get_api_key()

    if api_key:
        api_result = fetch_case_details(cnr, force_live=force_live)
        if api_result.get("success"):
            db_payload = {
                "cnr_number": api_result.get("cnr_number"),
                "case_title": api_result.get("case_title"),
                "case_status": api_result.get("case_status"),
                "court_name": api_result.get("court_name"),
                "parties": f"Petitioner: {', '.join(api_result.get('petitioners', []))} | Respondent: {', '.join(api_result.get('respondents', []))}",
                "advocates": f"Petitioner Adv: {', '.join(api_result.get('petitioner_advocates', []))} | Respondent Adv: {', '.join(api_result.get('respondent_advocates', []))}",
                "last_hearing_date": api_result.get("last_hearing_date"),
                "next_hearing_date": api_result.get("next_hearing_date")
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
                "is_cached": api_result.get("is_cached", False),
                "cache_note": api_result.get("cache_note", "Live API query used"),
                "case_data": api_result
            })
        else:
            return jsonify(api_result)

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
    """Renders a printable law firm case summary brief with Uncle's firm branding."""
    case = get_case_by_cnr(cnr.upper())
    if not case:
        return "<h3>Case not found in database. Please track it first.</h3>", 404

    settings = get_advocate_settings()

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Case Summary Brief - {{ case.cnr_number }}</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #1e293b; background: #fff; line-height: 1.6; }
            .header { border-bottom: 3px solid #0f172a; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }
            .firm-name { font-size: 24px; font-weight: 800; color: #0f172a; }
            .firm-subtitle { font-size: 14px; color: #64748b; font-weight: 600; }
            .badge { background: #0284c7; color: white; padding: 4px 12px; border-radius: 6px; font-size: 14px; font-weight: 600; }
            .section { margin-bottom: 20px; }
            .section-title { font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; font-weight: 700; margin-bottom: 6px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
            .card { background: #f8fafc; border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; }
            .highlight-card { background: #eff6ff; border: 1px solid #bfdbfe; }
            .hearing-date { font-size: 24px; font-weight: 800; color: #0369a1; }
            .footer { margin-top: 40px; border-top: 1px solid #cbd5e1; padding-top: 15px; font-size: 12px; color: #94a3b8; text-align: center; }
            @media print { .no-print { display: none; } body { padding: 0; } }
        </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom: 20px; display: flex; justify-content: space-between;">
            <button onclick="window.print()" style="padding: 10px 20px; background: #0284c7; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Print / Save as PDF</button>
            <span style="color: #64748b; font-size: 13px;">Official Legal Case Hearing Record</span>
        </div>

        <div class="header">
            <div>
                <div class="firm-name">⚖️ {{ settings.firm_name or 'Law Chambers & Associates' }}</div>
                <div class="firm-subtitle">{{ settings.lawyer_name or 'Senior Advocate' }} &bull; Office Contact: {{ settings.lawyer_phone or '+919876543210' }}</div>
            </div>
            <span class="badge">{{ case.case_status }}</span>
        </div>

        <div class="section">
            <div class="section-title">Case Title & CNR</div>
            <div style="font-size: 18px; font-weight: 700;">{{ case.case_title }}</div>
            <div style="font-family: monospace; font-size: 15px; color: #0284c7; margin-top: 2px;">CNR: {{ case.cnr_number }}</div>
        </div>

        <div class="grid section">
            <div class="card highlight-card">
                <div class="section-title">Next Scheduled Hearing Date</div>
                <div class="hearing-date">{{ case.next_hearing_date or 'Awaiting Schedule / Disposed' }}</div>
            </div>
            <div class="card">
                <div class="section-title">Last Hearing Date</div>
                <div style="font-size: 18px; font-weight: 600; color: #334155; margin-top: 4px;">{{ case.last_hearing_date or 'N/A' }}</div>
            </div>
        </div>

        <div class="grid section">
            <div class="card">
                <div class="section-title">Court & Jurisdiction</div>
                <div style="font-weight: 600;">{{ case.court_name }}</div>
            </div>
            <div class="card">
                <div class="section-title">Client Information</div>
                <div style="font-weight: 600;">{{ case.client_name or 'N/A' }}</div>
                <div style="color: #64748b; font-size: 13px;">Phone: {{ case.client_phone or 'N/A' }}</div>
            </div>
        </div>

        <div class="card section">
            <div class="section-title">Parties & Advocates</div>
            <div style="margin-bottom: 6px;"><strong>Parties:</strong> {{ case.parties or 'N/A' }}</div>
            <div><strong>Advocates:</strong> {{ case.advocates or 'N/A' }}</div>
        </div>

        {% if case.notes %}
        <div class="card section" style="background: #fffbeb; border-color: #fef3c7;">
            <div class="section-title" style="color: #b45309;">Advocate Confidential Notes</div>
            <div>{{ case.notes }}</div>
        </div>
        {% endif %}

        <div class="footer">
            {{ settings.default_whatsapp_footer }} &bull; Generated on: {{ case.last_checked_at }}
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, case=case, settings=settings)

if __name__ == "__main__":
    port = 5000
    print(f"🚀 Advocate Case Automation Web Server starting at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
