import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://portal.mintel.com/portal/login?next=https%3A%2F%2Foauth.mintel.com%2F")
    page.get_by_role("button", name="Login").click()
    page.goto("https://portal.mintel.com/")
    page.get_by_role("button", name="探索 Mintel 订阅").click()
    page.goto("https://clients.mintel.com/home")
    page.get_by_label("洞察").get_by_role("link", name="专家分析").click()
    page.goto("https://clients.mintel.com/content")
    page.get_by_role("button", name="Open dropdown").click()
    page.get_by_role("link", name="您的GNPD中心 从这里开启您的GNPD").click()
    page.goto("https://clients.mintel.com/gnpd-hub")
    with page.expect_popup() as page1_info:
        page.get_by_role("link", name="View more products in GNPD").click()
    page1 = page1_info.value
    page1.get_by_role("textbox", name="精确搜索").click()
    page1.get_by_role("textbox", name="精确搜索").click()
    page1.get_by_role("textbox", name="精确搜索").fill("Le Lipstick")
    page1.get_by_role("button", name="创建搜索").click()
    page1.locator("#item_13830642 input[name=\"Product_selection\"]").check()
    page1.locator("#item_13680716 input[name=\"Product_selection\"]").check()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
