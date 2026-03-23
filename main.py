import random
import time
from pathlib import Path

import keyring
from playwright.sync_api import Playwright, sync_playwright, TimeoutError

USERNAME = keyring.get_password("mintel", "username")
PASSWORD = keyring.get_password("mintel", "password")

LOGIN_URL = "https://portal.mintel.com/portal/login?next=https%3A%2F%2Foauth.mintel.com%2F"
PORTAL_HOME = "https://portal.mintel.com/"
CLIENTS_HOME = "https://clients.mintel.com/home"
STORAGE_STATE = "auth.json"


def human_wait(min_sec=5, max_sec=9):
    t = random.uniform(min_sec, max_sec)
    print(f"等待 {t:.2f} 秒...")
    time.sleep(t)


def human_type(locator, text, min_delay=80, max_delay=180):
    locator.click()
    human_wait(5, 6)
    locator.clear()
    for ch in text:
        locator.type(ch, delay=random.randint(min_delay, max_delay))


def is_logged_in(page) -> bool:
    try:
        page.goto(PORTAL_HOME, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        human_wait(5, 7)

        current_url = page.url.lower()
        if "login" in current_url or "portal/login" in current_url:
            return False

        return True
    except Exception:
        return False


def do_login(page):
    print("开始执行登录流程...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    human_wait()

    email_box = page.get_by_role("textbox", name="Email Address")
    next_btn = page.get_by_role("button", name="Next")
    password_box = page.get_by_role("textbox", name="Password")
    login_btn = page.get_by_role("button", name="Login")

    email_box.wait_for(timeout=15000)
    human_type(email_box, USERNAME)
    human_wait()

    next_btn.click()
    human_wait()

    password_box.wait_for(timeout=15000)
    human_type(password_box, PASSWORD)
    human_wait()

    login_btn.click()
    human_wait(8, 12)

    page.wait_for_load_state("networkidle")
    human_wait(5, 8)

    if "login" in page.url.lower():
        raise RuntimeError(f"登录后仍停留在登录页，当前 URL: {page.url}")

    print("登录成功")


def open_target(page):
    print("进入目标页面...")
    page.goto(PORTAL_HOME, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    human_wait()

    try:
        explore_btn = page.get_by_role("button", name="探索 Mintel 订阅")
        if explore_btn.is_visible(timeout=5000):
            explore_btn.click()
            human_wait()
    except Exception:
        pass

    page.goto(CLIENTS_HOME, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    human_wait()

    try:
        page.get_by_label("洞察").get_by_role("link", name="专家分析").click(timeout=10000)
        human_wait()
    except Exception:
        print("没有点击到“专家分析”，但已进入 clients 首页。")


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=100,
    )

    state_file = Path(STORAGE_STATE)

    if state_file.exists():
        print(f"发现已有登录态文件: {STORAGE_STATE}")
        context = browser.new_context(storage_state=STORAGE_STATE)
    else:
        print("未发现登录态文件，创建全新会话")
        context = browser.new_context()

    page = context.new_page()

    try:
        if not is_logged_in(page):
            print("当前未登录或登录态已失效，准备重新登录...")
            do_login(page)
            context.storage_state(path=STORAGE_STATE)
            print(f"登录态已保存到 {STORAGE_STATE}")
        else:
            print("检测到已登录，直接复用登录态")

        open_target(page)
        html = page.content()

        with open("test.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("已保存为 test.html")
        print("流程完成，浏览器保留 10 秒供观察...")
        time.sleep(10)

    except TimeoutError as e:
        print(f"页面等待超时: {e}")
    except Exception as e:
        print(f"执行失败: {e}")
    finally:
        context.close()
        browser.close()


if __name__ == "__main__":
    if not USERNAME or not PASSWORD:
        raise ValueError("请先用 keyring 保存 mintel 的 username 和 password")

    with sync_playwright() as playwright:
        run(playwright)