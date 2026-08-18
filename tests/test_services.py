import pytest
from app.services.ecourts_service import parse_ecourts_response, reset_circuit_breaker, API_CIRCUIT_BREAKER
from app.services.whatsapp_service import clean_phone_number, format_legal_notice_text, generate_whatsapp_web_link
from app.services.sync_service import evaluate_case_check_need
from app.services.ai_service import query_agentic_ai

def test_parse_ecourts_response():
    raw_api_payload = {
        "case_details": {
            "title": "M Palanisamy vs M Velmurugan",
            "status": "PENDING",
            "court": "Chief Judicial Magistrate Court, Karur",
            "state": "Tamil Nadu",
            "district": "Karur",
            "next_date": "2026-08-20",
            "last_date": "2026-07-15",
            "petitioners": ["M Palanisamy"],
            "respondents": ["M Velmurugan"],
            "petitioner_advocates": ["R. Anbaiya"],
            "respondent_advocates": ["Advocate K. Suresh"]
        }
    }
    parsed = parse_ecourts_response("TNKR010010352023", raw_api_payload)
    assert parsed["success"] is True
    assert parsed["cnr_number"] == "TNKR010010352023"
    assert parsed["case_title"] == "M Palanisamy vs M Velmurugan"
    assert parsed["court_name"] == "Chief Judicial Magistrate Court, Karur"
    assert parsed["next_hearing_date"] == "2026-08-20"

def test_clean_phone_number():
    assert clean_phone_number("9842112233") == "919842112233"
    assert clean_phone_number("+91 98421 12233") == "919842112233"
    assert clean_phone_number("919842112233") == "919842112233"

def test_format_legal_notice_text():
    case = {
        "client_name": "Kathiravan",
        "case_number_formatted": "OS/359/2024",
        "next_hearing_date": "2026-08-25",
        "court_name": "Principal District Munsif Court, Karur",
        "court_room": "Room 5",
        "item_number": "43",
        "case_stage": "Written Statement"
    }
    settings = {
        "firm_name": "R. ANBAIYA & ASSOCIATES",
        "lawyer_name": "Advocate R. Anbaiya",
        "lawyer_phone": "+919842112233",
        "default_whatsapp_footer": "Sent on behalf of Law Chambers."
    }
    msg = format_legal_notice_text(case, settings)
    assert "OS/359/2024" in msg
    assert "Kathiravan" in msg
    assert "Room 5" in msg
    assert "Written Statement" in msg

def test_generate_whatsapp_web_link():
    link = generate_whatsapp_web_link("9842112233", "Hello Advocate")
    assert link.startswith("https://wa.me/919842112233?text=")
    assert "Hello%20Advocate" in link

def test_evaluate_case_check_need():
    # Disposed Case
    disposed_case = {"cnr_number": "TNKR14", "case_status": "DISPOSED", "next_hearing_date": "2026-08-01"}
    ev_disp = evaluate_case_check_need(disposed_case, today_str="2026-08-18")
    assert ev_disp["should_check"] is False
    assert ev_disp["status_code"] == "DISPOSED"

    # Hearing Far Away (>3 days)
    far_case = {"cnr_number": "TNKR01", "case_status": "PENDING", "next_hearing_date": "2026-08-30"}
    ev_far = evaluate_case_check_need(far_case, today_str="2026-08-18")
    assert ev_far["should_check"] is False
    assert ev_far["status_code"] == "SLEEPING"

    # Hearing Near (Tomorrow)
    near_case = {"cnr_number": "TNKR02", "case_status": "PENDING", "next_hearing_date": "2026-08-19"}
    ev_near = evaluate_case_check_need(near_case, today_str="2026-08-18")
    assert ev_near["should_check"] is True
    assert ev_near["status_code"] == "HEARING_NEAR"
