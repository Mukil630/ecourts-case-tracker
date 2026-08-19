from flask import Blueprint, jsonify, request
from app.services.telegram_service import (
    get_telegram_config,
    auto_detect_chat_id,
    send_telegram_message,
    send_morning_docket_telegram
)
from app.db.repository import get_advocate_settings, update_advocate_settings

telegram_bp = Blueprint("telegram", __name__)

@telegram_bp.route("/api/telegram/status", methods=["GET"])
def telegram_status():
    """Returns Telegram configuration status and bot username."""
    config = get_telegram_config()
    return jsonify({
        "configured": config["configured"],
        "bot_username": "jarvis_prime_remote_bot",
        "has_token": bool(config["token"]),
        "has_chat_id": bool(config["chat_id"]),
        "chat_id": config["chat_id"]
    })

@telegram_bp.route("/api/telegram/save-config", methods=["POST"])
def save_telegram_config():
    """Saves Telegram Bot Token and Chat ID."""
    data = request.get_json() or {}
    token = data.get("bot_token", "").strip()
    chat_id = data.get("chat_id", "").strip()

    updates = {}
    if token:
        updates["telegram_bot_token"] = token
    if chat_id:
        updates["telegram_chat_id"] = chat_id

    if updates:
        update_advocate_settings(updates)
        return jsonify({"success": True, "message": "Telegram configuration saved successfully!"})
    return jsonify({"success": False, "error": "No configuration parameters provided."}), 400

@telegram_bp.route("/api/telegram/sync-chat-id", methods=["POST"])
def sync_chat_id():
    """Attempts to auto-detect chat ID from recent bot /start messages."""
    data = request.get_json() or {}
    token = data.get("bot_token", "").strip() or None
    detected = auto_detect_chat_id(token)
    if detected:
        return jsonify({
            "success": True,
            "chat_id": detected,
            "message": f"Successfully connected! Chat ID: {detected}"
        })
    return jsonify({
        "success": False,
        "error": "No incoming message detected yet. Please open @jarvis_prime_remote_bot on Telegram, press START (or send a message), and try again."
    }), 404

@telegram_bp.route("/api/telegram/send-test", methods=["POST"])
def send_test_message():
    """Sends a verification test alert to Telegram."""
    data = request.get_json() or {}
    chat_id = data.get("chat_id", "").strip() or None

    test_text = (
        "⚡ <b>JARVIS LEGAL BOT CONNECTED!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏛️ <b>eCourts Autonomous Case Tracker</b>\n"
        "👨‍⚖️ <i>R. Anbaiya & Associates, Karur</i>\n\n"
        "✅ <b>Status:</b> Live & Operational\n"
        "📋 <b>Services Active:</b>\n"
        "• 🌅 Daily Court Board Morning Briefings\n"
        "• 🚨 Urgent Warrants & Injunction Alerts\n"
        "• 🔄 Real-time Hearing Date Adjournments\n"
        "• 🎯 Prospective Client Consultation Leads\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 <i>Ready to manage your chamber docket automatically!</i>"
    )
    result = send_telegram_message(test_text, chat_id=chat_id)
    return jsonify(result)

@telegram_bp.route("/api/telegram/dispatch-docket", methods=["POST"])
def dispatch_docket_route():
    """Dispatches the full Daily Cause List hearing docket to Telegram."""
    data = request.get_json() or {}
    target_date = data.get("date", "").strip()
    chat_id = data.get("chat_id", "").strip() or None

    result = send_morning_docket_telegram(target_date, chat_id=chat_id)
    return jsonify(result)
