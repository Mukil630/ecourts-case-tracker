import os
import time
import easyocr
from playwright.sync_api import sync_playwright

def test_ecourts_captcha():
    print("[1/5] Initializing EasyOCR reader (English)...")
    reader = easyocr.Reader(['en'], gpu=False)

    print("[2/5] Launching browser...")
    with sync_playwright() as p:
        # Launch browser in visible mode
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("[3/5] Navigating to eCourts CNR search portal...")
        url = "https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/index"
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(3)
        except Exception as e:
            print(f"Opening alternative eCourts URL due to: {e}")
            page.goto("https://services.ecourts.gov.in/ecourtindia_v6/", timeout=30000)
            time.sleep(3)

        print("[4/5] Locating CAPTCHA element...")
        # Check for common captcha image selectors on eCourts
        captcha_img = (
            page.query_selector("#captcha_image")
            or page.query_selector("img[src*='captcha']")
            or page.query_selector("#imgCaptcha")
            or page.query_selector("img[id*='captcha']")
        )

        if not captcha_img:
            page.screenshot(path="C:/Users/mukil/ecourts_automation/page_view.png")
            print("Could not find standard captcha selector. Saved page_view.png for inspection.")
            browser.close()
            return

        # Screenshot specifically the CAPTCHA element
        captcha_path = "C:/Users/mukil/ecourts_automation/captcha.png"
        captcha_img.screenshot(path=captcha_path)
        print(f"CAPTCHA image saved to: {captcha_path}")

        # OCR to read the text
        ocr_result = reader.readtext(captcha_path, detail=0)
        solved_text = "".join(ocr_result).replace(" ", "").strip()
        print(f"\n==========================================")
        print(f"[SOLVED CAPTCHA] Text: '{solved_text}'")
        print(f"==========================================\n")

        # Find captcha input field and type it in
        captcha_input = (
            page.query_selector("#sec_code")
            or page.query_selector("#captcha")
            or page.query_selector("input[name*='captcha']")
            or page.query_selector("#txtCaptcha")
            or page.query_selector("input[id*='captcha']")
        )
        if captcha_input:
            captcha_input.fill(solved_text)
            print("Successfully typed solved CAPTCHA into the input field!")
        else:
            print("Captcha input box selector not matched directly.")

        # Take a final verification screenshot
        page.screenshot(path="C:/Users/mukil/ecourts_automation/solved_result.png")
        print("Verification screenshot saved to: C:/Users/mukil/ecourts_automation/solved_result.png")

        print("Keeping browser open for 5 seconds to inspect...")
        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    test_ecourts_captcha()
