import sys
import time
from pathlib import Path

from playwright.sync_api import Playwright, TimeoutError, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.login import PASSWORD, USERNAME, do_login

STORAGE_STATE = PROJECT_ROOT / "auth.json"


def run(playwright: Playwright) -> None:
    # 启动可见浏览器，测试登录模块
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=100,
    )
    context = browser.new_context()
    page = context.new_page()

    try:
        # 执行登录流程
        do_login(page)

        # 将登录态保存到项目根目录
        context.storage_state(path=str(STORAGE_STATE))
        print(f"saved state file: {STORAGE_STATE}")

        # 保留浏览器一段时间，方便人工确认结果
        print("login test complete, keeping browser open for 10 seconds...")
        time.sleep(10)

    except TimeoutError as e:
        print(f"page timeout: {e}")
    except Exception as e:
        print(f"execution failed: {e}")
    finally:
        context.close()
        browser.close()


if __name__ == "__main__":
    # 启动前先确认 keyring 中已经保存账号密码
    if not USERNAME or not PASSWORD:
        raise ValueError("please save mintel username/password in keyring first")

    with sync_playwright() as playwright:
        run(playwright)
