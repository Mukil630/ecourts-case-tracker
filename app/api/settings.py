from flask import Blueprint, jsonify, request
from app.services.ecourts_service import get_api_key, save_api_key_to_env, get_credit_guard_status
from app.db.repository import get_advocate_settings, update_advocate_settings

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/api/key-status", methods=["GET"])
def key_status():
    """Returns API key configuration state with credit guard status."""
    key = get_api_key()
    has_key = bool(key and key != "your_api_key_here")
    masked = (key[:8] + "..." + key[-4:]) if has_key and len(key) > 12 else ""
    guard = get_credit_guard_status()
    return jsonify({
        "configured": has_key,
        "masked_key": masked,
        "full_key": key if has_key else "",
        "credit_guard": guard
    })

@settings_bp.route("/api/credit-guard", methods=["GET"])
def credit_guard_route():
    """Returns status of credit guard and circuit breaker."""
    return jsonify(get_credit_guard_status())

@settings_bp.route("/api/save-key", methods=["POST"])
def save_key():
    """Saves new eCourts API key and resets circuit breaker."""
    data = request.get_json() or {}
    new_key = data.get("api_key", "").strip()
    if not new_key:
        return jsonify({"success": False, "error": "Key cannot be empty"}), 400

    saved = save_api_key_to_env(new_key)
    if saved:
        masked = new_key[:8] + "..." + new_key[-4:] if len(new_key) > 12 else "***"
        return jsonify({
            "success": True,
            "masked_key": masked,
            "credit_guard": get_credit_guard_status()
        })
    return jsonify({"success": False, "error": "Failed to save key"}), 500

@settings_bp.route("/api/advocate-settings", methods=["GET", "POST"])
def advocate_settings_route():
    """Retrieves or updates advocate law firm settings."""
    if request.method == "POST":
        data = request.get_json() or {}
        update_advocate_settings(data)
        return jsonify({"success": True, "settings": get_advocate_settings()})
    return jsonify(get_advocate_settings())
