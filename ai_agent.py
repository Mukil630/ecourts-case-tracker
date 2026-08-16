"""
JARVIS Autonomous Agentic Legal AI Co-Pilot
Specialized for Advocate R. Anbaiya & Associates, Karur District Courts
"""

import time
import sqlite3
import re
from typing import Dict, Any, List
from db import get_daily_cause_list, get_all_cases, get_all_leads, get_advocate_settings

def get_ai_daily_briefing(date_str: str = "") -> Dict[str, Any]:
    """Generates an autonomous agentic morning briefing analyzing urgent matters, rooms, and priorities."""
    if not date_str:
        date_str = time.strftime("%Y-%m-%d")

    data = get_daily_cause_list(date_str)
    courts = data.get("court_summaries", [])
    total_hearings = data.get("total_hearings", 0)
    courts_count = data.get("total_courts", len(courts))

    urgent_cases = []
    warrant_cases = []
    bank_cases = []
    evidence_cases = []

    for court in courts:
        for c in court.get("cases", []):
            stage = (c.get("case_stage") or "").lower()
            title = c.get("case_title") or ""
            notes = (c.get("notes") or "").lower()

            if "warrant" in stage or "warrant" in notes or "nbw" in notes:
                warrant_cases.append(c)
            elif "ia" in stage or "injunction" in notes or "attachment" in stage:
                urgent_cases.append(c)
            
            if "bank" in title.lower() or "sbi" in title.lower() or "baroda" in title.lower():
                bank_cases.append(c)

            if "evidence" in stage or "trial" in stage:
                evidence_cases.append(c)

    court_desc = f"across {courts_count} Courts in Karur" if courts_count > 0 else "across Karur Courts"

    summary_text = (
        f"⚡ **JARVIS Morning Legal Briefing:** You have **{total_hearings} confirmed hearings** today {court_desc}.\n\n"
        f"🚨 **High Priority Action Items:**\n"
    )

    if warrant_cases:
        c = warrant_cases[0]
        summary_text += f"• **Warrant Matter:** Case `{c.get('case_number_formatted') or c.get('cnr_number')}` in **{c.get('court_name')} ({c.get('court_room')}, Item #{c.get('item_number')})** - Presiding: {c.get('judge_name')}.\n"
    
    if urgent_cases:
        c = urgent_cases[0]
        summary_text += f"• **Urgent Interim Application / Execution:** Case `{c.get('case_number_formatted') or c.get('cnr_number')}` in **{c.get('court_name')} ({c.get('court_room')}, Item #{c.get('item_number')})**.\n"

    # Dynamic court strategy
    strategy_lines = []
    for court in courts:
        cname = court.get("court_name", "")
        ccount = court.get("hearings_count", len(court.get("cases", [])))
        sample_item = court.get("cases", [])[0] if court.get("cases") else None
        item_note = f" (Start here for Item #{sample_item.get('item_number')} - {sample_item.get('case_title')})" if sample_item else ""
        strategy_lines.append(f"• **{cname}:** {ccount} cases scheduled{item_note}.")

    strategy_text = "\n".join(strategy_lines) if strategy_lines else "• No active courtroom hearings scheduled for this date."

    summary_text += (
        f"\n🏛️ **Court Room Strategy:**\n"
        f"{strategy_text}\n"
        f"\n📲 **WhatsApp Status:** {total_hearings} client notices are pre-formatted and ready for 1-click dispatch."
    )

    recommended_court = courts[0].get("court_name") + f" ({courts[0].get('cases', [{}])[0].get('court_room', 'Room 1')})" if courts and courts[0].get("cases") else "Karur District Court Complex"

    return {
        "success": True,
        "date": date_str,
        "total_hearings": total_hearings,
        "warrant_count": len(warrant_cases),
        "urgent_count": len(urgent_cases),
        "bank_count": len(bank_cases),
        "briefing_text": summary_text,
        "recommended_first_court": recommended_court
    }


def query_agentic_ai(prompt: str) -> Dict[str, Any]:
    """Answers queries from the advocate using live database intelligence."""
    p = prompt.strip().lower()
    all_c = get_all_cases()
    leads = get_all_leads()
    settings = get_advocate_settings()
    lawyer = settings.get("lawyer_name", "Advocate R. Anbaiya")

    # 1. Urgent / Priority Queries
    if "urgent" in p or "warrant" in p or "priority" in p or "mukkiyam" in p:
        urgent_list = [c for c in all_c if "warrant" in (c.get("case_stage") or "").lower() or "ia" in (c.get("case_stage") or "").lower() or "attachment" in (c.get("case_stage") or "").lower()]
        resp = f"🚨 **JARVIS Identified {len(urgent_list)} Urgent Matters for {lawyer}:**\n\n"
        for c in urgent_list:
            resp += f"• **{c.get('case_number_formatted') or c.get('cnr_number')}** ({c.get('client_name')}): {c.get('court_name')} &bull; **{c.get('court_room')} (Item #{c.get('item_number')})** &bull; Stage: *{c.get('case_stage')}*\n"
        return {"success": True, "reply": resp}

    # 2. Bank / Institutional Matters
    if "bank" in p or "bob" in p or "sbi" in p:
        bank_list = [c for c in all_c if "bank" in (c.get("case_title") or "").lower() or "sbi" in (c.get("case_title") or "").lower()]
        resp = f"🏦 **Found {len(bank_list)} Institutional / Bank Matters:**\n\n"
        for c in bank_list:
            resp += f"• **{c.get('case_number_formatted') or c.get('cnr_number')}** &bull; {c.get('case_title')}\n  🏛️ {c.get('court_name')} ({c.get('court_room')}, Item #{c.get('item_number')}) &bull; Date: **{c.get('next_hearing_date')}**\n"
        return {"success": True, "reply": resp}

    # 3. Judge Specific Queries
    if "priyanga" in p or "sub judge" in p:
        priyanga_list = [c for c in all_c if "priyanga" in (c.get("judge_name") or "").lower() or ("sub court" in (c.get("court_name") or "").lower() and "room 3" in (c.get("court_room") or "").lower())]
        resp = f"⚖️ **Cases before Tmt. K.L. Priyanga, Principal Sub Judge (Room 3):**\n\n"
        for c in priyanga_list:
            resp += f"• **Item #{c.get('item_number')}** &bull; {c.get('case_number_formatted') or c.get('cnr_number')} ({c.get('client_name')}) &bull; Stage: *{c.get('case_stage')}*\n"
        return {"success": True, "reply": resp}

    # 4. Leads / Inquiries
    if "lead" in p or "inquiry" in p or "pudhu" in p:
        resp = f"👥 **Prospective Client Pipeline ({len(leads)} Leads):**\n\n"
        if not leads:
            resp += "No pending leads. Click '+ Add Client' or 'Case Leads' to register prospective inquiries."
        else:
            for l in leads:
                resp += f"• **{l.get('client_name')}** ({l.get('client_phone')}): {l.get('matter_type')} &bull; Status: `{l.get('status')}`\n"
        return {"success": True, "reply": resp}

    # 5. General / Catch-All
    total_active = len([c for c in all_c if (c.get("case_status") or "").upper() != "DISPOSED"])
    today_cause_list = get_daily_cause_list(time.strftime("%Y-%m-%d"))
    today_hearings_count = today_cause_list.get("total_hearings", 0)

    return {
        "success": True,
        "reply": (
            f"⚡ **JARVIS Legal AI Assistant Ready, Boss!**\n\n"
            f"• **Chamber:** {settings.get('firm_name')}\n"
            f"• **Active Monitored Cases:** {total_active} Cases\n"
            f"• **Today's Hearings:** {today_hearings_count} Cases Scheduled in Karur\n\n"
            f"💡 *You can ask me:*\n"
            f"1. *'Show urgent warrant cases today'*\n"
            f"2. *'List Bank of Baroda suits'*\n"
            f"3. *'Which court room should {lawyer} visit first?'*\n"
            f"4. *'Show all client inquiries'*."
        )
    }
