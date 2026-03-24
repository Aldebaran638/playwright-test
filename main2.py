import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.get_by_role("checkbox", name="专利").click()
    page.get_by_role("checkbox", name="成分").click()
    page.get_by_role("checkbox", name="产品概念").click()
    with page.expect_popup() as page1_info:
        page.get_by_text("美容产品创新亮点，2026年3月Regional2026年").click()
    page1 = page1_info.value
    page1.get_by_role("button", name="下载").click()
    with page1.expect_download() as download_info:
        page1.get_by_role("button", name="下载PDF文件").click()
    download = download_info.value

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
