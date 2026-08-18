import time
import re
from typing import Dict, Any, List
from app.db.repository import get_daily_cause_list, get_all_cases, get_all_leads, get_advocate_settings

def get_ai_daily_briefing(date_str: str = "") -> Dict[str, Any]:
    """Generates an autonomous agentic morning briefing analyzing urgent matters, courtrooms, and priorities."""
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

    recommended_court = (
        courts[0].get("court_name") + f" ({courts[0].get('cases', [{}])[0].get('court_room', 'Room 1')})"
        if courts and courts[0].get("cases")
        else "Karur District Court Complex"
    )

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
    if any(w in p for w in ("urgent", "warrant", "priority", "mukkiyam")):
        urgent_list = [
            c for c in all_c
            if "warrant" in (c.get("case_stage") or "").lower()
            or "ia" in (c.get("case_stage") or "").lower()
            or "attachment" in (c.get("case_stage") or "").lower()
        ]
        if urgent_list:
            items = []
            for c in urgent_list[:5]:
                items.append(f"• **{c.get('case_number_formatted') or c.get('cnr_number')}** - {c.get('case_title')} ({c.get('court_name')}, {c.get('court_room')}, Item #{c.get('item_number')}) - Stage: *{c.get('case_stage')}*")
            ans = f"⚖️ **Found {len(urgent_list)} High-Priority Urgent Matters:**\n\n" + "\n".join(items)
        else:
            ans = "✅ No critical warrants or emergency stay applications flagged in your portfolio for today."
        return {"success": True, "answer": ans, "type": "urgent_matters"}

    # 2. Bank / Recovery Case Queries
    if "bank" in p or "sbi" in p or "loan" in p or "recovery" in p or "baroda" in p:
        bank_list = [c for c in all_c if any(term in (c.get("case_title") or "").lower() for term in ("bank", "sbi", "baroda", "finance"))]
        if bank_list:
            items = [f"• **{c.get('case_number_formatted')}**: {c.get('case_title')} in *{c.get('court_name')}* (Stage: {c.get('case_stage')})" for c in bank_list]
            ans = f"🏦 **Found {len(bank_list)} Bank / Finance Matters:**\n\n" + "\n".join(items)
        else:
            ans = "No bank or commercial loan recovery suits currently found."
        return {"success": True, "answer": ans, "type": "bank_matters"}

    # 3. New Client Leads Queries
    if "lead" in p or "inquir" in p or "client" in p and ("new" in p or "prospective" in p):
        if leads:
            items = [f"• **{l.get('client_name')}** ({l.get('client_phone')}) - Matter: *{l.get('matter_type')}* ({l.get('expected_court')})" for l in leads[:4]]
            ans = f"👤 **Active Client Inquiries ({len(leads)} Total):**\n\n" + "\n".join(items)
        else:
            ans = "No pending new client inquiries at this time."
        return {"success": True, "answer": ans, "type": "leads"}

    # 4. Total Portfolio Overview
    if "how many" in p or "total" in p or "summary" in p or "count" in p:
        active_count = len([c for c in all_c if c.get("case_status") == "PENDING"])
        disposed_count = len([c for c in all_c if c.get("case_status") == "DISPOSED"])
        ans = (
            f"📊 **Law Chambers Case Portfolio Overview for {lawyer}:**\n\n"
            f"• **Total Active Cases:** {active_count}\n"
            f"• **Disposed / Concluded Cases:** {disposed_count}\n"
            f"• **Total Tracked Portfolio:** {len(all_c)} cases across Karur District & Sessions Courts\n"
            f"• **Prospective Client Leads:** {len(leads)} active inquiries\n"
            f"• **System Sync Engine:** Smart predictive polling active (100% zero credit burn protection)."
        )
        return {"success": True, "answer": ans, "type": "summary"}

    # Default fallback
    return {
        "success": True,
        "answer": f"🤖 **JARVIS Co-Pilot:** I am tracking {len(all_c)} cases for {lawyer}. You can ask me about today's urgent warrants, bank suits, upcoming court schedules, or new client inquiries.",
        "type": "general"
    }
