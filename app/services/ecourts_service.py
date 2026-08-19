import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List
from app.config import Config
from app.db.repository import get_cached_case, set_cached_case, get_case_by_cnr

# Global Circuit Breaker & Credit Shield State
API_CIRCUIT_BREAKER = {
    "tripped": False,
    "reason": "",
    "last_error_time": 0,
    "consecutive_failures": 0,
    "mode": "CREDIT_GUARD_ACTIVE"
}

def get_api_key() -> str:
    """Reads API key from environment variable or .env file in project root."""
    key = os.environ.get("ECOURTS_API_KEY")
    if key and key != "your_api_key_here" and len(key.strip()) > 5:
        return key.strip()

    env_path = Config.BASE_DIR / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ECOURTS_API_KEY="):
                        val = line.split("=", 1)[1].strip()
                        if val and val != "your_api_key_here" and len(val) > 5:
                            return val
        except Exception:
            pass
    return ""

def save_api_key_to_env(new_key: str) -> bool:
    """Saves the eCourts API key to the .env file and environment."""
    clean_key = new_key.strip()
    if not clean_key:
        return False
    
    env_path = Config.BASE_DIR / ".env"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(f"# eCourts API Key Configuration\nECOURTS_API_KEY={clean_key}\n")
    
    os.environ["ECOURTS_API_KEY"] = clean_key
    reset_circuit_breaker()
    return True

def get_credit_guard_status() -> Dict[str, Any]:
    """Returns the live status of the Credit Guard and Circuit Breaker."""
    key = get_api_key()
    has_key = bool(key)
    return {
        "api_configured": has_key,
        "circuit_breaker_tripped": API_CIRCUIT_BREAKER["tripped"],
        "breaker_reason": API_CIRCUIT_BREAKER["reason"],
        "mode": "LOCAL_VAULT_SHIELDED" if API_CIRCUIT_BREAKER["tripped"] or not has_key else "LIVE_API_GUARDED",
        "message": "⚡ 100% Zero-Credit Private Chamber Vault Mode Active" if API_CIRCUIT_BREAKER["tripped"] or not has_key else "🛡️ Active Credit Guard Protection"
    }

def reset_circuit_breaker():
    """Resets the circuit breaker if the user enters a new valid key."""
    API_CIRCUIT_BREAKER["tripped"] = False
    API_CIRCUIT_BREAKER["reason"] = ""
    API_CIRCUIT_BREAKER["consecutive_failures"] = 0

def fetch_case_details(cnr_number: str, force_live: bool = False, cache_ttl_seconds: int = 86400) -> Dict[str, Any]:
    """
    Fetches case details from eCourtsIndia v4 Partner API: GET /api/partner/case/{cnr}
    """
    clean_cnr = cnr_number.strip().upper()

    # 1. Check Local SQLite Cache first
    if not force_live:
        try:
            cached_json = get_cached_case(clean_cnr, max_age_seconds=cache_ttl_seconds)
            if cached_json:
                parsed = parse_ecourts_response(clean_cnr, cached_json)
                parsed["is_cached"] = True
                parsed["cache_note"] = "⚡ Loaded instantly from local cache (0 credits used)"
                return parsed
        except Exception:
            pass

    # 2. Check Database Existing Case
    try:
        existing = get_case_by_cnr(clean_cnr)
        if existing and not force_live:
            return {
                "success": True,
                "cnr_number": clean_cnr,
                "case_title": existing.get("case_title", f"{clean_cnr} Matter"),
                "case_status": existing.get("case_status", "PENDING"),
                "court_name": existing.get("court_name", "Karur District Court"),
                "court_room": existing.get("court_room", "Room 1"),
                "item_number": existing.get("item_number", "1"),
                "judge_name": existing.get("judge_name", ""),
                "case_stage": existing.get("case_stage", "Evidence"),
                "petitioners": [existing.get("client_name", "Petitioner")],
                "respondents": ["Opposing Party"],
                "last_hearing_date": existing.get("last_hearing_date", ""),
                "next_hearing_date": existing.get("next_hearing_date", ""),
                "is_cached": True,
                "cache_note": "⚡ Loaded from Chamber Vault (0 credits used)"
            }
    except Exception:
        pass

    # 3. Check Circuit Breaker
    if API_CIRCUIT_BREAKER["tripped"] and not force_live:
        return {
            "success": False,
            "error_type": "CIRCUIT_BREAKER_ACTIVE",
            "error": f"Credit Guard Active: {API_CIRCUIT_BREAKER['reason']}",
            "credit_guard": True
        }

    # 4. Check API Key
    api_key = get_api_key()
    if not api_key:
        return {
            "success": False,
            "error_type": "CONFIG_ERROR",
            "error": "eCourts API Key not configured. Please add ECOURTS_API_KEY in settings."
        }

    # 5. Make Live HTTP Request to v4 Partner API: GET /api/partner/case/{cnr}
    url = f"{Config.ECOURTS_API_BASE_URL}/api/partner/case/{clean_cnr}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=25)

        if response.status_code == 402:
            API_CIRCUIT_BREAKER["tripped"] = True
            API_CIRCUIT_BREAKER["reason"] = "Insufficient API Credits on webapi.ecourtsindia.com"
            return {
                "success": False,
                "error_type": "INSUFFICIENT_CREDITS",
                "error": "eCourts Partner API is out of credits (₹0.00).",
                "credit_guard": True
            }

        if response.status_code == 401:
            API_CIRCUIT_BREAKER["tripped"] = True
            API_CIRCUIT_BREAKER["reason"] = "Invalid or Expired eCourts API Key"
            return {
                "success": False,
                "error_type": "AUTH_ERROR",
                "error": "API Key rejected. Please verify on webapi.ecourtsindia.com.",
                "credit_guard": True
            }

        if response.status_code == 200:
            API_CIRCUIT_BREAKER["consecutive_failures"] = 0
            raw_data = response.json()

            try:
                set_cached_case(clean_cnr, raw_data)
            except Exception:
                pass

            parsed = parse_ecourts_response(clean_cnr, raw_data)
            parsed["is_cached"] = False
            parsed["cache_note"] = "Live eCourts v4 API Sync (1 API Credit consumed)"
            return parsed

        return {
            "success": False,
            "error_type": f"HTTP_{response.status_code}",
            "error": f"eCourts API error ({response.status_code}): {response.text[:200]}"
        }
    except Exception as e:
        return {
            "success": False,
            "error_type": "NETWORK_ERROR",
            "error": str(e)
        }

def fetch_case_by_cnr(cnr_number: str) -> Dict[str, Any]:
    """Backward compatibility alias for fetch_case_details."""
    return fetch_case_details(cnr_number)

def check_cnr_in_cause_list(cnr_number: str, date: str) -> Dict[str, Any]:
    """
    Checks if a specific CNR number is scheduled in tomorrow's cause list with Room & Item.
    """
    api_key = get_api_key()
    clean_cnr = cnr_number.strip().upper()

    if api_key and not API_CIRCUIT_BREAKER["tripped"]:
        url = f"{Config.ECOURTS_API_BASE_URL}/api/partner/causelist/cnr/batch"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        try:
            res = requests.post(url, headers=headers, json={"cnrs": [clean_cnr]}, timeout=15)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data and len(data) > 0:
                    listing = data[0].get("nextListing") or {}
                    return {
                        "success": True,
                        "cnr": clean_cnr,
                        "is_listed": data[0].get("hasCauselist", False),
                        "item_number": str(listing.get("listingNo") or "1"),
                        "court_room": f"Room {listing.get('courtNo', '1')}",
                        "judge_name": (listing.get("judge") or [""])[0] if listing.get("judge") else "",
                        "cost_estimate_rupees": 0.30
                    }
        except Exception:
            pass

    return {
        "success": True,
        "cnr": clean_cnr,
        "is_listed": False,
        "cost_estimate_rupees": 0.00
    }

def parse_ecourts_response(cnr_number: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes raw JSON from eCourtsIndia v4 API into clean internal schema."""
    case_wrapper = raw_data.get("data", raw_data.get("case_details", raw_data))
    if not isinstance(case_wrapper, dict):
        case_wrapper = {}
    court_data = case_wrapper.get("courtCaseData", case_wrapper)
    if not isinstance(court_data, dict):
        court_data = {}

    pets = court_data.get("petitioners", [])
    if isinstance(pets, str):
        pets = [pets]
    resps = court_data.get("respondents", [])
    if isinstance(resps, str):
        resps = [resps]

    pet_str = pets[0] if pets else "Petitioner"
    resp_str = resps[0] if resps else "Respondent"

    title = court_data.get("case_title") or court_data.get("caseTitle") or court_data.get("title") or (f"{pet_str} vs {resp_str}" if pets and resps else f"{cnr_number} Case")
    status = court_data.get("case_status") or court_data.get("caseStatus") or court_data.get("status") or "PENDING"
    court = court_data.get("court_name") or court_data.get("courtName") or court_data.get("court") or "District Court"
    room = str(court_data.get("court_room") or court_data.get("courtNo") or "Room 1")
    if not room.startswith("Room") and room != "":
        room = f"Room {room}"

    stage = court_data.get("purpose") or court_data.get("case_stage") or court_data.get("caseTypeSub") or "Evidence"
    next_date = court_data.get("next_hearing_date") or court_data.get("nextHearingDate") or court_data.get("next_date") or court_data.get("decisionDate") or ""
    last_date = court_data.get("last_hearing_date") or court_data.get("lastHearingDate") or court_data.get("last_date") or court_data.get("firstHearingDate") or ""
    pet_advs = court_data.get("petitionerAdvocates") or court_data.get("petitioner_advocates") or []
    if isinstance(pet_advs, str):
        pet_advs = [pet_advs]
    resp_advs = court_data.get("respondentAdvocates") or court_data.get("respondent_advocates") or []
    if isinstance(resp_advs, str):
        resp_advs = [resp_advs]

    judge = court_data.get("judge_name") or court_data.get("judge") or court_data.get("judges") or ""
    if isinstance(judge, list):
        judge = judge[0] if judge else ""

    case_type = court_data.get("caseType") or court_data.get("case_type") or ""
    reg_num = court_data.get("registrationNumber") or court_data.get("registration_number") or court_data.get("filingNumber") or ""
    formatted_num = f"{case_type}/{reg_num}" if case_type and reg_num else cnr_number

    parties_str = f"Petitioner: {', '.join(pets)} | Respondent: {', '.join(resps)}" if (pets or resps) else ""
    pet_adv_str = ', '.join(pet_advs) if isinstance(pet_advs, list) else str(pet_advs)
    resp_adv_str = ', '.join(resp_advs) if isinstance(resp_advs, list) else str(resp_advs)
    adv_str = f"Petitioner Adv: {pet_adv_str} | Respondent Adv: {resp_adv_str}" if (pet_adv_str or resp_adv_str) else ""

    history = court_data.get("historyOfCaseHearings") or []
    orders = court_data.get("interimOrders") or court_data.get("orders") or []

    return {
        "success": True,
        "cnr_number": cnr_number,
        "case_number_formatted": formatted_num,
        "case_title": title,
        "case_status": status,
        "court_name": court,
        "court_room": room,
        "judge_name": str(judge),
        "case_stage": stage,
        "next_hearing_date": next_date,
        "last_hearing_date": last_date,
        "petitioners": pets,
        "respondents": resps,
        "petitioner_advocates": pet_advs,
        "respondent_advocates": resp_advs,
        "parties": parties_str,
        "advocates": adv_str,
        "hearing_count": court_data.get("hearingCount", len(history)),
        "order_count": court_data.get("orderCount", len(orders)),
        "client_name": pet_str,
        "raw": raw_data
    }

def search_cases_by_advocate(advocate_name: str, district: str = "Karur", date: Optional[str] = None) -> Dict[str, Any]:
    """
    Live Search via eCourtsIndia v4 API: GET /api/partner/causelist/search & GET /api/partner/search
    """
    api_key = get_api_key()
    matched = []

    # 1. Live API Query if Key is Available
    if api_key and not API_CIRCUIT_BREAKER["tripped"]:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }
        clean_adv = advocate_name.replace("Advocate", "").replace(".", "").strip()

        # Try Cause List Search if date is specified
        if date:
            cl_url = f"{Config.ECOURTS_API_BASE_URL}/api/partner/causelist/search?advocate={clean_adv}&date={date}&limit=50"
            try:
                r = requests.get(cl_url, headers=headers, timeout=15)
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    for item in data.get("results", []):
                        c_no = item.get("caseNumber", [""])[0] if item.get("caseNumber") else ""
                        c_room = str(item.get("courtNo") or "1")
                        matched.append({
                            "cnr_number": item.get("cnr") or f"TNKR_{c_no.replace('/', '_')}",
                            "case_number_formatted": c_no,
                            "case_title": item.get("party") or "Party vs Opponent",
                            "court_name": item.get("courtName") or item.get("courtDescription") or f"{district} Court",
                            "court_room": f"Room {c_room}" if not c_room.startswith("Room") else c_room,
                            "item_number": str(item.get("listingNo") or "1"),
                            "judge_name": (item.get("judge") or [""])[0] if item.get("judge") else "",
                            "case_stage": item.get("listingFor") or "Evidence",
                            "case_status": item.get("status") or "PENDING",
                            "next_hearing_date": item.get("date") or date,
                            "client_name": (item.get("petitioners") or [item.get("party") or "Client"])[0],
                            "advocates": advocate_name
                        })
            except Exception:
                pass

        # If no date or no cause list results, query full case search
        if not matched:
            search_url = f"{Config.ECOURTS_API_BASE_URL}/api/partner/search?advocates={clean_adv}&pageSize=30"
            try:
                r = requests.get(search_url, headers=headers, timeout=15)
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    for item in data.get("results", []):
                        pets = item.get("petitioners", [])
                        resps = item.get("respondents", [])
                        p_str = pets[0] if pets else "Petitioner"
                        r_str = resps[0] if resps else "Respondent"
                        c_type = item.get("caseType", "")
                        c_reg = item.get("registrationNumber", "")
                        matched.append({
                            "cnr_number": item.get("cnr") or "",
                            "case_number_formatted": f"{c_type}/{c_reg}" if c_type and c_reg else item.get("cnr", ""),
                            "case_title": f"{p_str} vs {r_str}",
                            "court_name": item.get("courtName") or f"{district} Court",
                            "court_room": "Room 1",
                            "item_number": "1",
                            "judge_name": (item.get("judges") or [""])[0] if item.get("judges") else "",
                            "case_stage": "Evidence",
                            "case_status": item.get("caseStatus") or "PENDING",
                            "next_hearing_date": item.get("nextHearingDate") or "",
                            "client_name": p_str,
                            "advocates": advocate_name
                        })
            except Exception:
                pass

        if matched:
            return {
                "success": True,
                "advocate_name": advocate_name,
                "district": district,
                "total_found": len(matched),
                "cases": matched,
                "mode": "LIVE_ECOURTS_V4_API",
                "cost_estimate_rupees": 0.60
            }

    # 2. Local Chamber Vault Fallback (₹0.00)
    from app.db.repository import get_all_cases
    cases = get_all_cases()
    clean_name = advocate_name.lower().replace("advocate", "").replace(".", "").strip()

    for c in cases:
        adv = (c.get("advocates") or "").lower()
        if clean_name in adv or "anbaiya" in adv or not clean_name:
            if not date or c.get("next_hearing_date") == date:
                matched.append(c)

    return {
        "success": True,
        "advocate_name": advocate_name,
        "district": district,
        "total_found": len(matched),
        "cases": matched,
        "mode": "CHAMBER_VAULT_LOCAL",
        "cost_estimate_rupees": 0.00
    }

def check_cnr_in_cause_list(cnr_number: str, date: str) -> Dict[str, Any]:
    """
    Cost-Efficient Single CNR Check (₹0.30):
    Checks if a specific CNR number is scheduled in tomorrow's cause list with Room & Item.
    """
    api_key = get_api_key()
    clean_cnr = cnr_number.strip().upper()

    if api_key and not API_CIRCUIT_BREAKER["tripped"]:
        url = f"{Config.ECOURTS_API_BASE_URL}/cause-list/check-cnr"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        try:
            res = requests.post(url, headers=headers, json={"cnr": clean_cnr, "date": date}, timeout=15)
            if res.status_code == 200:
                data = res.json()
                return {
                    "success": True,
                    "cnr": clean_cnr,
                    "is_listed": data.get("is_listed", True),
                    "item_number": data.get("item_number", "1"),
                    "court_room": data.get("court_room", "Room 1"),
                    "judge_name": data.get("judge_name", ""),
                    "cost_estimate_rupees": 0.30
                }
        except Exception:
            pass

    return {
        "success": True,
        "cnr": clean_cnr,
        "is_listed": False,
        "cost_estimate_rupees": 0.00
    }
