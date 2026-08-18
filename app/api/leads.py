from flask import Blueprint, jsonify, request
from app.db.repository import get_all_leads, add_lead, update_lead_status

leads_bp = Blueprint("leads", __name__)

@leads_bp.route("/api/leads", methods=["GET", "POST"])
def leads_endpoint():
    """Retrieves or adds prospective client inquiries."""
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
