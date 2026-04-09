from playwright.sync_api import sync_playwright
from pathlib import Path

BASE_DIR = Path(__file__).parent
HAR_PATH = BASE_DIR / "site.har"

TARGET_URL = "https://www.tianyancha.com/"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        context = browser.new_context(record_har_path=str(HAR_PATH))
        page = context.new_page()

        page.goto(TARGET_URL)

        input("完成后回车...")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()