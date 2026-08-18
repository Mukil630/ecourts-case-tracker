import os
import time
import datetime
import threading
from typing import Dict, Any, List, Tuple
from ecourts_api import fetch_case_details, get_api_key, get_credit_guard_status, API_CIRCUIT_BREAKER
from db import init_db, upsert_case, get_all_cases, get_case_history_logs, get_current_ist_date, ensure_today_hearings_synchronized

def evaluate_case_check_need(case: Dict[str, Any], today_str: str = None) -> Dict[str, Any]:
    """
    Evaluates whether a case should be checked via live API today based on
    Smart Predictive Polling (Hearing Near vs Hearing Far Away).
    """
    if today_str is None:
        today_str = get_current_ist_date()

    today = datetime.datetime.strptime(today_str, "%Y-%m-%d").date()

    cnr = case.get("cnr_number", "")
    status = (case.get("case_status") or "").upper()
    next_date_str = case.get("next_hearing_date") or ""

    # Rule 1: Disposed Cases are frozen
    if "DISPOSE" in status or "DECIDED" in status:
        return {
            "cnr": cnr,
            "should_check": False,
            "status_code": "DISPOSED",
            "reason": "Case Disposed / Closed (Frozen in Vault)",
            "days_until": None,
            "badge_color": "var(--text-muted)"
        }

    # Rule 2: Cases with no hearing date yet need initial lookup
    if not next_date_str or next_date_str == "None":
        return {
            "cnr": cnr,
            "should_check": True,
            "status_code": "INITIAL_DISCOVERY",
            "reason": "No Hearing Date set (Chamber Vault Sync)",
            "days_until": 0,
            "badge_color": "var(--accent-blue)"
        }

    # Parse next hearing date
    try:
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
            "reason": f"Hearing {days_until} days away ({clean_date}) - Sleeping (0 credits)",
            "days_until": days_until,
            "badge_color": "var(--text-muted)"
        }

    # Rule 4: Hearing Due Soon (-1 to +3 Days) -> Active Check
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

    # Rule 5: Past Hearing Date (<-1 Days) -> Needs Post-Hearing Refresh
    else:
        return {
            "cnr": cnr,
            "should_check": True,
            "status_code": "POST_HEARING_REFRESH",
            "reason": f"Past Hearing ({clean_date}) - Needs Date Refresh",
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
                self.smart_sync_cases(force_all=False)
            except Exception as e:
                print(f"[!] [AutoSyncWorker] Error during sync: {e}")

    def smart_sync_cases(self, force_all: bool = False) -> Dict[str, Any]:
        """
        Executes Smart Predictive Polling with Credit-Guard Circuit Breaker:
        - Hearing Far Away -> Skips & Sleeps (0 credits)
        - Circuit Breaker Tripped / No Key -> Resolves via Vault Cache (0 credits)
        - Only queries live eCourts when required and safe.
        """
        init_db()
        ensure_today_hearings_synchronized()
        cases = get_all_cases()
        guard_status = get_credit_guard_status()
        today_str = get_current_ist_date()

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

            eval_res = evaluate_case_check_need(c, today_str)
            should_query = eval_res["should_check"] or force_all

            if not should_query:
                if eval_res["status_code"] == "DISPOSED":
                    disposed_count += 1
                else:
                    sleeping_count += 1
                
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
                "action": "VAULT CACHE / GUARDED SYNC",
                "reason": eval_res["reason"],
                "credits_used": 0.0 if API_CIRCUIT_BREAKER["tripped"] or not guard_status["api_configured"] else 1.5
            })

            try:
                # Do NOT force_live in background loop - rely on cache & credit guard!
                res = fetch_case_details(cnr, force_live=False)
                if res.get("success"):
                    # Only update hearing date if present and valid
                    new_date = res.get("next_hearing_date") or c.get("next_hearing_date")
                    if new_date and new_date != c.get("next_hearing_date"):
                        date_changes_detected.append({
                            "cnr": cnr,
                            "title": c.get("case_title"),
                            "client_name": c.get("client_name"),
                            "client_phone": c.get("client_phone"),
                            "previous_date": c.get("next_hearing_date"),
                            "new_date": new_date,
                            "auto_whatsapp": bool(c.get("auto_whatsapp_enabled", 1))
                        })
                else:
                    if not API_CIRCUIT_BREAKER["tripped"]:
                        errors.append({"cnr": cnr, "error": res.get("error")})
            except Exception as e:
                errors.append({"cnr": cnr, "error": str(e)})

        result = {
            "success": True,
            "timestamp": self.last_sync_time,
            "total_portfolio": total_portfolio,
            "sleeping_cases": sleeping_count,
            "disposed_cases": disposed_count,
            "checked_cases": checked_count,
            "credits_consumed": 0.0 if (API_CIRCUIT_BREAKER["tripped"] or not guard_status["api_configured"]) else (checked_count * 1.5),
            "credits_saved_this_run": (sleeping_count + disposed_count) * 1.5,
            "total_lifetime_credits_saved": self.total_credits_saved,
            "date_changes_count": len(date_changes_detected),
            "date_changes": date_changes_detected,
            "credit_guard_status": guard_status,
            "evaluation_log": evaluation_log,
            "errors": errors
        }
        self.last_sync_result = result
        return result

    def sync_all_cases(self, force_live: bool = False) -> Dict[str, Any]:
        """Helper pointing to smart_sync_cases."""
        return self.smart_sync_cases(force_all=force_live)

# Global singleton sync worker
sync_worker = AutoSyncWorker(interval_seconds=3600)
