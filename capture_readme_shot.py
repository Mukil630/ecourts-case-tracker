import time
from playwright.sync_api import sync_playwright

def capture_dashboard_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 920},
            device_scale_factor=2
        )
        page = context.new_page()
        page.goto("http://127.0.0.1:5000", wait_until="domcontentloaded")
        time.sleep(1)

        # Trigger form submission
        page.click("#btn-fetch")
        
        # Wait until the WhatsApp bubble and hearing box are actively rendered
        page.wait_for_selector(".whatsapp-bubble", timeout=20000)
        time.sleep(1)

        # Screenshot the full interface
        screenshot_path = "C:/Users/mukil/ecourts_automation/assets/dashboard_preview.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"High-res dashboard screenshot saved to: {screenshot_path}")
        browser.close()

if __name__ == "__main__":
    capture_dashboard_screenshot()
