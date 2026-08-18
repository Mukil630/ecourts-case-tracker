import time
from flask import Blueprint, jsonify, request
from app.services.ai_service import get_ai_daily_briefing, query_agentic_ai

ai_bp = Blueprint("ai", __name__)

@ai_bp.route("/api/ai-briefing")
def ai_briefing_endpoint():
    """Returns AI-generated executive morning briefing for Advocate."""
    date_str = request.args.get("date") or time.strftime("%Y-%m-%d")
    return jsonify(get_ai_daily_briefing(date_str))

@ai_bp.route("/api/ai-assistant", methods=["POST"])
def ai_assistant_endpoint():
    """Interactive JARVIS Agentic Legal Assistant query handler."""
    data = request.get_json() or {}
    prompt = data.get("prompt", "")
    return jsonify(query_agentic_ai(prompt))
