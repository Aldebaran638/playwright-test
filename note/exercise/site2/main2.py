from playwright.sync_api import sync_playwright
from pathlib import Path

BASE_DIR = Path(__file__).parent
HAR_PATH = BASE_DIR / "site.har"

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()

    context.route_from_har(str(HAR_PATH), not_found="abort")

    page = context.new_page()
    page.goto("https://www.tianyancha.com/")

    print(page.title())

    browser.close()