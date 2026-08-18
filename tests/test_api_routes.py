import json
import pytest

def test_health_check(client):
    """Verifies health check endpoint returns 200 and expected keys."""
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert "cases_monitored" in data

def test_live_status(client):
    """Verifies live status endpoint."""
    res = client.get("/api/live-status")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_cases" in data
    assert "today_hearings" in data

def test_key_status(client):
    """Verifies key status and credit guard return valid JSON."""
    res = client.get("/api/key-status")
    assert res.status_code == 200
    data = res.get_json()
    assert "configured" in data
    assert "credit_guard" in data

def test_credit_guard(client):
    """Verifies credit guard status endpoint."""
    res = client.get("/api/credit-guard")
    assert res.status_code == 200
    data = res.get_json()
    assert "mode" in data

def test_get_cases(client):
    """Verifies retrieval of stored cases."""
    res = client.get("/api/cases")
    assert res.status_code == 200
    cases = res.get_json()
    assert isinstance(cases, list)
    assert len(cases) > 0

def test_check_case_vault_enrollment(client):
    """Verifies instant enrollment into private chamber vault."""
    payload = {
        "client_name": "Test Litigant",
        "client_phone": "+919876543210",
        "case_title": "Test Litigant vs State",
        "case_number_formatted": "OS/999/2026",
        "court_name": "Principal District Court, Karur",
        "court_room": "Room 1",
        "item_number": "5",
        "case_stage": "Arguments",
        "notes": "Test Strategy Notes"
    }
    res = client.post("/api/check-case", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

def test_get_single_case(client):
    """Verifies single case retrieval by CNR."""
    res = client.get("/api/cases/TNKR010010352023")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["case"]["cnr_number"] == "TNKR010010352023"

def test_case_preferences_update(client):
    """Verifies updating case preferences."""
    pref = {
        "notes": "Updated strategy for trial",
        "track_next_hearing": True,
        "auto_whatsapp_enabled": True
    }
    res = client.put("/api/cases/TNKR010010352023/preferences", json=pref)
    assert res.status_code == 200
    assert res.get_json()["success"] is True

def test_case_status_update(client):
    """Verifies marking case as DISPOSED or PENDING."""
    res = client.put("/api/cases/TNKR010010352023/status", json={"status": "DISPOSED"})
    assert res.status_code == 200
    assert res.get_json()["success"] is True
    assert res.get_json()["status"] == "DISPOSED"

def test_daily_cause_list(client):
    """Verifies cause list grouped response."""
    res = client.get("/api/cause-list")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_hearings" in data
    assert "court_summaries" in data
    assert len(data["court_summaries"]) > 0

def test_cause_list_whatsapp_generator(client):
    """Verifies WhatsApp docket generation."""
    res = client.post("/api/cause-list/generate-whatsapp", json={})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "wa_link" in data
    assert "DAILY CAUSE LIST" in data["text"]

def test_export_cause_list_html(client):
    """Verifies A4 Printable cause list template rendering."""
    res = client.get("/api/export-cause-list")
    assert res.status_code == 200
    assert b"Daily Court Hearing Board" in res.data

def test_export_case_dossier_html(client):
    """Verifies A4 Printable case dossier template rendering."""
    res = client.get("/api/export-case/TNKR010010352023")
    assert res.status_code == 200
    assert b"Advocate Case Brief Dossier" in res.data

def test_leads_crud(client):
    """Verifies prospective client lead creation and retrieval."""
    lead_payload = {
        "client_name": "Prospective Client",
        "client_phone": "+919988776655",
        "matter_type": "Property Partition Suit",
        "expected_court": "Principal District Court, Karur",
        "notes": "Initial consultation needed"
    }
    create_res = client.post("/api/leads", json=lead_payload)
    assert create_res.status_code == 200
    assert create_res.get_json()["success"] is True

    get_res = client.get("/api/leads")
    assert get_res.status_code == 200
    leads = get_res.get_json()
    assert any(l["client_name"] == "Prospective Client" for l in leads)

def test_advocate_settings(client):
    """Verifies advocate firm settings retrieval and updates."""
    res = client.get("/api/advocate-settings")
    assert res.status_code == 200
    settings = res.get_json()
    assert "firm_name" in settings

    update_payload = {
        "firm_name": "R. ANBAIYA & ASSOCIATES",
        "lawyer_name": "Advocate R. Anbaiya",
        "lawyer_phone": "+919842112233"
    }
    post_res = client.post("/api/advocate-settings", json=update_payload)
    assert post_res.status_code == 200
    assert post_res.get_json()["success"] is True

def test_ai_briefing(client):
    """Verifies AI morning briefing generation."""
    res = client.get("/api/ai-briefing")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "briefing_text" in data

def test_ai_assistant_query(client):
    """Verifies JARVIS assistant natural language responses."""
    res = client.post("/api/ai-assistant", json={"prompt": "Show urgent cases today"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "answer" in data

def test_scheduler_evaluation(client):
    """Verifies predictive scheduler evaluation breakdown."""
    res = client.get("/api/scheduler/evaluation")
    assert res.status_code == 200
    data = res.get_json()
    assert "total_cases" in data
    assert "sleeping_cases" in data
    assert "credits_saved_today" in data
