import sys
import time
from pathlib import Path

from playwright.sync_api import Playwright, TimeoutError, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.expert_analysis import open_expert_analysis_from_home

STORAGE_STATE = PROJECT_ROOT / "auth.json"


def run(playwright: Playwright) -> None:
    # 启动可见浏览器，测试“进入专家分析页”模块
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=100,
    )

    if not STORAGE_STATE.exists():
        raise FileNotFoundError(f"missing storage state file: {STORAGE_STATE}")

    context = browser.new_context(storage_state=str(STORAGE_STATE))
    page = context.new_page()

    try:
        # 执行“从主页进入专家分析页”流程
        open_expert_analysis_from_home(page)

        print("expert_analysis test complete, keeping browser open for 10 seconds...")
        time.sleep(10)

    except TimeoutError as e:
        print(f"page timeout: {e}")
    except Exception as e:
        print(f"execution failed: {e}")
    finally:
        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
