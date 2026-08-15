import os
import sys
import time
import json
from typing import Dict, Any, Optional, TypedDict

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import easyocr
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from langgraph.graph import StateGraph, END

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
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.reader = None

    def initialize(self):
        if not self.reader:
            print("[OCR Model] Initializing EasyOCR Engine...")
            self.reader = easyocr.Reader(['en'], gpu=False)
        
        if not self.playwright:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=False)
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
    
    # Navigate if on initial attempt
    if state["attempt"] == 1:
        print(f"[*] Navigating to: {url}")
        page.goto(url, timeout=45000, wait_until="domcontentloaded")
        time.sleep(2)

    # Enter CNR Number into #cino
    cnr = state["cnr_number"]
    print(f"[*] Entering CNR Number: {cnr}")
    cino_input = page.wait_for_selector("#cino", timeout=10000)
    cino_input.fill("")
    cino_input.fill(cnr)
    
    state["status"] = "CNR_ENTERED"
    return state


def zoom_and_capture_captcha_node(state: AgentState) -> AgentState:
    """Node 2: Locates and zooms/crops high-res CAPTCHA image."""
    print("\n--- [NODE 2: ZOOM & CAPTURE CAPTCHA] ---")
    page = manager.page

    # Refresh captcha if this is a retry loop
    if state["attempt"] > 1:
        print("[*] Refreshing CAPTCHA image...")
        try:
            # Click refresh button or click on image to reload
            refresh_btn = page.query_selector("a[onclick*='refresh'], button[onclick*='refresh'], #captcha_image")
            if refresh_btn:
                refresh_btn.click()
                time.sleep(2)
        except Exception as e:
            print(f"Warning during refresh: {e}")

    captcha_img = page.wait_for_selector("#captcha_image", timeout=10000)
    
    # Save cropped captcha screenshot
    captcha_file = f"C:/Users/mukil/ecourts_automation/captcha_attempt_{state['attempt']}.png"
    captcha_img.screenshot(path=captcha_file)
    print(f"[*] CAPTCHA cropped and saved: {captcha_file}")

    state["screenshot_path"] = captcha_file
    state["status"] = "CAPTCHA_CAPTURED"
    return state


def vision_solve_node(state: AgentState) -> AgentState:
    """Node 3: Uses Vision / OCR Engine to decipher the CAPTCHA."""
    print("\n--- [NODE 3: VISION OCR SOLVER] ---")
    captcha_path = state["screenshot_path"]
    
    # Perform OCR
    results = manager.reader.readtext(captcha_path, detail=0)
    solved = "".join(results).replace(" ", "").strip().lower()
    
    # Basic cleanup (alphanumeric only)
    solved = "".join(c for c in solved if c.isalnum())
    print(f"[*] Decoded CAPTCHA: '{solved}'")

    state["captcha_text"] = solved
    state["status"] = "SOLVED"
    return state


def fill_and_submit_node(state: AgentState) -> AgentState:
    """Node 4: Fills the solved CAPTCHA into the form and clicks Search."""
    print("\n--- [NODE 4: FILL & SUBMIT FORM] ---")
    page = manager.page

    # Fill captcha
    captcha_input = page.wait_for_selector("#fcaptcha_code", timeout=10000)
    captcha_input.fill("")
    captcha_input.fill(state["captcha_text"])
    time.sleep(0.5)

    # Click Search button
    print("[*] Clicking 'Search' button (#searchbtn)...")
    search_btn = page.wait_for_selector("#searchbtn", timeout=10000)
    search_btn.click()
    
    # Wait for server response / modal popup / table update
    time.sleep(3)
    state["status"] = "SUBMITTED"
    return state


def verify_and_evaluate_node(state: AgentState) -> AgentState:
    """Node 5: Evaluates response for 'Invalid Captcha' vs 'Success'."""
    print("\n--- [NODE 5: VERIFICATION & EVALUATION] ---")
    page = manager.page

    # Check for error modal / alert popup
    error_modal = page.query_selector("#validateError, .modal.show, div[id*='error']")
    modal_text = ""
    if error_modal and error_modal.is_visible():
        modal_text = error_modal.inner_text().strip().lower()
        print(f"[*] Detected Alert Modal: '{modal_text}'")

    # Close modal if open
    close_btn = page.query_selector("button[onclick*='closeModel'], .modal-footer button, .btn-close")
    if close_btn and close_btn.is_visible():
        close_btn.click()
        time.sleep(1)

    # Check conditions
    if "captcha" in modal_text or "invalid" in modal_text or "match" in modal_text:
        print(f"[!] Captcha Mismatch detected on Attempt #{state['attempt']}. Triggering loop retry...")
        state["status"] = "RETRY"
        state["attempt"] += 1
        state["error_message"] = "Invalid CAPTCHA - retrying"
        return state

    # Check if case details or history table rendered
    case_table = page.query_selector("#dispTable, #history_cnr, .case_details_table, table")
    page_text = page.inner_text("body").lower()

    if "record not found" in page_text or "invalid cnr" in page_text:
        print("[!] Result: CNR Number not found or Invalid.")
        state["status"] = "INVALID_CNR"
        state["error_message"] = "CNR Number not found in court records"
        return state

    # If search was accepted and details are loading/present
    print("[+] SUCCESS! Case query accepted.")
    state["status"] = "SUCCESS"
    return state


def extract_case_data_node(state: AgentState) -> AgentState:
    """Node 6: Extracts all case data (Hearing dates, status, parties)."""
    print("\n--- [NODE 6: EXTRACT CASE DATA] ---")
    page = manager.page
    time.sleep(2)

    # Take full result screenshot
    result_screenshot = "C:/Users/mukil/ecourts_automation/case_result_full.png"
    page.screenshot(path=result_screenshot, full_page=True)
    print(f"[*] Full case details screenshot saved: {result_screenshot}")

    # Extract all text and tables
    extracted_info = {
        "cnr_number": state["cnr_number"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "raw_text_summary": page.inner_text("body")[:1000]
    }

    # Save to JSON
    json_path = "C:/Users/mukil/ecourts_automation/case_details.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(extracted_info, f, indent=4)
    print(f"[*] Case details saved to JSON: {json_path}")

    state["case_data"] = extracted_info
    state["status"] = "COMPLETED"
    return state


def handle_failure_node(state: AgentState) -> AgentState:
    """Node 7: Handles max retry limit or fatal error."""
    print(f"\n--- [NODE 7: FAILURE HANDLER] Reason: {state.get('error_message')} ---")
    state["status"] = "TERMINATED"
    return state

# ==========================================
# 3. LOOP ROUTER (CONDITIONAL EDGE)
# ==========================================
def loop_router(state: AgentState) -> str:
    """Determines next step based on verification state (Loop Engineering)."""
    current_status = state["status"]
    attempt = state["attempt"]
    max_attempts = state["max_attempts"]

    if current_status == "SUCCESS":
        return "extract_case_data_node"
    
    if current_status == "RETRY":
        if attempt <= max_attempts:
            print(f"--> [LOOP ROUTING]: Looping back to Zoom & Capture (Attempt {attempt}/{max_attempts})")
            return "zoom_and_capture_captcha_node"
        else:
            print("--> [LOOP ROUTING]: Max retries reached. Routing to Failure Handler.")
            state["error_message"] = "Max CAPTCHA retries exceeded"
            return "handle_failure_node"

    if current_status == "INVALID_CNR":
        return "handle_failure_node"

    return "handle_failure_node"

# ==========================================
# 4. GRAPH ASSEMBLY
# ==========================================
def build_ecourts_graph():
    builder = StateGraph(AgentState)

    # Register Nodes
    builder.add_node("navigate_and_input_cnr_node", navigate_and_input_cnr_node)
    builder.add_node("zoom_and_capture_captcha_node", zoom_and_capture_captcha_node)
    builder.add_node("vision_solve_node", vision_solve_node)
    builder.add_node("fill_and_submit_node", fill_and_submit_node)
    builder.add_node("verify_and_evaluate_node", verify_and_evaluate_node)
    builder.add_node("extract_case_data_node", extract_case_data_node)
    builder.add_node("handle_failure_node", handle_failure_node)

    # Set Entry Point
    builder.set_entry_point("navigate_and_input_cnr_node")

    # Connect Edges
    builder.add_edge("navigate_and_input_cnr_node", "zoom_and_capture_captcha_node")
    builder.add_edge("zoom_and_capture_captcha_node", "vision_solve_node")
    builder.add_edge("vision_solve_node", "fill_and_submit_node")
    builder.add_edge("fill_and_submit_node", "verify_and_evaluate_node")

    # Conditional Self-Correcting Loop
    builder.add_conditional_edges(
        "verify_and_evaluate_node",
        loop_router,
        {
            "zoom_and_capture_captcha_node": "zoom_and_capture_captcha_node",
            "extract_case_data_node": "extract_case_data_node",
            "handle_failure_node": "handle_failure_node"
        }
    )

    builder.add_edge("extract_case_data_node", END)
    builder.add_edge("handle_failure_node", END)

    return builder.compile()

# ==========================================
# 5. RUNNER
# ==========================================
def run_agent(cnr_number: str = "MHAU019999992015"):
    print("============================================================")
    print(f"[START] ECOURTS AUTONOMOUS AI AGENT")
    print(f"[TARGET CNR] {cnr_number}")
    print("============================================================")

    initial_state: AgentState = {
        "cnr_number": cnr_number,
        "target_url": "https://services.ecourts.gov.in/ecourtindia_v6/",
        "attempt": 1,
        "max_attempts": 5,
        "captcha_text": "",
        "status": "START",
        "error_message": None,
        "case_data": None,
        "screenshot_path": None
    }

    graph = build_ecourts_graph()
    try:
        final_state = graph.invoke(initial_state)
        print("\n============================================================")
        print(f"[FINISHED] WORKFLOW STATUS: {final_state['status']}")
        print("============================================================")
        return final_state
    finally:
        time.sleep(3)
        manager.close()

if __name__ == "__main__":
    test_cnr = sys.argv[1] if len(sys.argv) > 1 else "MHAU019999992015"
    run_agent(test_cnr)
