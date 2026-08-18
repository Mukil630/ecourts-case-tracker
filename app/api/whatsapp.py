import time
from flask import Blueprint, jsonify, request
from app.db.repository import (
    get_case_by_cnr,
    get_advocate_settings,
    update_advocate_settings,
    get_daily_cause_list,
    mark_log_notified,
)
from app.services.whatsapp_service import (
    get_meta_config,
    send_meta_whatsapp_message,
    format_legal_notice_text,
)

whatsapp_bp = Blueprint("whatsapp", __name__)

@whatsapp_bp.route("/api/whatsapp/config", methods=["GET", "POST"])
def whatsapp_config_route():
    """Manages Meta WhatsApp Cloud API credentials."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        settings = get_advocate_settings()
        settings["meta_phone_number_id"] = data.get("phone_number_id", "").strip()
        settings["meta_access_token"] = data.get("access_token", "").strip()
        settings["meta_waba_id"] = data.get("waba_id", "").strip()
        settings["auto_dispatch_meta"] = bool(data.get("auto_dispatch", False))
        update_advocate_settings(settings)
        return jsonify({"success": True, "config": get_meta_config()})

    cfg = get_meta_config()
    masked_token = (cfg["token"][:6] + "..." + cfg["token"][-4:]) if len(cfg["token"]) > 10 else ""
    return jsonify({
        "configured": cfg["configured"],
        "phone_number_id": cfg["phone_id"],
        "waba_id": cfg["waba_id"],
        "masked_token": masked_token
    })

@whatsapp_bp.route("/api/whatsapp/test-send", methods=["POST"])
def test_whatsapp_send_route():
    """Sends a verified test message to verify Meta WhatsApp credentials."""
    data = request.get_json(silent=True) or {}
    phone = data.get("phone", "").strip()
    msg = data.get("message") or "⚖️ *Official Test Message from Legal Management System.* Your Official Meta WhatsApp Cloud API integration is active and verified!"
    res = send_meta_whatsapp_message(phone, msg)
    return jsonify(res)

@whatsapp_bp.route("/api/whatsapp/dispatch-single", methods=["POST"])
def dispatch_single_whatsapp_route():
    """Dispatches a single client notice via Official Meta WhatsApp Cloud API."""
    data = request.get_json(silent=True) or {}
    cnr = data.get("cnr_number", "").strip()
    case = get_case_by_cnr(cnr)
    if not case:
        return jsonify({"success": False, "error": "Case not found"}), 404

    settings = get_advocate_settings()
    phone = case.get("client_phone") or data.get("phone", "")
    text = format_legal_notice_text(case, settings)

    res = send_meta_whatsapp_message(phone, text)
    return jsonify(res)

@whatsapp_bp.route("/api/whatsapp/dispatch-all", methods=["POST"])
def dispatch_all_whatsapp_route():
    """Dispatches official notices to all cases scheduled for target_date via Official Meta Cloud API."""
    data = request.get_json(silent=True) or {}
    target_date = (data.get("date") or time.strftime("%Y-%m-%d")).strip()
    cause_list = get_daily_cause_list(target_date)
    settings = get_advocate_settings()

    results = []
    sent_count = 0
    failed_count = 0

    for summary in cause_list.get("court_summaries", []):
        for c in summary.get("cases", []):
            phone = c.get("client_phone")
            if not phone:
                continue
            notice_text = format_legal_notice_text(c, settings)
            res = send_meta_whatsapp_message(phone, notice_text)
            results.append({
                "client": c.get("client_name"),
                "phone": phone,
                "case_no": c.get("case_number_formatted") or c.get("cnr_number"),
                "status": "SENT" if res.get("success") else "FAILED",
                "detail": res.get("message_id") if res.get("success") else res.get("error")
            })
            if res.get("success"):
                sent_count += 1
            else:
                failed_count += 1

    return jsonify({
        "success": True,
        "total": len(results),
        "sent": sent_count,
        "failed": failed_count,
        "dispatches": results
    })

@whatsapp_bp.route("/api/dispatch-alert", methods=["POST"])
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
