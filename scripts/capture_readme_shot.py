import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright
from app.config import Config

def capture_dashboard_screenshot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1050},
            device_scale_factor=2
        )
        page = context.new_page()
        page.goto("http://127.0.0.1:5000", wait_until="networkidle")
        time.sleep(1)

        # Force dismiss startup splash immediately so dashboard is visible
        page.evaluate("""
            const splash = document.getElementById('app-startup-splash');
            if (splash) splash.remove();
        """)
        time.sleep(2)

        # Wait until table container is rendered
        page.wait_for_selector("#hearing-board-list-container", timeout=15000)
        time.sleep(2)

        # Screenshot the full dashboard interface
        assets_dir = Config.BASE_DIR / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = str(assets_dir / "dashboard_preview.png")
        page.screenshot(path=screenshot_path, full_page=False)
        print(f"High-res dashboard screenshot saved to: {screenshot_path}")
        browser.close()

if __name__ == "__main__":
    capture_dashboard_screenshot()
