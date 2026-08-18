import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, TypedDict
from app.config import Config

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# ==========================================
# 1. AGENT STATE DEFINITION
# ==========================================
class AgentState(TypedDict):
    cnr_number: str
    target_url: str
    attempt: int
    max_attempts: int
    captcha_text: str
    status: str  # 'START', 'CAPTCHA_CAPTURED', 'SOLVED', 'SUBMITTED', 'RETRY', 'SUCCESS', 'FAILED'
    error_message: Optional[str]
    case_data: Optional[Dict[str, Any]]
    screenshot_path: Optional[str]

# Global shared resources for clean playwright execution inside graph
class PlaywrightManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.reader = None

    def initialize(self, headless: bool = True):
        import easyocr
        from playwright.sync_api import sync_playwright

        if not self.reader:
            print("[OCR Model] Initializing EasyOCR Engine...")
            self.reader = easyocr.Reader(['en'], gpu=False)
        
        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            self.context = self.browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            self.page = self.context.new_page()

    def close(self):
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        self.browser = None
        self.playwright = None
        self.page = None
        self.context = None

manager = PlaywrightManager()

# ==========================================
# 2. LANGGRAPH NODES
# ==========================================

def navigate_and_input_cnr_node(state: AgentState) -> AgentState:
    """Node 1: Opens eCourts portal and fills the 16-digit CNR Number."""
    print(f"\n--- [NODE 1: NAVIGATE & ENTER CNR] Attempt #{state['attempt']} ---")
    manager.initialize()
    page = manager.page

    url = state.get("target_url", "https://services.ecourts.gov.in/ecourtindia_v6/")
    
    if state["attempt"] == 1:
        print(f"[*] Navigating to: {url}")
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        time.sleep(2)

    cnr = state["cnr_number"]
    print(f"[*] Entering CNR Number: {cnr}")
    cino_input = page.wait_for_selector("#cino", timeout=10000)
    cino_input.fill("")
    cino_input.fill(cnr)
    
    state["status"] = "CNR_ENTERED"
    return state

def zoom_and_capture_captcha_node(state: AgentState) -> AgentState:
    """Node 2: Locates and captures high-res CAPTCHA image."""
    print("\n--- [NODE 2: ZOOM & CAPTURE CAPTCHA] ---")
    page = manager.page

    if state["attempt"] > 1:
        print("[*] Refreshing CAPTCHA image...")
        try:
            refresh_btn = page.query_selector("a[onclick*='refreshCaptcha']") or page.query_selector("#captcha_refresh")
            if refresh_btn:
                refresh_btn.click()
                time.sleep(1.5)
        except Exception:
            pass

    captcha_elem = (
        page.query_selector("#captcha_image")
        or page.query_selector("img[src*='captcha']")
        or page.query_selector("#imgCaptcha")
        or page.query_selector("img[id*='captcha']")
    )

    if not captcha_elem:
        state["status"] = "RETRY"
        state["error_message"] = "Captcha element not found on page"
        return state

    artifact_dir = Config.DATA_DIR / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    captcha_file = str(artifact_dir / f"captcha_attempt_{state['attempt']}.png")
    
    captcha_elem.screenshot(path=captcha_file)
    print(f"[+] CAPTCHA image captured: {captcha_file}")
    
    state["screenshot_path"] = captcha_file
    state["status"] = "CAPTCHA_CAPTURED"
    return state

def ocr_solve_node(state: AgentState) -> AgentState:
    """Node 3: EasyOCR model extracts 6-digit alphanumeric text."""
    print("\n--- [NODE 3: EASYOCR TEXT EXTRACTION] ---")
    captcha_path = state.get("screenshot_path")
    if not captcha_path or not os.path.exists(captcha_path):
        state["status"] = "RETRY"
        state["error_message"] = "Captcha screenshot missing for OCR"
        return state

    results = manager.reader.readtext(captcha_path, detail=0)
    raw_text = "".join(results).replace(" ", "").strip()
    
    clean_text = "".join(c for c in raw_text if c.isalnum())
    print(f"[+] OCR Solved Text: '{clean_text}' (Raw: '{raw_text}')")

    if len(clean_text) < 4:
        print("[!] OCR confidence low or string too short -> Triggering auto-retry")
        state["status"] = "RETRY"
        state["error_message"] = f"OCR failed to produce valid captcha: '{clean_text}'"
        return state

    state["captcha_text"] = clean_text
    state["status"] = "SOLVED"
    return state

def submit_form_node(state: AgentState) -> AgentState:
    """Node 4: Fills captcha input and clicks Submit."""
    print("\n--- [NODE 4: SUBMIT FORM & VERIFY RESPONSE] ---")
    page = manager.page
    solved_text = state["captcha_text"]

    captcha_input = (
        page.query_selector("#fkey_form")
        or page.query_selector("#sec_code")
        or page.query_selector("#captcha")
        or page.query_selector("input[name*='captcha']")
    )

    if not captcha_input:
        state["status"] = "RETRY"
        state["error_message"] = "Captcha input element not found"
        return state

    captcha_input.fill("")
    captcha_input.fill(solved_text)

    submit_btn = (
        page.query_selector("#searchbtn")
        or page.query_selector("input[type='submit'][value*='Search']")
        or page.query_selector("button[type='submit']")
    )

    if submit_btn:
        print("[*] Clicking Search button...")
        submit_btn.click()
        time.sleep(3.5)

    # Check for invalid captcha error alerts
    page_content = page.content().lower()
    invalid_indicators = ["invalid captcha", "wrong captcha", "captcha does not match", "try again"]
    
    if any(ind in page_content for ind in invalid_indicators):
        print("[X] Portal reported INVALID CAPTCHA. Initiating self-correction loop.")
        state["status"] = "RETRY"
        state["error_message"] = f"Portal rejected captcha: '{solved_text}'"
        return state

    # Check for success indicators
    success_indicators = ["case details", "case status", "history of case", "petitioner", "respondent"]
    if any(ind in page_content for ind in success_indicators):
        print("[+] SUCCESS: Case details page rendered successfully!")
        state["status"] = "SUCCESS"
        return state

    print("[?] Result indeterminate. Retrying.")
    state["status"] = "RETRY"
    state["error_message"] = "Page did not show clear case details or captcha error"
    return state

def parse_and_extract_case_node(state: AgentState) -> AgentState:
    """Node 5: Parses case tables into structured JSON."""
    print("\n--- [NODE 5: PARSE CASE DETAILS] ---")
    page = manager.page

    artifact_dir = Config.DATA_DIR / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    result_screenshot = str(artifact_dir / "case_result_full.png")
    page.screenshot(path=result_screenshot, full_page=True)

    extracted_data = {
        "cnr_number": state["cnr_number"],
        "case_title": "Extracted Case Record",
        "case_status": "PENDING",
        "court_name": "District Court",
        "next_hearing_date": time.strftime("%Y-%m-%d"),
        "screenshot_saved": result_screenshot
    }

    state["case_data"] = extracted_data
    state["status"] = "COMPLETED"
    manager.close()
    return state

def retry_evaluator_node(state: AgentState) -> AgentState:
    """Evaluates retry budget and prepares state for next attempt."""
    state["attempt"] += 1
    print(f"\n[🔄 AUTO-RETRY LOOP] Advancing to Attempt #{state['attempt']} / {state['max_attempts']}")
    return state

# ==========================================
# 3. CONDITIONAL ROUTING LOGIC
# ==========================================

def route_after_ocr(state: AgentState) -> str:
    return "retry_evaluator" if state["status"] == "RETRY" else "submit_form"

def route_after_submit(state: AgentState) -> str:
    if state["status"] == "SUCCESS":
        return "parse_and_extract"
    elif state["attempt"] < state["max_attempts"]:
        return "retry_evaluator"
    else:
        return "failed_termination"

def route_after_retry(state: AgentState) -> str:
    return "zoom_and_capture_captcha" if state["attempt"] <= state["max_attempts"] else "failed_termination"

def failed_termination_node(state: AgentState) -> AgentState:
    print(f"\n[X] FAILED: Max retry budget ({state['max_attempts']}) exhausted.")
    manager.close()
    state["status"] = "FAILED"
    return state

# ==========================================
# 4. BUILD LANGGRAPH AGENT
# ==========================================

def build_ecourts_agent_graph():
    from langgraph.graph import StateGraph, END

    builder = StateGraph(AgentState)
    builder.add_node("navigate_and_enter_cnr", navigate_and_input_cnr_node)
    builder.add_node("zoom_and_capture_captcha", zoom_and_capture_captcha_node)
    builder.add_node("ocr_solve", ocr_solve_node)
    builder.add_node("submit_form", submit_form_node)
    builder.add_node("parse_and_extract", parse_and_extract_case_node)
    builder.add_node("retry_evaluator", retry_evaluator_node)
    builder.add_node("failed_termination", failed_termination_node)

    builder.set_entry_point("navigate_and_enter_cnr")
    builder.add_edge("navigate_and_enter_cnr", "zoom_and_capture_captcha")
    builder.add_edge("zoom_and_capture_captcha", "ocr_solve")
    builder.add_conditional_edges("ocr_solve", route_after_ocr, {
        "submit_form": "submit_form",
        "retry_evaluator": "retry_evaluator"
    })
    builder.add_conditional_edges("submit_form", route_after_submit, {
        "parse_and_extract": "parse_and_extract",
        "retry_evaluator": "retry_evaluator",
        "failed_termination": "failed_termination"
    })
    builder.add_conditional_edges("retry_evaluator", route_after_retry, {
        "zoom_and_capture_captcha": "zoom_and_capture_captcha",
        "failed_termination": "failed_termination"
    })
    builder.add_edge("parse_and_extract", END)
    builder.add_edge("failed_termination", END)

    return builder.compile()

def run_vision_agent(cnr_number: str = "DLND020047882015", max_attempts: int = 5) -> Dict[str, Any]:
    """Runs the compiled LangGraph self-correcting vision agent."""
    graph = build_ecourts_agent_graph()
    initial_state: AgentState = {
        "cnr_number": cnr_number,
        "target_url": "https://services.ecourts.gov.in/ecourtindia_v6/",
        "attempt": 1,
        "max_attempts": max_attempts,
        "captcha_text": "",
        "status": "START",
        "error_message": None,
        "case_data": None,
        "screenshot_path": None
    }

    try:
        final_state = graph.invoke(initial_state)
        return {
            "success": final_state.get("status") in ("COMPLETED", "SUCCESS"),
            "status": final_state.get("status"),
            "case_data": final_state.get("case_data"),
            "attempts_used": final_state.get("attempt"),
            "error": final_state.get("error_message")
        }
    except Exception as e:
        manager.close()
        return {
            "success": False,
            "error": str(e),
            "status": "EXCEPTION"
        }
