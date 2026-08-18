import sys
import os
import argparse
from app.services.ecourts_service import fetch_case_details, get_api_key
from app.services.whatsapp_service import format_legal_notice_text
from app.db.database import init_db
from app.db.repository import upsert_case

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def track_and_verify_case(cnr_number: str, client_name: str = "Client", client_phone: str = "+919876543210"):
    print("=" * 65)
    print("          ECOURTS CASE TRACKER & VERIFIER               ")
    print("=" * 65)

    # 1. Check API Key
    api_key = get_api_key()
    if not api_key:
        print("[!] ERROR: ECOURTS_API_KEY is not configured.")
        print("[*] Please configure ECOURTS_API_KEY in your .env file or environment.")
        return

    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    print(f"[*] Auth Token: {masked_key}")
    print(f"[*] Target CNR: {cnr_number}")
    print(f"[*] Client:     {client_name} ({client_phone})")
    print("-" * 65)

    # 2. Initialize Database
    init_db()

    # 3. Call API
    print("[*] Fetching live case details from eCourtsIndia API...")
    result = fetch_case_details(cnr_number)

    if not result.get("success"):
        print(f"\n[X] API Request Failed: [{result.get('error_type')}]")
        print(f"    Message: {result.get('error')}")
        return

    # 4. Display Formatted Case Summary
    print("\n[+] CASE DETAILS RETRIEVED SUCCESSFULLY:")
    print("=" * 65)
    print(f"• Title:             {result.get('case_title')}")
    print(f"• CNR Number:        {result.get('cnr_number')}")
    print(f"• Status:            {result.get('case_status')}")
    print(f"• Court:             {result.get('court_name')}")
    print(f"• State / District:  {result.get('state')} / {result.get('district')}")
    print(f"• Next Hearing Date: {result.get('next_hearing_date') or 'Not Scheduled / Disposed'}")
    print(f"• Last Hearing Date: {result.get('last_hearing_date') or 'N/A'}")
    print(f"• Total Hearings:    {result.get('hearing_count')}")
    print(f"• Total Orders:      {result.get('order_count')}")
    print("=" * 65)

    # 5. Store in Local Database & Detect Hearing Date Changes
    db_payload = {
        "cnr_number": result.get("cnr_number"),
        "case_title": result.get("case_title"),
        "case_status": result.get("case_status"),
        "court_name": result.get("court_name"),
        "parties": f"Petitioner: {', '.join(result.get('petitioners', []))} | Respondent: {', '.join(result.get('respondents', []))}",
        "advocates": f"Petitioner Adv: {', '.join(result.get('petitioner_advocates', []))} | Respondent Adv: {', '.join(result.get('respondent_advocates', []))}",
        "last_hearing_date": result.get("last_hearing_date"),
        "next_hearing_date": result.get("next_hearing_date")
    }

    date_changed = upsert_case(db_payload, client_name=client_name, client_phone=client_phone)

    # 6. Format WhatsApp Alert Message
    whatsapp_message = (
        f"*LEGAL CASE UPDATE*\n"
        f"---------------------------\n"
        f"*Case:* {result.get('case_title')}\n"
        f"*CNR:* `{result.get('cnr_number')}`\n"
        f"*Status:* {result.get('case_status')}\n"
        f"*Court:* {result.get('court_name')}\n"
        f"*Next Hearing Date:* *{result.get('next_hearing_date') or 'Disposed / Awaiting Date'}*\n"
        f"---------------------------\n"
        f"Sent on behalf of Advocate Office."
    )

    print("\n[+] PREPARED WHATSAPP NOTIFICATION:")
    print("--------------------------------------------------")
    print(whatsapp_message)
    print("--------------------------------------------------")

    if date_changed:
        print("\n[!] ALERT: Next Hearing Date change detected! Notification queued.")
    else:
        print("\n[*] Case record saved to SQLite DB. No date change detected since last check.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="eCourts CLI Case Tracker & Verifier")
    parser.add_argument("cnr", nargs="?", default="DLND020047882015", help="16-character CNR Number")
    parser.add_argument("--name", default="Client", help="Client name")
    parser.add_argument("--phone", default="+919876543210", help="Client phone number")
    args = parser.parse_args()

    track_and_verify_case(args.cnr, args.name, args.phone)
