from flask import Blueprint, jsonify, request
from app.db.repository import get_all_cases, get_case_history_logs
from app.db.database import get_current_ist_date
from app.services.sync_service import sync_worker, evaluate_case_check_need

scheduler_bp = Blueprint("scheduler", __name__)

@scheduler_bp.route("/api/scheduler/evaluation", methods=["GET"])
def scheduler_evaluation():
    """Evaluates all portfolio cases and returns sleeping vs active check status with credit calculation."""
    cases = get_all_cases()
    today = get_current_ist_date()

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

@scheduler_bp.route("/api/scheduler/smart-sync", methods=["POST"])
def scheduler_smart_sync():
    """Triggers the Smart Predictive Polling engine (Sleep far away -> Check near -> Compare -> Alert)."""
    result = sync_worker.smart_sync_cases(force_all=False)
    return jsonify(result)

@scheduler_bp.route("/api/sync-all", methods=["POST"])
def sync_all():
    """Triggers batch re-check of all tracked cases."""
    data = request.get_json() or {}
    force_live = bool(data.get("force_live", False))
    result = sync_worker.smart_sync_cases(force_all=force_live)
    return jsonify(result)

@scheduler_bp.route("/api/sync-status", methods=["GET"])
def sync_status():
    """Returns status of background auto-poller and credits saved."""
    return jsonify({
        "running": sync_worker.running,
        "interval_seconds": sync_worker.interval_seconds,
        "last_sync_time": sync_worker.last_sync_time,
        "last_sync_result": sync_worker.last_sync_result,
        "total_credits_saved": sync_worker.total_credits_saved
    })

@scheduler_bp.route("/api/history", methods=["GET"])
def get_history():
    """Returns change audit trail."""
    logs = get_case_history_logs(limit=50)
    return jsonify(logs)
