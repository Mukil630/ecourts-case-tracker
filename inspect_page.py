import time
from playwright.sync_api import sync_playwright

def inspect_cnr_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://services.ecourts.gov.in/ecourtindia_v6/", timeout=45000, wait_until="domcontentloaded")
        time.sleep(3)

        # Print all inputs and images related to CNR and Captcha
        print("Page Title:", page.title())

        # Inspect inputs
        inputs = page.query_selector_all("input")
        print("\n--- Inputs found ---")
        for inp in inputs:
            name = inp.get_attribute("name") or ""
            inp_id = inp.get_attribute("id") or ""
            placeholder = inp.get_attribute("placeholder") or ""
            inp_type = inp.get_attribute("type") or ""
            print(f"Type: {inp_type} | ID: {inp_id} | Name: {name} | Placeholder: {placeholder}")

        # Inspect images
        images = page.query_selector_all("img")
        print("\n--- Images found ---")
        for img in images:
            img_id = img.get_attribute("id") or ""
            src = img.get_attribute("src") or ""
            if "captcha" in src.lower() or "captcha" in img_id.lower():
                print(f"Captcha Image -> ID: {img_id} | Src: {src}")

        # Inspect buttons
        buttons = page.query_selector_all("button, input[type='button'], input[type='submit']")
        print("\n--- Buttons found ---")
        for btn in buttons:
            btn_id = btn.get_attribute("id") or ""
            text = btn.inner_text() if hasattr(btn, 'inner_text') else ""
            val = btn.get_attribute("value") or ""
            onclick = btn.get_attribute("onclick") or ""
            print(f"Button -> ID: {btn_id} | Text: {text} | Value: {val} | OnClick: {onclick}")

        page.screenshot(path="C:/Users/mukil/ecourts_automation/cnr_home_screen.png")
        print("\nScreenshot saved to cnr_home_screen.png")
        browser.close()

if __name__ == "__main__":
    inspect_cnr_page()
