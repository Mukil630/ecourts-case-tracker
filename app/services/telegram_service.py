import os
import requests
import json
import time
from typing import Dict, Any, Optional, List
from app.config import Config
from app.db.repository import get_advocate_settings, update_advocate_settings

DEFAULT_BOT_TOKEN = "8206363312:AAH7sjVsT4nj7YtDUceWPRoOCa9d1cM6X6U"

def get_telegram_config() -> Dict[str, Any]:
    """Retrieves Telegram Bot Token and Chat ID from database settings or environment."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or DEFAULT_BOT_TOKEN
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    try:
        settings = get_advocate_settings()
        token = settings.get("telegram_bot_token") or token
        chat_id = settings.get("telegram_chat_id") or chat_id
    except Exception:
        pass

    return {
        "token": str(token).strip(),
        "chat_id": str(chat_id).strip(),
        "configured": bool(str(token).strip() and str(chat_id).strip())
    }

def auto_detect_chat_id(token: Optional[str] = None) -> Optional[str]:
    """
    Checks getUpdates from Telegram to automatically capture the Chat ID
    of the user who started or messaged the bot.
    """
    tok = token or get_telegram_config()["token"]
    if not tok:
        return None

    url = f"https://api.telegram.org/bot{tok}/getUpdates"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if data.get("ok") and data.get("result"):
            # Get the most recent message's chat_id
            for update in reversed(data["result"]):
                msg = update.get("message") or update.get("channel_post") or update.get("my_chat_member")
                if msg and "chat" in msg and "id" in msg["chat"]:
                    detected_id = str(msg["chat"]["id"])
                    # Save to DB settings
                    update_advocate_settings({
                        "telegram_bot_token": tok,
                        "telegram_chat_id": detected_id
                    })
                    return detected_id
    except Exception as e:
        print(f"[Telegram Auto-Detect Error] {e}")
    return None

def send_telegram_message(
    text: str,
    chat_id: Optional[str] = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True
) -> Dict[str, Any]:
    """Dispatches a formatted message to Telegram Bot."""
    config = get_telegram_config()
    tok = config["token"]
    target_chat = chat_id or config["chat_id"]

    if not target_chat:
        # Try auto-detecting chat ID
        target_chat = auto_detect_chat_id(tok)

    if not tok or not target_chat:
        return {
            "success": False,
            "error": "Telegram Bot Token or Chat ID not configured. Please message @jarvis_prime_remote_bot and click Start.",
            "mode": "unconfigured"
        }

    url = f"https://api.telegram.org/bot{tok}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview
    }

    try:
        res = requests.post(url, json=payload, timeout=15)
        res_data = res.json()
        if res_data.get("ok"):
            return {
                "success": True,
                "message_id": res_data.get("result", {}).get("message_id"),
                "chat_id": target_chat
            }
        else:
            return {
                "success": False,
                "error": res_data.get("description", "Unknown Telegram API error")
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def send_morning_docket_telegram(target_date: str = "", chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Formats and dispatches the full Daily Cause List hearing docket to Telegram."""
    from app.db.repository import get_daily_cause_list
    from app.db.database import get_effective_practice_date

    if not target_date:
        target_date = get_effective_practice_date()

    cause_list = get_daily_cause_list(target_date)
    settings = get_advocate_settings()

    firm_name = settings.get("firm_name", "R. ANBAIYA & ASSOCIATES")
    lawyer_name = settings.get("lawyer_name", "Advocate R. Anbaiya")
    total_hearings = cause_list.get("total_hearings", 0)
    total_courts = cause_list.get("total_courts", 0)

    lines = [
        f"⚖️ <b>{firm_name.upper()}</b>",
        f"📋 <b>DAILY COURT HEARING BOARD DOCKET</b>",
        f"📅 <b>Date:</b> {target_date}",
        f"⚡ <b>Total Hearings:</b> {total_hearings} across {total_courts} Court(s)",
        "━━━━━━━━━━━━━━━━━━━━━━"
    ]

    if total_hearings == 0:
        lines.append("🏛️ <i>No court hearings listed on the official diary for today.</i>")
        lines.append("<i>Chamber & brief preparation day.</i>")
    else:
        for summary in cause_list.get("court_summaries", []):
            court_title = summary.get("court_name", "Court")
            lines.append(f"\n🏛️ <b>{court_title.upper()}</b> ({summary.get('hearings_count')} Cases)")
            for c in summary.get("cases", []):
                item_no = c.get("item_number") or "-"
                room = c.get("court_room") or "-"
                case_no = c.get("case_number_formatted") or c.get("cnr_number")
                title = c.get("case_title") or "Matter"
                stage = c.get("case_stage") or "Hearing"
                judge = c.get("judge_name") or ""
                client = c.get("client_name") or ""

                lines.append(f"• <b>Item #{item_no}</b> (Room: {room}): {title}")
                lines.append(f"  └ <i>[{case_no}] Stage: {stage}</i>")
                if client:
                    lines.append(f"  └ Client: {client}")
                if judge:
                    lines.append(f"  └ Judge: {judge}")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🤖 <i>Automated Briefing prepared for: {lawyer_name}</i>")

    full_text = "\n".join(lines)
    return send_telegram_message(full_text, chat_id=chat_id)

def send_adjournment_alert_telegram(case_data: Dict[str, Any], old_date: str, new_date: str, chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Sends real-time date change / adjournment notification via Telegram."""
    case_no = case_data.get("case_number_formatted") or case_data.get("cnr_number")
    title = case_data.get("case_title", "Court Matter")
    court = case_data.get("court_name", "Court")
    stage = case_data.get("case_stage", "Hearing")
    client = case_data.get("client_name", "Client")

    text = (
        f"🔄 <b>HEARING DATE RESCHEDULED ALERT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚖️ <b>Case:</b> {title}\n"
        f"📌 <b>Number:</b> {case_no}\n"
        f"🏛️ <b>Court:</b> {court}\n"
        f"👤 <b>Client:</b> {client}\n"
        f"📋 <b>Stage:</b> {stage}\n\n"
        f"🗓️ <b>Previous Date:</b> {old_date}\n"
        f"➔ <b>NEW HEARING DATE:</b> <b>{new_date}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <i>eCourts Live Sync detected date shift. Client WhatsApp notice ready.</i>"
    )
    return send_telegram_message(text, chat_id=chat_id)

def send_urgent_case_alert_telegram(case_data: Dict[str, Any], chat_id: Optional[str] = None) -> Dict[str, Any]:
    """Sends high-priority alert for warrants, injunctions, or bank matters."""
    case_no = case_data.get("case_number_formatted") or case_data.get("cnr_number")
    title = case_data.get("case_title", "Court Matter")
    stage = case_data.get("case_stage", "Urgent")
    court = case_data.get("court_name", "Court")
    room = case_data.get("court_room", "Room 1")
    item = case_data.get("item_number", "1")

    text = (
        f"🚨 <b>URGENT COURT ACTION REQUIRED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚖️ <b>Case:</b> {title}\n"
        f"📌 <b>Number:</b> {case_no}\n"
        f"🏛️ <b>Court:</b> {court} (Room {room}, Item #{item})\n"
        f"⚡ <b>Urgent Action:</b> {stage}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <i>JARVIS Autonomous Legal Alert</i>"
    )
    return send_telegram_message(text, chat_id=chat_id)
