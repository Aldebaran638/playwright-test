import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://top.tianyancha.com/")
    page.get_by_role("searchbox", name="请输入公司名称、人名、品牌名称等关键词").click()
    page.get_by_role("searchbox", name="请输入公司名称、人名、品牌名称等关键词").fill("小米通讯技术有限公司")
    page.get_by_text("天眼一下").first.click()
    with page.expect_popup() as page1_info:
        page.get_by_role("link", name="小米通讯技术有限公司", exact=True).click()
    page1 = page1_info.value

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
