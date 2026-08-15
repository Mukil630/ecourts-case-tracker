import sys
import json
from ecourts_api import fetch_case_by_cnr, get_api_key
from db import init_db, upsert_case

def test_cnr_flow(test_cnr: str = "MHAU019999992015"):
    print("==================================================")
    print("      eCourts API Test Runner (Phase 1)           ")
    print("==================================================")

    # 1. Check API Key
    api_key = get_api_key()
    if not api_key:
        print("[!] ERROR: No API Key found.")
        print("[*] Please open 'C:\\Users\\mukil\\ecourts_automation\\.env'")
        print("[*] Add: ECOURTS_API_KEY=your_actual_key_here")
        return

    print(f"[*] API Key detected: {'*' * (len(api_key)-4) + api_key[-4:] if len(api_key) > 4 else '***'}")
    print(f"[*] Testing with CNR: {test_cnr}")

    # 2. Initialize Database
    init_db()

    # 3. Call API
    print("\n[*] Sending request to eCourts API...")
    try:
        case_data = fetch_case_by_cnr(test_cnr)
        print("\n--- API RESPONSE ---")
        print(json.dumps(case_data, indent=2))

        if case_data.get("success"):
            # 4. Store in DB
            date_changed = upsert_case(case_data, client_name="Test Client", client_phone="+919999999999")
            print("\n[+] SUCCESS! Case saved to SQLite Database.")
            print(f"[+] Date Changed Flag: {date_changed}")
        else:
            print(f"\n[!] Notice from API: {case_data.get('error')}")

    except Exception as e:
        print(f"\n[!] Error during API call: {e}")

if __name__ == "__main__":
    cnr = sys.argv[1] if len(sys.argv) > 1 else "MHAU019999992015"
    test_cnr_flow(cnr)
