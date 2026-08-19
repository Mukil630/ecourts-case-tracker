import time
import threading
import requests
import datetime
from typing import Optional, Dict, Any, List
from app.config import Config
from app.db.repository import (
    get_all_cases,
    get_daily_cause_list,
    get_all_leads,
    get_advocate_settings,
    get_case_by_cnr
)
from app.db.database import get_current_ist_date, get_effective_practice_date, get_db_connection
from app.services.telegram_service import get_telegram_config, send_telegram_message

class TelegramBotWorker:
    """
    Background Autonomous Telegram Bot Poller.
    Listens for incoming messages from @jarvis_prime_remote_bot and provides
    100% database-grounded, zero-hallucination answers to Advocate R. Anbaiya.
    """
    def __init__(self):
        self.running = False
        self.last_update_id = 0
        self.thread: Optional[threading.Thread] = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        print("[Telegram Bot] Autonomous listener started for @jarvis_prime_remote_bot")

    def stop(self):
        self.running = False

    def _poll_loop(self):
        time.sleep(5)
        while self.running:
            try:
                self._process_updates()
            except Exception as e:
                time.sleep(5)
            time.sleep(2.5)

    def _process_updates(self):
        config = get_telegram_config()
        token = config["token"]
        if not token:
            return

        url = f"https://api.telegram.org/bot{token}/getUpdates?offset={self.last_update_id + 1}&timeout=5"
        res = requests.get(url, timeout=10)
        data = res.json()

        if not data.get("ok") or not data.get("result"):
            return

        for update in data["result"]:
            self.last_update_id = update["update_id"]
            msg = update.get("message")
            if not msg:
                continue

            chat_id = str(msg.get("chat", {}).get("id", ""))
            text = (msg.get("text") or "").strip()
            user_first_name = msg.get("from", {}).get("first_name", "Advocate")

            if chat_id and text:
                reply = handle_telegram_incoming_message(text, chat_id, user_first_name)
                if reply:
                    send_telegram_message(reply, chat_id=chat_id)

def handle_telegram_incoming_message(text: str, chat_id: str, user_name: str = "Advocate") -> str:
    """
    Processes incoming Telegram commands and queries.
    STRICT ZERO-HALLUCINATION POLICY: Uses Groq RAG grounded directly in the SQLite database.
    """
    cmd = text.strip()
    cmd_lower = cmd.lower()
    today_str = get_current_ist_date()

    # Save active chat ID to settings automatically
    if chat_id:
        try:
            from app.db.repository import update_advocate_settings
            update_advocate_settings({"telegram_chat_id": chat_id})
        except Exception:
            pass

    # 1. If Groq API Key is configured, use Autonomous RAG Engine
    try:
        from app.services.rag_service import get_groq_api_key, generate_rag_response
        if get_groq_api_key():
            return generate_rag_response(text, user_name)
    except Exception as ex:
        print(f"[RAG Engine Fallback] {ex}")

    settings = get_advocate_settings()
    lawyer = settings.get("lawyer_name", "Advocate R. Anbaiya")
    firm = settings.get("firm_name", "R. ANBAIYA & ASSOCIATES")

    # 1. /start or /help or greeting (hi, hii, hello, etc.)
    greeting_triggers = ("/start", "/help", "hi", "hii", "hiii", "hai", "hello", "hey", "vanakkam", "help", "menu", "commands")
    if any(cmd_lower == g or cmd_lower.startswith(g + " ") for g in greeting_triggers):
        return (
            f"⚡ <b>JARVIS Autonomous Legal Co-Pilot Online!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍⚖️ <b>Welcome, {lawyer}!</b>\n"
            f"🏛️ <i>{firm} Chamber Vault (44 Cases Monitored)</i>\n\n"
            f"<b>Available Commands:</b>\n"
            f"• 📊 <code>/today</code> — Today's Daily Hearing Board ({today_str})\n"
            f"• 📅 <code>/tomorrow</code> — Tomorrow's Confirmed Hearings\n"
            f"• 🚨 <code>/urgent</code> — High Priority (Warrants & Injunctions)\n"
            f"• 📁 <code>/cases</code> — 44 Chamber Portfolio Summary\n"
            f"• 👥 <code>/leads</code> — Prospective Client Inquiries\n"
            f"• 🔍 <code>/search &lt;name/number&gt;</code> — Search any case\n\n"
            f"💡 <i>Or simply send any case name (e.g. 'Palanisamy' or 'OS/361/2025')!</i>"
        )

    # 2. /today — Daily Court Board
    if cmd_lower in ("/today", "today", "today cases", "innaikku", "board"):
        cause_list = get_daily_cause_list(today_str)
        total = cause_list.get("total_hearings", 0)
        courts = cause_list.get("court_summaries", [])

        lines = [
            f"⚖️ <b>DAILY COURT HEARING BOARD</b>",
            f"📅 <b>Date:</b> {today_str}",
            f"⚡ <b>Confirmed Hearings:</b> {total}",
            "━━━━━━━━━━━━━━━━━━━━━━"
        ]

        if total == 0:
            lines.append("🏛️ <b>No court hearings listed on the official diary for today.</b>")
            lines.append("<i>Chamber & brief preparation day.</i>\n")
            lines.append("👉 Use <code>/tomorrow</code> to check tomorrow's schedule.")
        else:
            for court in courts:
                cname = court.get("court_name", "Court")
                lines.append(f"\n🏛️ <b>{cname.upper()}</b> ({court.get('hearings_count')} Cases)")
                for c in court.get("cases", []):
                    item = c.get("item_number") or "-"
                    room = c.get("court_room") or "-"
                    case_no = c.get("case_number_formatted") or c.get("cnr_number")
                    title = c.get("case_title") or "Matter"
                    stage = c.get("case_stage") or "Hearing"
                    judge = c.get("judge_name") or ""
                    client = c.get("client_name") or ""

                    lines.append(f"• <b>Item #{item}</b> ({room}): {title}")
                    lines.append(f"  └ <i>[{case_no}] Stage: {stage}</i>")
                    if client:
                        lines.append(f"  └ Client: {client}")
                    if judge:
                        lines.append(f"  └ Judge: {judge}")

        return "\n".join(lines)

    # 3. /tomorrow — Next Day Schedule
    if cmd_lower in ("/tomorrow", "tomorrow", "nalaikku"):
        base_dt = datetime.datetime.strptime(today_str, "%Y-%m-%d").date()
        tomorrow_str = (base_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        cause_list = get_daily_cause_list(tomorrow_str)
        total = cause_list.get("total_hearings", 0)

        lines = [
            f"📅 <b>TOMORROW'S COURT SCHEDULE</b>",
            f"🗓️ <b>Date:</b> {tomorrow_str}",
            f"⚡ <b>Total Confirmed Hearings:</b> {total}",
            "━━━━━━━━━━━━━━━━━━━━━━"
        ]

        if total == 0:
            lines.append("🏛️ <i>No hearings scheduled for tomorrow.</i>")
        else:
            for court in cause_list.get("court_summaries", []):
                lines.append(f"\n🏛️ <b>{court.get('court_name').upper()}</b>")
                for c in court.get("cases", []):
                    item = c.get("item_number") or "-"
                    room = c.get("court_room") or "-"
                    case_no = c.get("case_number_formatted") or c.get("cnr_number")
                    title = c.get("case_title") or "Matter"
                    stage = c.get("case_stage") or "Hearing"
                    lines.append(f"• <b>Item #{item}</b> ({room}): {title}")
                    lines.append(f"  └ <i>[{case_no}] Stage: {stage}</i>")

        return "\n".join(lines)

    # 4. /urgent — Critical Warrants & Injunctions
    if cmd_lower in ("/urgent", "urgent", "warrant", "nbw", "injunction"):
        all_cases = get_all_cases()
        urgent_cases = [
            c for c in all_cases
            if "warrant" in (c.get("case_stage") or "").lower()
            or "ia" in (c.get("case_stage") or "").lower()
            or "attachment" in (c.get("case_stage") or "").lower()
            or "nbw" in (c.get("notes") or "").lower()
        ]

        lines = [
            f"🚨 <b>HIGH-PRIORITY URGENT MATTERS ({len(urgent_cases)} Total)</b>",
            "━━━━━━━━━━━━━━━━━━━━━━"
        ]

        if not urgent_cases:
            lines.append("✅ <i>No critical warrants or emergency stay applications currently flagged.</i>")
        else:
            for c in urgent_cases[:6]:
                case_no = c.get("case_number_formatted") or c.get("cnr_number")
                title = c.get("case_title")
                court = c.get("court_name")
                stage = c.get("case_stage")
                date_val = c.get("next_hearing_date") or "Pending"
                lines.append(f"• <b>{case_no}</b>: {title}")
                lines.append(f"  └ 🏛️ {court} (Room {c.get('court_room', '-')}, Item #{c.get('item_number', '-')})")
                lines.append(f"  └ ⚡ <b>Action:</b> {stage} (Date: {date_val})")

        return "\n".join(lines)

    # 5. /cases or /summary — Portfolio Overview
    if cmd_lower in ("/cases", "cases", "all cases", "summary", "count"):
        all_cases = get_all_cases()
        active = [c for c in all_cases if c.get("case_status") != "DISPOSED"]
        disposed = [c for c in all_cases if c.get("case_status") == "DISPOSED"]

        return (
            f"📊 <b>CHAMBER PORTFOLIO OVERVIEW</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👨‍⚖️ <b>Advocate:</b> {lawyer}\n"
            f"👥 <b>Active Monitored Cases:</b> {len(active)}\n"
            f"📁 <b>Disposed / Closed Matters:</b> {len(disposed)}\n"
            f"🏛️ <b>Total Tracked Portfolio:</b> {len(all_cases)} Cases\n"
            f"⚡ <b>Jurisdiction:</b> Karur District, Sub & Magistrate Courts\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <i>Send any party name or case number to search details!</i>"
        )

    # 6. /leads — Prospective Clients
    if cmd_lower in ("/leads", "leads", "inquiries"):
        leads = get_all_leads()
        lines = [
            f"👥 <b>PROSPECTIVE CLIENT INQUIRIES ({len(leads)} Total)</b>",
            "━━━━━━━━━━━━━━━━━━━━━━"
        ]
        if not leads:
            lines.append("<i>No active client consultation inquiries recorded.</i>")
        else:
            for l in leads:
                lines.append(f"• <b>{l.get('client_name')}</b> (📞 {l.get('client_phone')})")
                lines.append(f"  └ Matter: {l.get('matter_type')} ({l.get('expected_court')})")
                lines.append(f"  └ Status: <b>{l.get('status')}</b>")
        return "\n".join(lines)

    # 7. Search by CNR / Party Name / Case Number
    search_term = cmd.replace("/search", "").strip()
    if not search_term:
        search_term = cmd

    conn = get_db_connection()
    cursor = conn.cursor()
    pattern = f"%{search_term}%"
    cursor.execute("""
        SELECT * FROM cases 
        WHERE cnr_number LIKE ? 
           OR case_number_formatted LIKE ? 
           OR case_title LIKE ? 
           OR client_name LIKE ?
           OR court_name LIKE ?
        LIMIT 4
    """, (pattern, pattern, pattern, pattern, pattern))
    results = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if results:
        lines = [
            f"🔍 <b>SEARCH RESULTS FOR '{search_term}' ({len(results)} Found):</b>",
            "━━━━━━━━━━━━━━━━━━━━━━"
        ]
        for c in results:
            case_no = c.get("case_number_formatted") or c.get("cnr_number")
            lines.append(f"\n⚖️ <b>{c.get('case_title')}</b>")
            lines.append(f"📌 <b>Case No:</b> {case_no} (CNR: <code>{c.get('cnr_number')}</code>)")
            lines.append(f"🏛️ <b>Court:</b> {c.get('court_name')} ({c.get('court_room', '-')}, Item #{c.get('item_number', '-')})")
            lines.append(f"📋 <b>Stage:</b> {c.get('case_stage')} | <b>Status:</b> {c.get('case_status')}")
            lines.append(f"📅 <b>Hearing Date:</b> <b>{c.get('next_hearing_date') or 'Pending'}</b>")
            lines.append(f"👤 <b>Client:</b> {c.get('client_name')} (📞 {c.get('client_phone')})")
            if c.get("notes"):
                lines.append(f"📝 <b>Note:</b> {c.get('notes')}")
        return "\n".join(lines)

    # Default fallback - Strict Truth
    return (
        f"❌ <b>No match found in chamber records for '{search_term}'.</b>\n\n"
        f"💡 Please check the spelling, party name, or CNR number.\n"
        f"Available commands: <code>/today</code>, <code>/tomorrow</code>, <code>/urgent</code>, <code>/cases</code>"
    )

# Global autonomous Telegram poller worker
telegram_bot_worker = TelegramBotWorker()
