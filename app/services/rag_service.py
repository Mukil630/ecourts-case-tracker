import os
import json
import requests
import datetime
from typing import Dict, Any, List, Optional
from app.config import Config
from app.db.repository import (
    get_all_cases,
    get_daily_cause_list,
    get_all_leads,
    get_advocate_settings
)
from app.db.database import get_current_ist_date, get_db_connection

def get_groq_api_key() -> str:
    """Retrieves Groq API key from environment, settings, or .env file."""
    key = os.environ.get("GROQ_API_KEY", "")
    if key and len(key.strip()) > 10:
        return key.strip()

    try:
        settings = get_advocate_settings()
        key = settings.get("groq_api_key") or ""
        if key and len(key.strip()) > 10:
            return key.strip()
    except Exception:
        pass

    env_path = Config.BASE_DIR / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GROQ_API_KEY="):
                        val = line.strip().split("=", 1)[1].strip()
                        if val and len(val) > 10:
                            return val
        except Exception:
            pass
    return ""

def retrieve_chamber_context(query: str, today_str: Optional[str] = None) -> Dict[str, Any]:
    """
    RAG Retrieval Step:
    Fetches structured chamber intelligence from SQLite database based on the query.
    """
    if not today_str:
        today_str = get_current_ist_date()

    all_cases = get_all_cases()
    today_cause_list = get_daily_cause_list(today_str)
    
    # Calculate tomorrow's date and cause list
    base_dt = datetime.datetime.strptime(today_str, "%Y-%m-%d").date()
    tomorrow_str = (base_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_cause_list = get_daily_cause_list(tomorrow_str)

    leads = get_all_leads()
    settings = get_advocate_settings()

    # Search specific cases relevant to query keywords
    conn = get_db_connection()
    cursor = conn.cursor()
    words = [w.strip() for w in query.split() if len(w.strip()) > 2 and not w.startswith("/")]
    
    matched_cases = []
    if words:
        conditions = []
        params = []
        for w in words[:4]:
            conditions.append("(cnr_number LIKE ? OR case_number_formatted LIKE ? OR case_title LIKE ? OR client_name LIKE ? OR court_name LIKE ? OR case_stage LIKE ?)")
            p = f"%{w}%"
            params.extend([p, p, p, p, p, p])
        sql = f"SELECT * FROM cases WHERE {' OR '.join(conditions)} LIMIT 10"
        cursor.execute(sql, params)
        matched_cases = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # High priority urgent cases
    urgent_cases = [
        c for c in all_cases
        if "warrant" in (c.get("case_stage") or "").lower()
        or "ia" in (c.get("case_stage") or "").lower()
        or "attachment" in (c.get("case_stage") or "").lower()
        or "nbw" in (c.get("notes") or "").lower()
    ]

    active_cases = [c for c in all_cases if c.get("case_status") != "DISPOSED"]
    disposed_cases = [c for c in all_cases if c.get("case_status") == "DISPOSED"]

    return {
        "today_date": today_str,
        "tomorrow_date": tomorrow_str,
        "lawyer_name": settings.get("lawyer_name", "Advocate R. Anbaiya"),
        "firm_name": settings.get("firm_name", "R. ANBAIYA & ASSOCIATES"),
        "total_monitored_cases": len(all_cases),
        "active_cases_count": len(active_cases),
        "disposed_cases_count": len(disposed_cases),
        "today_hearings": today_cause_list.get("court_summaries", []),
        "today_total_hearings": today_cause_list.get("total_hearings", 0),
        "tomorrow_hearings": tomorrow_cause_list.get("court_summaries", []),
        "tomorrow_total_hearings": tomorrow_cause_list.get("total_hearings", 0),
        "urgent_cases": urgent_cases[:6],
        "matched_cases": matched_cases,
        "leads": leads[:5]
    }

def generate_rag_response(user_query: str, user_name: str = "Advocate") -> str:
    """
    RAG Generation Step via Groq LLM (LLaMA 3.3 70B / LLaMA 3.1 8B).
    Synthesizes a natural, highly intelligent, perfectly accurate response
    grounded 100% in the retrieved SQLite database context.
    """
    today_str = get_current_ist_date()
    context = retrieve_chamber_context(user_query, today_str)
    groq_key = get_groq_api_key()

    if not groq_key:
        # Fallback to local grounded responder if Groq key not set yet
        from app.services.telegram_bot_engine import handle_telegram_incoming_message
        return handle_telegram_incoming_message(user_query, "", user_name)

    system_prompt = f"""You are JARVIS, an autonomous elite AI Legal Co-Pilot assisting {context['lawyer_name']} at {context['firm_name']}, Karur.
Today's Date in Indian Standard Time (IST): {context['today_date']}.

You have direct access to the live, verified Chamber Case Vault & Court Board Database:
--------------------------------------------------
CHAMBER CONTEXT:
• Law Firm: {context['firm_name']}
• Advocate: {context['lawyer_name']}
• Total Monitored Portfolio: {context['total_monitored_cases']} cases ({context['active_cases_count']} Active, {context['disposed_cases_count']} Disposed)
• Today's Hearings ({context['today_date']}): {context['today_total_hearings']} confirmed hearings on court diary.
• Today's Court Schedule Details: {json.dumps(context['today_hearings'], ensure_ascii=False)}
• Tomorrow's Schedule ({context['tomorrow_date']}): {context['tomorrow_total_hearings']} confirmed hearings.
• Tomorrow's Court Schedule Details: {json.dumps(context['tomorrow_hearings'], ensure_ascii=False)}
• Urgent Matters (Warrants/Injunctions): {json.dumps(context['urgent_cases'], ensure_ascii=False)}
• Query-Matched Case Records: {json.dumps(context['matched_cases'], ensure_ascii=False)}
• Client Leads / Consultations: {json.dumps(context['leads'], ensure_ascii=False)}
--------------------------------------------------

STRICT GUIDELINES:
1. TRUTHFULNESS & ZERO HALLUCINATION: Only answer using facts present in the Chamber Context above. Never invent dates, judges, courtrooms, or case numbers.
2. TODAY'S HEARINGS: If today has 0 hearings, explicitly state that there are no hearings scheduled for today ({context['today_date']}), and mention upcoming hearings (like tomorrow {context['tomorrow_date']}).
3. TONE & STYLE: Professional, concise, intelligent, and warm. You can use standard formatting with emojis (🏛️, ⚖️, 📌, 📅, 🚨).
4. MULTILINGUAL: If the user communicates in Tanglish (Tamil + English) or Tamil, answer naturally and fluently in Tanglish/English with warmth.
5. KEEP RESPONSES ACTIONABLE for Telegram mobile chat.
"""

    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        "temperature": 0.2,
        "max_tokens": 800
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20)
        if response.status_code == 200:
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            return answer
        else:
            # If 70B fails or rate limited, fallback to llama-3.1-8b-instant
            payload["model"] = "llama-3.1-8b-instant"
            res2 = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
            if res2.status_code == 200:
                return res2.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[Groq RAG Error] {e}")

    # Fallback to local grounded responder
    from app.services.telegram_bot_engine import handle_telegram_incoming_message
    return handle_telegram_incoming_message(user_query, "", user_name)
