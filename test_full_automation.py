import os
import sys
import unittest
import json
from db import init_db, upsert_case, get_all_cases, get_case_by_cnr, delete_case, get_case_history_logs, mark_log_notified
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

    def test_02_database_operations(self):
        test_case = {
            "cnr_number": "TEST010000002026",
            "case_title": "Unit Test Party A vs Unit Test Party B",
            "case_status": "PENDING",
            "court_name": "Delhi High Court",
            "parties": "Petitioner: Unit Test | Respondent: Test Corp",
            "advocates": "Adv. Test",
            "last_hearing_date": "2026-08-01",
            "next_hearing_date": "2026-09-01"
        }
        
        # 1. Insert Case
        changed = upsert_case(test_case, client_name="Test Client", client_phone="+919000000000")
        self.assertFalse(changed, "First insert should not trigger date change flag")

        # 2. Query Case
        saved = get_case_by_cnr("TEST010000002026")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["case_title"], "Unit Test Party A vs Unit Test Party B")

        # 3. Update Hearing Date (Date Shift Trigger)
        test_case["next_hearing_date"] = "2026-09-15"
        date_changed = upsert_case(test_case, client_name="Test Client", client_phone="+919000000000")
        self.assertTrue(date_changed, "Hearing date change must trigger date_changed = True")

        # 4. Verify History Log
        logs = get_case_history_logs()
        matching = [l for l in logs if l["cnr_number"] == "TEST010000002026"]
        self.assertTrue(len(matching) > 0, "Date change must be recorded in case_history_logs")
        self.assertEqual(matching[0]["previous_hearing_date"], "2026-09-01")
        self.assertEqual(matching[0]["new_hearing_date"], "2026-09-15")

        # 5. Clean up
        deleted = delete_case("TEST010000002026")
        self.assertTrue(deleted, "Case should be cleanly deleted")
        print("[TEST PASS] Database CRUD and Date-Shift Detection operations verified.")

    def test_03_live_api_case_lookup(self):
        cnr = "DLND020047882015"
        res = fetch_case_details(cnr)
        self.assertTrue(res.get("success"), f"Live API fetch should succeed for {cnr}")
        self.assertEqual(res.get("cnr_number"), cnr)
        self.assertIn("Arun Jaitley", res.get("case_title"))
        print(f"[TEST PASS] Live eCourts Partner API lookup passed: {res.get('case_title')}")

    def test_04_server_rest_api_endpoints(self):
        # 1. Key Status
        res = self.client.get("/api/key-status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("configured"))

        # 2. List Cases
        res = self.client.get("/api/cases")
        self.assertEqual(res.status_code, 200)

        # 3. Check Case API
        res = self.client.post("/api/check-case", json={
            "cnr": "DLND020047882015",
            "client_name": "Arun Jaitley",
            "client_phone": "+919876543210"
        })
        self.assertEqual(res.status_code, 200)
        check_data = res.get_json()
        self.assertTrue(check_data.get("success"))

        # 4. History Logs
        res = self.client.get("/api/history")
        self.assertEqual(res.status_code, 200)

        # 5. Export Printable Brief
        res = self.client.get("/api/export-case/DLND020047882015")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Case Hearing Brief", res.data.decode("utf-8"))

        print("[TEST PASS] All Flask REST API endpoints verified.")

    def test_05_sync_all_engine(self):
        sync_res = sync_worker.sync_all_cases()
        self.assertTrue(sync_res.get("success"))
        self.assertGreaterEqual(sync_res.get("total_checked"), 1)
        print(f"[TEST PASS] SyncAll Engine verified. Checked {sync_res.get('total_checked')} cases.")

if __name__ == "__main__":
    unittest.main()
