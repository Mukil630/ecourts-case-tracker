import os
import time
import datetime
import threading
from typing import Dict, Any, List, Tuple
from ecourts_api import fetch_case_details, get_api_key
from db import init_db, upsert_case, get_all_cases, get_case_history_logs

def evaluate_case_check_need(case: Dict[str, Any], today: datetime.date = None) -> Dict[str, Any]:
    """
    Evaluates whether a case should be checked via live API today based on
    Smart Predictive Polling (Hearing Near vs Hearing Far Away).
    """
    if today is None:
        today = datetime.date.today()

    cnr = case.get("cnr_number", "")
    status = (case.get("case_status") or "").upper()
    next_date_str = case.get("next_hearing_date") or ""

    # Rule 1: Disposed Cases are frozen
    if "DISPOSE" in status or "DECIDED" in status:
        return {
            "cnr": cnr,
            "should_check": False,
            "status_code": "DISPOSED",
            "reason": "Case Disposed / Closed (Frozen)",
            "days_until": None,
            "badge_color": "var(--text-muted)"
        }

    # Rule 2: Cases with no hearing date yet need initial lookup
    if not next_date_str or next_date_str == "None":
        return {
            "cnr": cnr,
            "should_check": True,
            "status_code": "INITIAL_DISCOVERY",
            "reason": "No Hearing Date set (Initial Discovery)",
            "days_until": 0,
            "badge_color": "var(--accent-blue)"
        }

    # Parse next hearing date
    try:
        # Handle YYYY-MM-DD
        clean_date = next_date_str.split("T")[0].strip()
        parts = [int(p) for p in clean_date.split("-")]
        if len(parts) == 3:
            hearing_date = datetime.date(parts[0], parts[1], parts[2])
        else:
            hearing_date = today
    except Exception:
        hearing_date = today

    days_until = (hearing_date - today).days

    # Rule 3: Hearing Far Away (> 3 Days) -> Sleep & Do NOT Check (0 credits!)
    if days_until > 3:
        return {
            "cnr": cnr,
            "should_check": False,
            "status_code": "SLEEPING",
            "reason": f"Hearing {days_until} days away ({clean_date}) - Sleeping",
            "days_until": days_until,
            "badge_color": "var(--text-muted)"
        }

    # Rule 4: Hearing Due Soon (-1 to +3 Days) -> Active Check (1.5 credits)
    elif -1 <= days_until <= 3:
        timing_label = "Tomorrow" if days_until == 1 else ("Today" if days_until == 0 else f"in {days_until} days")
        return {
            "cnr": cnr,
            "should_check": True,
            "status_code": "HEARING_NEAR",
            "reason": f"Hearing {timing_label} ({clean_date}) - Verification Due",
            "days_until": days_until,
            "badge_color": "var(--accent-emerald)"
        }

    # Rule 5: Past Hearing Date (<-1 Days) -> Needs Post-Hearing Refresh for new date
    else:
        return {
            "cnr": cnr,
            "should_check": True,
            "status_code": "POST_HEARING_REFRESH",
            "reason": f"Past Hearing ({clean_date}) - Needs Next Date Refresh",
            "days_until": days_until,
            "badge_color": "var(--accent-amber)"
        }

class AutoSyncWorker:
    def __init__(self, interval_seconds: int = 3600):
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread: threading.Thread = None
        self.last_sync_time: str = "Never"
        self.last_sync_result: Dict[str, Any] = {}
        self.total_credits_saved: float = 0.0

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
                print("[*] [AutoSyncWorker] Scheduled Smart Predictive Polling triggered...")
                self.smart_sync_cases()
            except Exception as e:
                print(f"[!] [AutoSyncWorker] Error during sync: {e}")

    def smart_sync_cases(self, force_all: bool = False) -> Dict[str, Any]:
        """
        Executes Smart Predictive Polling:
        - Hearing Far Away -> Skips & Sleeps (0 credits)
        - Hearing Near / Due -> Queries API (1.5 credits)
        - Compares old vs new date -> Logs shift & queues WhatsApp
        """
        init_db()
        cases = get_all_cases()
        api_key = get_api_key()
        today = datetime.date.today()

        total_portfolio = len(cases)
        sleeping_count = 0
        disposed_count = 0
        checked_count = 0
        date_changes_detected = []
        errors = []
        evaluation_log = []

        self.last_sync_time = time.strftime("%Y-%m-%d %H:%M:%S")

        for c in cases:
            cnr = c.get("cnr_number")
            if not cnr:
                continue

            eval_res = evaluate_case_check_need(c, today)
            should_query = eval_res["should_check"] or force_all

            if not should_query:
                if eval_res["status_code"] == "DISPOSED":
                    disposed_count += 1
                else:
                    sleeping_count += 1
                
                # Each avoided call saves 1.5 credits
                self.total_credits_saved += 1.5
                evaluation_log.append({
                    "cnr": cnr,
                    "title": c.get("case_title"),
                    "action": "SLEEP / SKIP",
                    "reason": eval_res["reason"],
                    "credits_used": 0.0
                })
                continue

            # Case is DUE for check
            checked_count += 1
            evaluation_log.append({
                "cnr": cnr,
                "title": c.get("case_title"),
                "action": "API QUERY",
                "reason": eval_res["reason"],
                "credits_used": 1.5
            })

            try:
                if api_key:
                    # Safe rate-limiting delay between requests
                    time.sleep(0.3)
                    res = fetch_case_details(cnr, force_live=True)
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
                            track_next_hearing=bool(c.get("track_next_hearing", 1)),
                            track_orders=bool(c.get("track_orders", 1)),
                            track_case_status=bool(c.get("track_case_status", 1)),
                            auto_whatsapp_enabled=bool(c.get("auto_whatsapp_enabled", 1)),
                            notes=c.get("notes", ""),
                            custom_advocate_header=c.get("custom_advocate_header", "Advocate Office Notice"),
                            case_number_formatted=c.get("case_number_formatted", ""),
                            case_stage=c.get("case_stage", ""),
                            court_room=c.get("court_room", ""),
                            item_number=c.get("item_number", ""),
                            judge_name=c.get("judge_name", "")
                        )
                        
                        if changed:
                            date_changes_detected.append({
                                "cnr": cnr,
                                "title": res.get("case_title"),
                                "client_name": c.get("client_name"),
                                "client_phone": c.get("client_phone"),
                                "previous_date": c.get("next_hearing_date"),
                                "new_date": res.get("next_hearing_date"),
                                "auto_whatsapp": bool(c.get("auto_whatsapp_enabled", 1))
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
            "total_portfolio": total_portfolio,
            "sleeping_cases": sleeping_count,
            "disposed_cases": disposed_count,
            "checked_cases": checked_count,
            "credits_consumed": checked_count * 1.5,
            "credits_saved_this_run": (sleeping_count + disposed_count) * 1.5,
            "total_lifetime_credits_saved": self.total_credits_saved,
            "date_changes_count": len(date_changes_detected),
            "date_changes": date_changes_detected,
            "evaluation_log": evaluation_log,
            "errors": errors
        }
        self.last_sync_result = result
        return result

    def sync_all_cases(self, force_live: bool = False) -> Dict[str, Any]:
        """Legacy helper pointing to smart_sync_cases."""
        return self.smart_sync_cases(force_all=force_live)

# Global singleton sync worker
sync_worker = AutoSyncWorker(interval_seconds=3600)
