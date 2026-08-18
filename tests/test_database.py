import pytest
import os
import tempfile
from app.db.database import init_db, get_db_connection, get_current_ist_date
from app.db.repository import (
    upsert_case,
    get_all_cases,
    get_case_by_cnr,
    delete_case,
    clear_all_cases,
    update_case_preferences,
    get_cached_case,
    set_cached_case,
    get_all_leads,
    add_lead,
    get_case_history_logs,
)

@pytest.fixture
def temp_db():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    init_db(db_path=db_path, auto_seed=False)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

def test_upsert_and_retrieve_case(temp_db):
    case_data = {
        "cnr_number": "TEST010000002026",
        "case_title": "Appellant vs Respondent",
        "case_status": "PENDING",
        "court_name": "Karur Sub Court",
        "next_hearing_date": "2026-09-10"
    }

    changed = upsert_case(
        case_data,
        client_name="Test Client",
        client_phone="+919876543210",
        notes="Important hearing",
        db_path=temp_db
    )
    assert changed is False  # First insert does not trigger date changed

    saved = get_case_by_cnr("TEST010000002026", db_path=temp_db)
    assert saved is not None
    assert saved["client_name"] == "Test Client"
    assert saved["notes"] == "Important hearing"

def test_hearing_date_change_log(temp_db):
    case_data = {
        "cnr_number": "TEST020000002026",
        "case_title": "Case 2",
        "case_status": "PENDING",
        "court_name": "Karur Sub Court",
        "next_hearing_date": "2026-09-10"
    }
    upsert_case(case_data, db_path=temp_db)

    # Update next hearing date
    case_data["next_hearing_date"] = "2026-09-25"
    changed = upsert_case(case_data, db_path=temp_db)
    assert changed is True

    logs = get_case_history_logs(limit=10, db_path=temp_db)
    assert len(logs) > 0
    assert logs[0]["cnr_number"] == "TEST020000002026"
    assert logs[0]["previous_hearing_date"] == "2026-09-10"
    assert logs[0]["new_hearing_date"] == "2026-09-25"

def test_query_cache(temp_db):
    data = {"status": "SUCCESS", "title": "Cached Case"}
    set_cached_case("TESTCACHE01", data, db_path=temp_db)

    cached = get_cached_case("TESTCACHE01", max_age_seconds=3600, db_path=temp_db)
    assert cached is not None
    assert cached["title"] == "Cached Case"

def test_delete_case(temp_db):
    case_data = {
        "cnr_number": "TEST030000002026",
        "case_title": "To Delete",
        "next_hearing_date": "2026-09-10"
    }
    upsert_case(case_data, db_path=temp_db)
    deleted = delete_case("TEST030000002026", db_path=temp_db)
    assert deleted is True
    assert get_case_by_cnr("TEST030000002026", db_path=temp_db) is None
