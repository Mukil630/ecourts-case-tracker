import os
import sys
import json
import time
from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from ecourts_api import fetch_case_details, get_api_key
from db import init_db, upsert_case, get_all_cases, get_case_by_cnr, delete_case, get_case_history_logs, mark_log_notified
from sync_engine import sync_worker

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

@app.route("/api/check-case", methods=["POST"])
def check_case():
    """Fetches case from eCourts API or fallback demo data if key not set."""
    data = request.get_json() or {}
    cnr = (data.get("cnr") or "DLND020047882015").strip().upper()
    client_name = data.get("client_name", "Client")
    client_phone = data.get("client_phone", "+919876543210")

    api_key = get_api_key()

    # If API Key is present, call the real eCourts API
    if api_key:
        api_result = fetch_case_details(cnr)
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
            date_changed = upsert_case(db_payload, client_name=client_name, client_phone=client_phone)
            return jsonify({
                "success": True,
                "date_changed": date_changed,
                "case_data": api_result
            })
        else:
            return jsonify(api_result)

    # Fallback Sample Data for instant testing if key not set yet
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
        "note": "Running in Demo Mode. Add ECOURTS_API_KEY in .env for live API queries."
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
    date_changed = upsert_case(db_payload, client_name=client_name, client_phone=client_phone)

    return jsonify({
        "success": True,
        "date_changed": date_changed,
        "case_data": sample_case
    })

@app.route("/api/sync-all", methods=["POST"])
def sync_all():
    """Triggers batch re-check of all tracked cases."""
    result = sync_worker.sync_all_cases()
    return jsonify(result)

@app.route("/api/sync-status", methods=["GET"])
def sync_status():
    """Returns status of background auto-poller."""
    return jsonify({
        "running": sync_worker.running,
        "interval_seconds": sync_worker.interval_seconds,
        "last_sync_time": sync_worker.last_sync_time,
        "last_sync_result": sync_worker.last_sync_result
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

@app.route("/api/run-agent", methods=["POST"])
def trigger_agent():
    """Runs LangGraph Autonomous Vision Agent in separate thread or fallback."""
    data = request.get_json() or {}
    cnr = (data.get("cnr") or "DLND020047882015").strip().upper()
    try:
        from ecourts_agent_graph import run_agent
        result = run_agent(cnr)
        return jsonify({
            "success": result.get("status") in ["SUCCESS", "COMPLETED"],
            "status": result.get("status"),
            "agent_state": {
                "cnr": cnr,
                "attempt": result.get("attempt"),
                "status": result.get("status"),
                "captcha_text": result.get("captcha_text"),
                "screenshot": "/static/case_result_full.png" if os.path.exists("C:/Users/mukil/ecourts_automation/case_result_full.png") else None
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/export-case/<cnr>")
def export_case(cnr):
    """Renders a printable law firm case summary brief."""
    case = get_case_by_cnr(cnr.upper())
    if not case:
        return "<h3>Case not found in database. Please track it first.</h3>", 404

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Case Summary Brief - {{ case.cnr_number }}</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; color: #1e293b; background: #fff; line-height: 1.6; }
            .header { border-bottom: 3px solid #0f172a; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: center; }
            .title { font-size: 24px; font-weight: 800; color: #0f172a; }
            .badge { background: #0284c7; color: white; padding: 4px 12px; border-radius: 6px; font-size: 14px; font-weight: 600; }
            .section { margin-bottom: 25px; }
            .section-title { font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; font-weight: 700; margin-bottom: 8px; }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .card { background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; }
            .highlight-card { background: #eff6ff; border: 1px solid #bfdbfe; }
            .hearing-date { font-size: 26px; font-weight: 800; color: #0369a1; }
            .footer { margin-top: 50px; border-top: 1px solid #cbd5e1; padding-top: 15px; font-size: 12px; color: #94a3b8; text-align: center; }
            @media print { .no-print { display: none; } body { padding: 0; } }
        </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom: 20px;">
            <button onclick="window.print()" style="padding: 10px 20px; background: #0284c7; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Print / Save as PDF</button>
        </div>

        <div class="header">
            <div>
                <div class="title">⚖️ Case Hearing Brief</div>
                <div style="color: #64748b; font-size: 14px;">Official Legal Case Summary & Client Record</div>
            </div>
            <span class="badge">{{ case.case_status }}</span>
        </div>

        <div class="section">
            <div class="section-title">Case Title & CNR</div>
            <div style="font-size: 20px; font-weight: 700;">{{ case.case_title }}</div>
            <div style="font-family: monospace; font-size: 16px; color: #0284c7; margin-top: 4px;">CNR: {{ case.cnr_number }}</div>
        </div>

        <div class="grid section">
            <div class="card highlight-card">
                <div class="section-title">Next Scheduled Hearing Date</div>
                <div class="hearing-date">{{ case.next_hearing_date or 'Awaiting Schedule / Disposed' }}</div>
            </div>
            <div class="card">
                <div class="section-title">Last Hearing Date</div>
                <div style="font-size: 20px; font-weight: 600; color: #334155; margin-top: 6px;">{{ case.last_hearing_date or 'N/A' }}</div>
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
            <div style="margin-bottom: 8px;"><strong>Parties:</strong> {{ case.parties or 'N/A' }}</div>
            <div><strong>Advocates:</strong> {{ case.advocates or 'N/A' }}</div>
        </div>

        <div class="footer">
            Generated via LegalCase eCourts Automated Management System &bull; Timestamp: {{ case.last_checked_at }}
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, case=case)

if __name__ == "__main__":
    port = 5000
    print(f"🚀 LegalCase Automation Web Server starting at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
