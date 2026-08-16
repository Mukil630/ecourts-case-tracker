"""
Official Meta WhatsApp Business Cloud API Client
Provides official, 100% ban-safe, enterprise-grade WhatsApp message dispatching
using Meta's Graph API (1,000 Free Service Conversations per month).
"""

import os
import requests
import json
import re
from typing import Dict, Any, Optional

META_GRAPH_API_VERSION = "v21.0"
DEFAULT_BASE_URL = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"

def get_meta_config() -> Dict[str, str]:
    """Retrieves Meta WhatsApp Cloud API credentials from env or database."""
    token = os.environ.get("META_WA_TOKEN") or os.environ.get("WHATSAPP_API_TOKEN") or ""
    phone_id = os.environ.get("META_PHONE_ID") or os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or ""
    waba_id = os.environ.get("META_WABA_ID") or os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID") or ""
    
    # Also check SQLite settings fallback
    if not token or not phone_id:
        try:
            from db import get_advocate_settings
            settings = get_advocate_settings()
            token = token or settings.get("meta_access_token", "")
            phone_id = phone_id or settings.get("meta_phone_number_id", "")
            waba_id = waba_id or settings.get("meta_waba_id", "")
        except Exception:
            pass

    return {
        "token": token.strip(),
        "phone_id": phone_id.strip(),
        "waba_id": waba_id.strip(),
        "configured": bool(token.strip() and phone_id.strip())
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

    url = f"{DEFAULT_BASE_URL}/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # If template message is specified
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
        # Direct text message
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
        res_data = response.json()

        if response.status_code in [200, 201]:
            message_id = res_data.get("messages", [{}])[0].get("id", "")
            return {
                "success": True,
                "message_id": message_id,
                "recipient": clean_to,
                "status": "SENT_VIA_META_CLOUD_API"
            }
        else:
            error_msg = res_data.get("error", {}).get("message", response.text)
            error_code = res_data.get("error", {}).get("code")
            return {
                "success": False,
                "error": f"Meta API Error ({error_code}): {error_msg}",
                "raw": res_data
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Connection error: {str(e)}"
        }

def format_legal_notice_text(case_data: Dict[str, Any], settings: Dict[str, Any]) -> str:
    """Formats a clean, professional court hearing update notice for WhatsApp."""
    firm = settings.get("firm_name", "R. ANBAIYA & ASSOCIATES").upper()
    lawyer = settings.get("lawyer_name", "Advocate R. Anbaiya")
    footer = settings.get("default_whatsapp_footer", "Sent on behalf of R. Anbaiya & Associates, Advocates & Legal Consultants, Karur")

    client_name = case_data.get("client_name") or "Valued Client"
    case_title = case_data.get("case_title") or "Legal Matter"
    case_no = case_data.get("case_number_formatted") or case_data.get("cnr_number") or "-"
    court = case_data.get("court_name") or "District Court Complex"
    room = case_data.get("court_room") or "-"
    item = case_data.get("item_number") or "-"
    stage = case_data.get("case_stage") or "Hearing"
    hearing_date = case_data.get("next_hearing_date") or "Scheduled Date"
    notes = case_data.get("notes") or ""

    lines = [
        f"⚖️ *{firm}*",
        "📋 *OFFICIAL COURT HEARING NOTICE*",
        "---------------------------------------",
        f"Dear *{client_name}*,",
        "",
        "Please be informed of the confirmed schedule for your court matter:",
        f"• *Case:* {case_title}",
        f"• *Case No:* {case_no}",
        f"• *Court:* {court}",
        f"• *Item No:* #{item} ({room})",
        f"• *Stage / Purpose:* *{stage}*",
        f"• *Hearing Date:* *{hearing_date}*",
    ]

    if notes:
        lines.append(f"• *Advocate Instruction:* {notes}")

    lines.extend([
        "---------------------------------------",
        footer,
        f"*Advocate:* {lawyer}"
    ])

    return "\n".join(lines)
