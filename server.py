import os
import sys
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ecourts_api import fetch_case_details, get_api_key
from db import init_db, upsert_case, get_all_cases

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__, static_folder="static")
CORS(app)

# Initialize DB on startup
init_db()

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
    return jsonify({"configured": has_key, "masked_key": masked, "full_key": key if has_key else ""})

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

@app.route("/api/check-case", methods=["POST"])
def check_case():
    """Fetches case from eCourts API or fallback mock if key not set."""
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

if __name__ == "__main__":
    port = 5000
    print(f"🚀 LegalCase Automation Web Server starting at http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
