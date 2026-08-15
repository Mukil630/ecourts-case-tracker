import os
import sys
import json
import requests
from typing import Optional, Dict, Any

# Ensure UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def get_api_key() -> str:
    """Reads API key from environment variable or .env file."""
    key = os.environ.get("ECOURTS_API_KEY")
    if key and key != "your_api_key_here":
        return key.strip()

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ECOURTS_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    if key and key != "your_api_key_here":
                        return key
    return ""

def fetch_case_details(cnr_number: str) -> Dict[str, Any]:
    """
    Fetches full case details from official eCourtsIndia Partner API.
    Endpoint: GET https://webapi.ecourtsindia.com/api/partner/case/{cnr}
    """
    api_key = get_api_key()
    if not api_key:
        return {
            "success": False,
            "error_type": "MISSING_KEY",
            "error": "API Key not configured. Please paste your token in .env file."
        }

    clean_cnr = cnr_number.strip().upper()
    url = f"https://webapi.ecourtsindia.com/api/partner/case/{clean_cnr}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error_type": "NETWORK_ERROR",
            "error": f"Failed to connect to API: {str(e)}"
        }

    if response.status_code == 200:
        raw_json = response.json()
        return parse_ecourts_response(clean_cnr, raw_json)
    
    elif response.status_code == 401:
        return {
            "success": False,
            "status_code": 401,
            "error_type": "INVALID_TOKEN",
            "error": "Bearer token is invalid or expired. Check your ECOURTS_API_KEY in .env"
        }
    elif response.status_code == 402:
        return {
            "success": False,
            "status_code": 402,
            "error_type": "INSUFFICIENT_CREDITS",
            "error": "Account credits exhausted or subscription required."
        }
    elif response.status_code == 404:
        return {
            "success": False,
            "status_code": 404,
            "error_type": "CASE_NOT_FOUND",
            "error": f"Case with CNR '{clean_cnr}' not found in court records."
        }
    elif response.status_code == 429:
        return {
            "success": False,
            "status_code": 429,
            "error_type": "RATE_LIMIT",
            "error": "Rate limit exceeded. Please wait a moment before trying again."
        }
    else:
        return {
            "success": False,
            "status_code": response.status_code,
            "error_type": "API_ERROR",
            "error": response.text
        }

def parse_ecourts_response(cnr_number: str, raw_json: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts standardized case fields according to official eCourtsIndia schema."""
    data = raw_json.get("data", {})
    case_data = data.get("courtCaseData", {})
    entity_info = data.get("entityInfo", {})

    petitioners = case_data.get("petitioners", [])
    respondents = case_data.get("respondents", [])
    petitioner_advs = case_data.get("petitionerAdvocates", [])
    respondent_advs = case_data.get("respondentAdvocates", [])

    # Format Title
    petitioner_str = ", ".join(petitioners) if petitioners else "Petitioner"
    respondent_str = ", ".join(respondents) if respondents else "Respondent"
    case_title = f"{petitioner_str} vs {respondent_str}"

    # Extract Latest / Next Hearing
    next_hearing = case_data.get("nextHearingDate") or entity_info.get("nextDateOfHearing", "")
    if next_hearing and "T" in str(next_hearing):
        next_hearing = next_hearing.split("T")[0]

    last_hearing = case_data.get("lastHearingDate") or entity_info.get("lastDateOfHearing", "")
    if last_hearing and "T" in str(last_hearing):
        last_hearing = last_hearing.split("T")[0]

    return {
        "success": True,
        "cnr_number": cnr_number,
        "case_title": case_title,
        "case_status": case_data.get("caseStatus", "UNKNOWN"),
        "case_type": case_data.get("caseType", ""),
        "case_type_desc": case_data.get("caseTypeRaw", ""),
        "court_name": case_data.get("courtName", ""),
        "district": case_data.get("district", ""),
        "state": case_data.get("state", ""),
        "petitioners": petitioners,
        "respondents": respondents,
        "petitioner_advocates": petitioner_advs,
        "respondent_advocates": respondent_advs,
        "filing_date": case_data.get("filingDate", ""),
        "registration_number": case_data.get("registrationNumber", ""),
        "last_hearing_date": str(last_hearing),
        "next_hearing_date": str(next_hearing),
        "decision_date": case_data.get("decisionDate", ""),
        "order_count": case_data.get("orderCount", 0),
        "hearing_count": case_data.get("hearingCount", 0),
        "purpose": case_data.get("purpose", ""),
        "request_id": raw_json.get("meta", {}).get("request_id") or raw_json.get("meta", {}).get("requestId", ""),
        "raw_response": raw_json
    }
