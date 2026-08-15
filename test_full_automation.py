import os
import sys
import unittest
import json
from db import (
    init_db, upsert_case, get_all_cases, get_case_by_cnr, delete_case,
    get_case_history_logs, mark_log_notified, update_case_preferences,
    get_advocate_settings, update_advocate_settings, get_cached_case, set_cached_case
)
from ecourts_api import get_api_key, fetch_case_details, fetch_case_by_cnr
from sync_engine import sync_worker
from server import app

class TestFullAutomationSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = app.test_client()

    def test_01_api_key_configured(self):
        key = get_api_key()
        self.assertTrue(bool(key), "API Key should be configured in .env")
        print(f"[TEST PASS] API Key loaded successfully.")

    def test_02_database_operations_and_rules(self):
        test_case = {
            "cnr_number": "TEST010000002026",
            "case_title": "Uncle Client A vs Test Respondent",
            "case_status": "PENDING",
            "court_name": "Madras High Court",
            "parties": "Petitioner: Client A | Respondent: Govt",
            "advocates": "Senior Advocate",
            "last_hearing_date": "2026-08-01",
            "next_hearing_date": "2026-09-01"
        }
        
        # 1. Insert Case with custom automation rules
        changed = upsert_case(
            test_case,
            client_name="Test Client A",
            client_phone="+919876543210",
            track_next_hearing=True,
            track_orders=True,
            track_case_status=True,
            auto_whatsapp_enabled=True,
            notes="Urgent stay application"
        )
        self.assertFalse(changed, "First insert should not trigger date change flag")

        # 2. Query Case & verify rules
        saved = get_case_by_cnr("TEST010000002026")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["client_name"], "Test Client A")
        self.assertEqual(saved["notes"], "Urgent stay application")
        self.assertTrue(bool(saved["track_next_hearing"]))

        # 3. Update Preferences
        updated = update_case_preferences("TEST010000002026", {
            "notes": "Updated note: Hearing posted for arguments",
            "auto_whatsapp_enabled": False
        })
        self.assertTrue(updated)
        saved_updated = get_case_by_cnr("TEST010000002026")
        self.assertEqual(saved_updated["notes"], "Updated note: Hearing posted for arguments")

        # 4. Update Hearing Date (Date Shift Trigger)
        test_case["next_hearing_date"] = "2026-09-20"
        date_changed = upsert_case(test_case, client_name="Test Client A", client_phone="+919876543210")
        self.assertTrue(date_changed, "Hearing date change must trigger date_changed = True")

        # 5. Verify History Log
        logs = get_case_history_logs()
        matching = [l for l in logs if l["cnr_number"] == "TEST010000002026"]
        self.assertTrue(len(matching) > 0, "Date change must be recorded in case_history_logs")
        self.assertEqual(matching[0]["previous_hearing_date"], "2026-09-01")
        self.assertEqual(matching[0]["new_hearing_date"], "2026-09-20")

        # 6. Clean up
        deleted = delete_case("TEST010000002026")
        self.assertTrue(deleted, "Case should be cleanly deleted")
        print("[TEST PASS] Database CRUD and Uncle's Automation Rules verified.")

    def test_03_credit_guard_caching(self):
        # Test cache insertion and instant retrieval
        cnr = "CACHE0199992026"
        dummy_json = {
            "data": {
                "courtCaseData": {
                    "caseTitle": "Cache Test vs Indian Judiciary",
                    "nextHearingDate": "2026-10-10",
                    "caseStatus": "PENDING"
                }
            }
        }
        set_cached_case(cnr, dummy_json)
        cached = get_cached_case(cnr)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["data"]["courtCaseData"]["caseTitle"], "Cache Test vs Indian Judiciary")

        # Fetch case via ecourts_api with force_live=False (must return cached, 0 credits!)
        res = fetch_case_details(cnr, force_live=False)
        self.assertTrue(res.get("is_cached"))
        print("[TEST PASS] Credit-Guard Cache verified (0 credits consumed).")

    def test_04_advocate_firm_settings(self):
        settings = get_advocate_settings()
        self.assertTrue(bool(settings.get("firm_name")))
        
        # Test update
        update_advocate_settings({
            "lawyer_name": "Advocate Ramesh",
            "firm_name": "Ramesh & Associates Legal Chambers",
            "lawyer_phone": "+919123456789",
            "default_whatsapp_footer": "Official Chambers Notice"
        })
        new_settings = get_advocate_settings()
        self.assertEqual(new_settings["lawyer_name"], "Advocate Ramesh")
        self.assertEqual(new_settings["firm_name"], "Ramesh & Associates Legal Chambers")
        print("[TEST PASS] Advocate Firm Branding Settings verified.")

    def test_05_server_endpoints(self):
        # 1. Key Status
        res = self.client.get("/api/key-status")
        self.assertEqual(res.status_code, 200)

        # 2. List Cases
        res = self.client.get("/api/cases")
        self.assertEqual(res.status_code, 200)

        # 3. Advocate Settings
        res = self.client.get("/api/advocate-settings")
        self.assertEqual(res.status_code, 200)

        # 4. History Logs
        res = self.client.get("/api/history")
        self.assertEqual(res.status_code, 200)

        print("[TEST PASS] All Flask REST API Endpoints verified.")

if __name__ == "__main__":
    unittest.main()
