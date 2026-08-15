import os
import time
import threading
from typing import Dict, Any, List
from ecourts_api import fetch_case_details, get_api_key
from db import init_db, upsert_case, get_all_cases, get_case_history_logs

class AutoSyncWorker:
    def __init__(self, interval_seconds: int = 1800):
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread: threading.Thread = None
        self.last_sync_time: str = "Never"
        self.last_sync_result: Dict[str, Any] = {}

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print(f"[*] Background AutoSyncWorker started (Interval: {self.interval_seconds}s)")

    def stop(self):
        self.running = False

    def _run_loop(self):
        while self.running:
            time.sleep(self.interval_seconds)
            if not self.running:
                break
            try:
                print("[*] [AutoSyncWorker] Periodic background sync initiated...")
                self.sync_all_cases()
            except Exception as e:
                print(f"[!] [AutoSyncWorker] Error during sync: {e}")

    def sync_all_cases(self) -> Dict[str, Any]:
        """Iterates through all tracked cases in SQLite and fetches updated hearing dates."""
        init_db()
        cases = get_all_cases()
        api_key = get_api_key()

        total_checked = 0
        date_changes_detected = []
        errors = []

        self.last_sync_time = time.strftime("%Y-%m-%d %H:%M:%S")

        for c in cases:
            cnr = c.get("cnr_number")
            if not cnr:
                continue

            total_checked += 1
            try:
                if api_key:
                    res = fetch_case_details(cnr)
                    if res.get("success"):
                        db_payload = {
                            "cnr_number": res.get("cnr_number"),
                            "case_title": res.get("case_title"),
                            "case_status": res.get("case_status"),
                            "court_name": res.get("court_name"),
                            "parties": f"Petitioner: {', '.join(res.get('petitioners', []))} | Respondent: {', '.join(res.get('respondents', []))}",
                            "advocates": f"Petitioner Adv: {', '.join(res.get('petitioner_advocates', []))} | Respondent Adv: {', '.join(res.get('respondent_advocates', []))}",
                            "last_hearing_date": res.get("last_hearing_date"),
                            "next_hearing_date": res.get("next_hearing_date")
                        }
                        changed = upsert_case(db_payload, client_name=c.get("client_name", ""), client_phone=c.get("client_phone", ""))
                        if changed:
                            date_changes_detected.append({
                                "cnr": cnr,
                                "title": res.get("case_title"),
                                "new_date": res.get("next_hearing_date")
                            })
                    else:
                        errors.append({"cnr": cnr, "error": res.get("error")})
                else:
                    # In demo mode, simulate sync
                    time.sleep(0.1)
            except Exception as e:
                errors.append({"cnr": cnr, "error": str(e)})

        result = {
            "success": True,
            "timestamp": self.last_sync_time,
            "total_cases": len(cases),
            "total_checked": total_checked,
            "date_changes_count": len(date_changes_detected),
            "date_changes": date_changes_detected,
            "errors": errors
        }
        self.last_sync_result = result
        return result

# Global singleton sync worker
sync_worker = AutoSyncWorker(interval_seconds=1800)
