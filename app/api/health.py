import time
from flask import Blueprint, jsonify, request
from app.db.repository import get_all_cases, get_daily_cause_list
from app.db.database import get_current_ist_date
from app.services.sync_service import sync_worker

health_bp = Blueprint("health", __name__)

@health_bp.route("/healthz")
@health_bp.route("/api/health")
def health_check():
    """200 OK Health Check for UptimeRobot & Render Keep-Alive."""
    try:
        cases_count = len(get_all_cases())
    except Exception:
        cases_count = 0
    return jsonify({
        "status": "healthy",
        "service": "ecourts-case-tracker",
        "cases_monitored": cases_count,
        "auto_sync": "running" if sync_worker.running else "stopped",
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
    }), 200

@health_bp.route("/api/live-status")
def live_status_endpoint():
    """Lightweight endpoint for zero-refresh real-time live sync polling."""
    all_cases = get_all_cases()
    today_date = request.args.get("date") or get_current_ist_date()
    today_data = get_daily_cause_list(today_date)
    return jsonify({
        "timestamp": int(time.time()),
        "total_cases": len(all_cases),
        "today_hearings": today_data.get("total_hearings", 0),
        "today_date": today_date,
        "last_updated": time.strftime("%H:%M:%S")
    })
