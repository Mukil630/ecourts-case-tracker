import os
import time
import datetime
import threading
from typing import Dict, Any, List, Tuple, Optional
from app.config import Config
from app.services.ecourts_service import fetch_case_details, get_api_key, get_credit_guard_status, API_CIRCUIT_BREAKER
from app.db.database import get_current_ist_date
from app.db.repository import get_all_cases, upsert_case, get_case_history_logs
from app.db.seed_data import ensure_today_hearings_synchronized

def evaluate_case_check_need(case: Dict[str, Any], today_str: Optional[str] = None) -> Dict[str, Any]:
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

    # Rule 2: Cases with no hearing date set need initial lookup
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

    # Rule 3: Hearing Far Away (> 3 Days) -> Sleep & Do NOT Check (0 credits consumed!)
    if days_until > 3:
        return {
            "cnr": cnr,
            "should_check": False,
            "status_code": "SLEEPING",
            "reason": f"Hearing {days_until} days away ({clean_date}) - Sleeping (0 credits)",
            "days_until": days_until,
            "badge_color": "var(--text-muted)"
        }

    # Rule 4: Hearing Due Soon (-1 to +3 Days) -> Active Verification Check
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

    # Rule 5: Past Hearing Date (<-1 Days) -> Post-Hearing Refresh
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
        self.thread: Optional[threading.Thread] = None
        self.last_sync_time: str = "Never"
        self.last_sync_result: Dict[str, Any] = {}
        self.total_credits_saved: float = 0.0

    def start(self):
        if self.running or self.interval_seconds <= 0:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _run_loop(self):
        # Initial wait before starting first automated background cycle
        time.sleep(10)
        while self.running:
            try:
                self.smart_sync_cases(force_all=False)
            except Exception as e:
                print(f"[SyncWorker Error] {e}")
            time.sleep(self.interval_seconds)

    def smart_sync_cases(self, force_all: bool = False) -> Dict[str, Any]:
        """
        Runs the smart predictive sync over all monitored cases.
        1. Auto-discovers tomorrow's / next court day's new client allocations at 7:30 PM.
        2. Updates next hearing dates, stages, and courtroom details daily.
        """
        from app.db.database import get_effective_practice_date
        target_effective_date = get_effective_practice_date()

        # 1. Automatic Evening Cause List Allocations Discovery
        try:
            from app.services.ecourts_service import search_cases_by_advocate
            adv_res = search_cases_by_advocate("Advocate R. Anbaiya", district="Karur", date=target_effective_date)
            if adv_res.get("success") and adv_res.get("cases"):
                for discovered in adv_res["cases"]:
                    upsert_case(
                        discovered,
                        client_name=discovered.get("client_name", ""),
                        client_phone="+919842112233",
                        litigant_role="Petitioner / Complainant",
                        notes=f"Auto-allocated for {target_effective_date} court session",
                        case_number_formatted=discovered.get("case_number_formatted", ""),
                        case_stage=discovered.get("case_stage", "Hearing"),
                        court_room=discovered.get("court_room", "Room 1"),
                        item_number=discovered.get("item_number", "1"),
                        judge_name=discovered.get("judge_name", "")
                    )
        except Exception as ex:
            print(f"[Evening CauseList Allocations Sync] {ex}")

        all_cases = get_all_cases()
        today = get_current_ist_date()

        checked = []
        skipped = []
        updated = []
        disposed = []
        errors = []
        credits_used = 0
        credits_saved = 0

        for c in all_cases:
            cnr = c.get("cnr_number")
            eval_res = evaluate_case_check_need(c, today)

            # Skip checking if hearing is far away or case is disposed
            if not eval_res["should_check"] and not force_all:
                skipped.append({
                    "cnr": cnr,
                    "case_title": c.get("case_title"),
                    "reason": eval_res["reason"],
                    "status": eval_res["status_code"]
                })
                credits_saved += 1
                continue

            # Case is due for check
            try:
                res = fetch_case_details(cnr, force_live=force_all)
                if res.get("success"):
                    checked.append(cnr)
                    if not res.get("is_cached"):
                        credits_used += 1

                    # Check if hearing date, stage, or status changed
                    new_date = res.get("next_hearing_date")
                    old_date = c.get("next_hearing_date")
                    new_stage = res.get("case_stage") or c.get("case_stage")
                    new_status = (res.get("case_status") or c.get("case_status") or "PENDING").upper()
                    new_room = res.get("court_room") or c.get("court_room")
                    new_item = res.get("item_number") or c.get("item_number")
                    new_judge = res.get("judge_name") or c.get("judge_name")

                    # Check if status became Disposed
                    if "DISPOSE" in new_status or "DECIDED" in new_status or "CLOSED" in new_status:
                        new_status = "DISPOSED"
                        disposed.append(cnr)

                    if (new_date and new_date != old_date) or (new_status != c.get("case_status")):
                        upsert_case(
                            res,
                            client_name=c.get("client_name", ""),
                            client_phone=c.get("client_phone", ""),
                            notes=c.get("notes", ""),
                            case_number_formatted=res.get("case_number_formatted") or c.get("case_number_formatted", ""),
                            case_stage=new_stage,
                            court_room=new_room,
                            item_number=new_item
                        )
                        updated.append({
                            "cnr": cnr,
                            "case_title": c.get("case_title"),
                            "old_date": old_date,
                            "new_date": new_date,
                            "new_stage": new_stage,
                            "status": new_status
                        })

                        # Trigger automated real-time Telegram alert
                        try:
                            from app.services.telegram_service import send_adjournment_alert_telegram
                            send_adjournment_alert_telegram(c, old_date, new_date)
                        except Exception:
                            pass
                else:
                    if res.get("credit_guard"):
                        # In credit guard mode, vault serves data safely
                        skipped.append({
                            "cnr": cnr,
                            "case_title": c.get("case_title"),
                            "reason": "Credit Guard Protection Active",
                            "status": "SHIELDED"
                        })
                        credits_saved += 1
                    else:
                        errors.append({"cnr": cnr, "error": res.get("error")})
            except Exception as e:
                errors.append({"cnr": cnr, "error": str(e)})

        self.last_sync_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.total_credits_saved += (credits_saved * 1.5)

        self.last_sync_result = {
            "timestamp": self.last_sync_time,
            "total_monitored": len(all_cases),
            "checked_count": len(checked),
            "sleeping_count": len(skipped),
            "updated_count": len(updated),
            "disposed_count": len(disposed),
            "errors_count": len(errors),
            "credits_used_estimate": credits_used * 1.5,
            "credits_saved_rupees": credits_saved * 1.5,
            "updated_cases": updated,
            "sleeping_cases": skipped[:10],
            "guard_status": get_credit_guard_status()
        }

        return self.last_sync_result

# Global worker instance initialized with app config
sync_worker = AutoSyncWorker(interval_seconds=Config.SYNC_INTERVAL_SECONDS)
