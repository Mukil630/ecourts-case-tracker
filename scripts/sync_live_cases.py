import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app.services.ecourts_service import fetch_case_details, get_api_key
from app.db.repository import upsert_case
from app.db.database import init_db

def sync_live_verified_cases():
    api_key = get_api_key()
    print(f"[*] eCourts API Key: {api_key[:8]}...{api_key[-4:] if len(api_key)>12 else '***'}")

    verified_cnrs = [
        ("DLND020047882015", "Arun Jaitley", "+919876543210"),
        ("TNCH010000012024", "Lawrence Raj", "+919842112233"),
        ("TNKR010010352023", "M Palanisamy", "+919443322110"),
        ("TNKR020003832025", "G Eniyavan", "+919842112233"),
        ("TNKR050003592024", "Kathiravan", "+919789012345")
    ]

    init_db()

    for cnr, client_name, client_phone in verified_cnrs:
        print(f"\n[*] Fetching live eCourts data for {cnr} ({client_name})...")
        res = fetch_case_details(cnr, force_live=True)
        if res.get("success"):
            print(f"  [+] Court: {res.get('court_name')}")
            print(f"  [+] Title: {res.get('case_title')}")
            print(f"  [+] Status: {res.get('case_status')} | Next Date: {res.get('next_hearing_date')}")
            print(f"  [+] Parties: {res.get('parties')}")
            print(f"  [+] Advocates: {res.get('advocates')}")
            print(f"  [+] Room: {res.get('court_room')} | Judge: {res.get('judge_name')}")

            db_payload = {
                "cnr_number": res.get("cnr_number") or cnr,
                "case_title": res.get("case_title"),
                "case_status": res.get("case_status") or "PENDING",
                "court_name": res.get("court_name"),
                "parties": res.get("parties"),
                "advocates": res.get("advocates"),
                "last_hearing_date": res.get("last_hearing_date"),
                "next_hearing_date": res.get("next_hearing_date")
            }

            upsert_case(
                db_payload,
                client_name=client_name,
                client_phone=client_phone,
                case_number_formatted=res.get("case_number_formatted") or cnr,
                case_stage=res.get("case_stage") or "Evidence",
                court_room=res.get("court_room") or "Room 1",
                item_number="1",
                judge_name=res.get("judge_name") or ""
            )
            print(f"  [✓] Successfully upserted into local chamber database.")
        else:
            print(f"  [X] Failed: {res.get('error')}")

if __name__ == "__main__":
    sync_live_verified_cases()
