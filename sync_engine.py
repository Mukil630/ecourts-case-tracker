import os
import time
import threading
from typing import Dict, Any, List
from ecourts_api import fetch_case_details, get_api_key
from db import init_db, upsert_case, get_all_cases, get_case_history_logs

class AutoSyncWorker:
    def __init__(self, interval_seconds: int = 3600):
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread: threading.Thread = None
        self.last_sync_time: str = "Never"
        self.last_sync_result: Dict[str, Any] = {}
        self.total_credits_saved: int = 0

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

    def sync_all_cases(self, force_live: bool = False) -> Dict[str, Any]:
        """
        Iterates through all tracked cases in SQLite and fetches updated hearing dates
        respecting Uncle's custom rules and credit-saving cache.
        """
        init_db()
        cases = get_all_cases()
        api_key = get_api_key()

        total_checked = 0
        date_changes_detected = []
        errors = []
        cached_count = 0
        live_count = 0

        self.last_sync_time = time.strftime("%Y-%m-%d %H:%M:%S")

        for c in cases:
            cnr = c.get("cnr_number")
            if not cnr:
                continue

            # Respect Uncle's tracking rules
            track_hearing = bool(c.get("track_next_hearing", 1))
            track_orders = bool(c.get("track_orders", 1))
            track_status = bool(c.get("track_case_status", 1))
            auto_wa = bool(c.get("auto_whatsapp_enabled", 1))

            total_checked += 1
            try:
                if api_key:
                    res = fetch_case_details(cnr, force_live=force_live)
                    if res.get("is_cached"):
                        cached_count += 1
                        self.total_credits_saved += 1
                    else:
                        live_count += 1

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
                        
                        changed = upsert_case(
                            db_payload,
                            client_name=c.get("client_name", ""),
                            client_phone=c.get("client_phone", ""),
                            track_next_hearing=track_hearing,
                            track_orders=track_orders,
                            track_case_status=track_status,
                            auto_whatsapp_enabled=auto_wa,
                            notes=c.get("notes", ""),
                            custom_advocate_header=c.get("custom_advocate_header", "Advocate Office Notice")
                        )
                        if changed and track_hearing:
                            date_changes_detected.append({
                                "cnr": cnr,
                                "title": res.get("case_title"),
                                "client_name": c.get("client_name"),
                                "client_phone": c.get("client_phone"),
                                "new_date": res.get("next_hearing_date"),
                                "auto_whatsapp": auto_wa
                            })
                    else:
                        errors.append({"cnr": cnr, "error": res.get("error")})
                else:
                    time.sleep(0.05)
            except Exception as e:
                errors.append({"cnr": cnr, "error": str(e)})

        result = {
            "success": True,
            "timestamp": self.last_sync_time,
            "total_cases": len(cases),
            "total_checked": total_checked,
            "cached_count": cached_count,
            "live_count": live_count,
            "date_changes_count": len(date_changes_detected),
            "date_changes": date_changes_detected,
            "errors": errors
        }
        self.last_sync_result = result
        return result

# Global singleton sync worker
sync_worker = AutoSyncWorker(interval_seconds=3600)
