import os
import requests
import json
import re
import urllib.parse
from typing import Dict, Any, Optional
from app.config import Config
from app.db.repository import get_advocate_settings

def get_meta_config() -> Dict[str, Any]:
    """Retrieves Meta WhatsApp Cloud API credentials from environment or database settings."""
    token = Config.META_WA_TOKEN
    phone_id = Config.META_PHONE_ID
    waba_id = Config.META_WABA_ID
    
    if not token or not phone_id:
        try:
            settings = get_advocate_settings()
            token = token or settings.get("meta_access_token", "")
            phone_id = phone_id or settings.get("meta_phone_number_id", "")
            waba_id = waba_id or settings.get("meta_waba_id", "")
        except Exception:
            pass

    return {
        "token": str(token).strip(),
        "phone_id": str(phone_id).strip(),
        "waba_id": str(waba_id).strip(),
        "configured": bool(str(token).strip() and str(phone_id).strip())
    }

def clean_phone_number(raw_phone: str) -> str:
    """Formats phone number to international E.164 without plus sign (e.g. 919842112233)."""
    digits = re.sub(r"[^0-9]", "", str(raw_phone or ""))
    # If 10 digits (Standard Indian mobile), prepend 91
    if len(digits) == 10:
        return "91" + digits
    # If 12 digits starting with 91, return as is
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    return digits

def send_meta_whatsapp_message(
    to_phone: str,
    message_text: str,
    template_name: Optional[str] = None,
    template_params: Optional[list] = None
) -> Dict[str, Any]:
    """
    Dispatches an official message via Meta WhatsApp Business Cloud API.
    Supports direct text messages and approved templates.
    """
    config = get_meta_config()
    if not config["configured"]:
        return {
            "success": False,
            "error": "Meta WhatsApp Cloud API is not configured. Please add Phone Number ID & Access Token.",
            "mode": "unconfigured"
        }

    phone_id = config["phone_id"]
    token = config["token"]
    clean_to = clean_phone_number(to_phone)

    if not clean_to or len(clean_to) < 10:
        return {
            "success": False,
            "error": f"Invalid recipient phone number: '{to_phone}'"
        }

    url = f"https://graph.facebook.com/{Config.META_GRAPH_API_VERSION}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    if template_name:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": str(p)} for p in (template_params or [])]
                    }
                ]
            }
        }
    else:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_text
            }
        }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        res_data = response.json() if response.text else {}

        if response.status_code in (200, 201):
            msg_id = (res_data.get("messages") or [{}])[0].get("id", "")
            return {
                "success": True,
                "message_id": msg_id,
                "recipient": clean_to,
                "mode": "META_CLOUD_API",
                "status": "SENT"
            }
        else:
            err_msg = (res_data.get("error") or {}).get("message", response.text)
            return {
                "success": False,
                "error": err_msg,
                "status_code": response.status_code,
                "details": res_data
            }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Meta Graph API timeout (20s). Please check your internet connection."
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to send Meta WhatsApp message: {str(e)}"
        }

def format_legal_notice_text(case: Dict[str, Any], settings: Optional[Dict[str, Any]] = None) -> str:
    """Formats an official, polished court appearance WhatsApp message for client communication."""
    if not settings:
        settings = get_advocate_settings()

    firm_name = settings.get("firm_name") or "R. ANBAIYA & ASSOCIATES"
    lawyer_name = settings.get("lawyer_name") or "Advocate R. Anbaiya"
    lawyer_phone = settings.get("lawyer_phone") or "+919842112233"
    footer = settings.get("default_whatsapp_footer") or f"Office Helpline: {lawyer_phone}"

    client_name = case.get("client_name") or "Valued Client"
    case_num = case.get("case_number_formatted") or case.get("cnr_number")
    hearing_date = case.get("next_hearing_date") or "Next Scheduled Court Date"
    court = case.get("court_name") or "Karur District Court"
    stage = case.get("case_stage") or "Hearing / Evidence"
    room = case.get("court_room") or "Room 1"
    item = case.get("item_number") or "-"

    msg = (
        f"⚖️ *{firm_name.upper()}*\n"
        f"📋 *OFFICIAL COURT HEARING NOTICE*\n"
        f"---------------------------------------\n"
        f"Dear *{client_name}*,\n\n"
        f"Please be informed regarding the upcoming hearing of your legal matter:\n\n"
        f"📁 *Case Number:* `{case_num}`\n"
        f"📅 *Hearing Date:* *{hearing_date}*\n"
        f"🏛️ *Court:* {court}\n"
        f"🚪 *Court Room:* {room} (Item #{item})\n"
        f"⚡ *Stage of Case:* *{stage}*\n"
        f"---------------------------------------\n"
        f"Kindly be present at the courtroom on time with necessary documents.\n\n"
        f"Advocate in Charge: *{lawyer_name}*\n"
        f"{footer}"
    )
    return msg

def generate_whatsapp_web_link(phone: str, text: str) -> str:
    """Generates standard https://wa.me link with URL-encoded message text."""
    clean = clean_phone_number(phone)
    encoded = urllib.parse.quote(text)
    return f"https://wa.me/{clean}?text={encoded}"
