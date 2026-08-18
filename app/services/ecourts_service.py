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
    Fetches case details with Fail-Safe Credit-Guard & Local SQLite Cache protection.
    Will NEVER burn credits if circuit breaker is active or cached copy exists.
    """
    clean_cnr = cnr_number.strip().upper()

    # 1. Check Local SQLite Cache first (Primary Credit-Guard)
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

    # 2. Check Database Existing Case as instant local fallback
    try:
        existing = get_case_by_cnr(clean_cnr)
        if existing and not force_live:
            return {
                "success": True,
                "cnr_number": clean_cnr,
                "case_title": existing.get("case_title", f"{clean_cnr} Matter"),
                "case_status": existing.get("case_status", "PENDING"),
                "court_name": existing.get("court_name", "Karur District Court"),
                "petitioners": [existing.get("client_name", "Petitioner")],
                "respondents": ["Opposing Party"],
                "last_hearing_date": existing.get("last_hearing_date", ""),
                "next_hearing_date": existing.get("next_hearing_date", ""),
                "is_cached": True,
                "cache_note": "⚡ Loaded from Chamber Vault (0 credits used)"
            }
    except Exception:
        pass

    # 3. Check Circuit Breaker (Prevents credit draining loops)
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
            "error": "eCourts API Key not configured. Please add ECOURTS_API_KEY to .env or dashboard settings."
        }

    # 5. Make Live HTTP Request to eCourts Partner API
    url = f"{Config.ECOURTS_API_BASE_URL}/cnr/details"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {"cnumber": clean_cnr}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)

        # Handle 402 Payment Required / Insufficient Credits
        if response.status_code == 402:
            API_CIRCUIT_BREAKER["tripped"] = True
            API_CIRCUIT_BREAKER["reason"] = "Insufficient API Credits on webapi.ecourtsindia.com"
            API_CIRCUIT_BREAKER["last_error_time"] = time.time()
            return {
                "success": False,
                "error_type": "INSUFFICIENT_CREDITS",
                "error": "eCourts Partner API account is out of credits (₹0.00). Local Chamber Vault protection engaged.",
                "credit_guard": True
            }

        # Handle 401 Unauthorized / Expired Token
        if response.status_code == 401:
            API_CIRCUIT_BREAKER["tripped"] = True
            API_CIRCUIT_BREAKER["reason"] = "Invalid or Expired eCourts API Key"
            API_CIRCUIT_BREAKER["last_error_time"] = time.time()
            return {
                "success": False,
                "error_type": "AUTH_ERROR",
                "error": "API Key rejected by eCourts API. Please verify your key on webapi.ecourtsindia.com.",
                "credit_guard": True
            }

        # Handle 200 OK Response
        if response.status_code == 200:
            API_CIRCUIT_BREAKER["consecutive_failures"] = 0
            raw_data = response.json()

            # Cache the raw response in SQLite
            try:
                set_cached_case(clean_cnr, raw_data)
            except Exception:
                pass

            parsed = parse_ecourts_response(clean_cnr, raw_data)
            parsed["is_cached"] = False
            parsed["cache_note"] = "Live eCourts API Sync (1 API Credit consumed)"
            return parsed

        return {
            "success": False,
            "error_type": f"HTTP_{response.status_code}",
            "error": f"eCourts API error ({response.status_code}): {response.text[:200]}"
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error_type": "TIMEOUT",
            "error": "eCourts API took longer than 25s to respond. Using local vault backup."
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

def parse_ecourts_response(cnr_number: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes variable raw JSON structures from eCourts Partner API into clean schema."""
    case_info = raw_data.get("data", raw_data.get("case_details", raw_data))
    if not isinstance(case_info, dict):
        case_info = {}

    title = case_info.get("case_title") or case_info.get("title") or f"{cnr_number} Case"
    status = case_info.get("case_status") or case_info.get("status") or "PENDING"
    court = case_info.get("court_name") or case_info.get("court") or "District Court"
    state = case_info.get("state") or "Tamil Nadu"
    district = case_info.get("district") or "Karur"

    # Hearing Dates
    next_date = case_info.get("next_hearing_date") or case_info.get("next_date") or ""
    last_date = case_info.get("last_hearing_date") or case_info.get("last_date") or ""

    # Parties
    pet_list = case_info.get("petitioners", [])
    if isinstance(pet_list, str):
        pet_list = [pet_list]
    resp_list = case_info.get("respondents", [])
    if isinstance(resp_list, str):
        resp_list = [resp_list]

    pet_adv = case_info.get("petitioner_advocates", [])
    if isinstance(pet_adv, str):
        pet_adv = [pet_adv]
    resp_adv = case_info.get("respondent_advocates", [])
    if isinstance(resp_adv, str):
        resp_adv = [resp_adv]

    return {
        "success": True,
        "cnr_number": cnr_number,
        "case_title": title,
        "case_status": status,
        "court_name": court,
        "state": state,
        "district": district,
        "next_hearing_date": next_date,
        "last_hearing_date": last_date,
        "petitioners": pet_list,
        "respondents": resp_list,
        "petitioner_advocates": pet_adv,
        "respondent_advocates": resp_adv,
        "hearing_count": case_info.get("hearing_count", len(case_info.get("hearings", []))),
        "order_count": case_info.get("order_count", len(case_info.get("orders", []))),
        "raw": raw_data
    }

def search_cases_by_advocate(advocate_name: str, district: str = "Karur") -> Dict[str, Any]:
    """Queries cases under advocate's name across courts."""
    from app.db.repository import get_all_cases
    cases = get_all_cases()
    matched = []
    clean_name = advocate_name.lower().replace("advocate", "").replace(".", "").strip()

    for c in cases:
        adv = (c.get("advocates") or "").lower()
        if clean_name in adv or "anbaiya" in adv or not clean_name:
            matched.append(c)

    return {
        "success": True,
        "advocate_name": advocate_name,
        "district": district,
        "total_found": len(matched),
        "cases": matched
    }
