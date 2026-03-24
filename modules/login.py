import random
import time

import keyring
from playwright.sync_api import Page

# 从系统凭据管理器读取用户名和密码
USERNAME = keyring.get_password("mintel", "username")
PASSWORD = keyring.get_password("mintel", "password")

# 登录页地址和门户主页地址
LOGIN_URL = "https://portal.mintel.com/portal/login?next=https%3A%2F%2Foauth.mintel.com%2F"
PORTAL_HOME = "https://portal.mintel.com/"


def human_wait(min_sec=3, max_sec=6):
    # 随机等待，避免操作节奏过于固定
    t = random.uniform(min_sec, max_sec)
    print(f"wait {t:.2f}s")
    time.sleep(t)


def human_type(locator, text, min_delay=80, max_delay=180):
    # 先聚焦输入框并清空旧内容
    locator.click()
    human_wait(3, 6)
    locator.clear()
    # 逐字符输入，模拟人工输入节奏
    for ch in text:
        locator.type(ch, delay=random.randint(min_delay, max_delay))


def is_logged_in(page: Page) -> bool:
    try:
        # 访问门户主页，检查是否被重定向到登录页
        page.goto(PORTAL_HOME, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        human_wait(3, 6)

        # 如果 URL 中包含 login 关键词，说明当前未登录
        current_url = page.url.lower()
        if "login" in current_url or "portal/login" in current_url:
            return False

        return True
    except Exception:
        # 判断过程出错时，按未登录处理
        return False


def do_login(page: Page):
    # 打开登录页并等待页面稳定
    print("start login flow...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    human_wait()

    # 定位邮箱、密码输入框和按钮
    email_box = page.get_by_role("textbox", name="Email Address")
    next_btn = page.get_by_role("button", name="Next")
    password_box = page.get_by_role("textbox", name="Password")
    login_btn = page.get_by_role("button", name="Login")

    # 输入邮箱并进入下一步
    email_box.wait_for(timeout=15000)
    human_type(email_box, USERNAME)
    human_wait()

    next_btn.click()
    human_wait()

    # 输入密码并提交登录
    password_box.wait_for(timeout=15000)
    human_type(password_box, PASSWORD)
    human_wait()

    login_btn.click()
    human_wait(3, 6)

    # 等待登录后的页面跳转完成
    page.wait_for_load_state("networkidle")
    human_wait(3, 6)

    # 如果提交后仍停留在登录页，则视为登录失败
    if "login" in page.url.lower():
        raise RuntimeError(f"still on login page after submit, current URL: {page.url}")

    # 走到这里说明登录流程执行成功
    print("login success")
