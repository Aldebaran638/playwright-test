import sys
import time
from pathlib import Path

from playwright.sync_api import Playwright, TimeoutError, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.expert_tags import apply_expert_analysis_tag_filters

STORAGE_STATE = PROJECT_ROOT / "auth.json"
TARGET_URL = ""


def run(playwright: Playwright, target_url: str) -> None:
    # 启动可见浏览器，测试标签筛选模块
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=100,
    )

    if not STORAGE_STATE.exists():
        raise FileNotFoundError(f"missing storage state file: {STORAGE_STATE}")

    context = browser.new_context(storage_state=str(STORAGE_STATE))
    page = context.new_page()

    try:
        # 打开用户提供的专家分析页面链接
        page.goto(target_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")

        # 执行标签筛选逻辑
        apply_expert_analysis_tag_filters(page)

        print("expert_tags test complete, keeping browser open for 10 seconds...")
        time.sleep(10)

    except TimeoutError as e:
        print(f"page timeout: {e}")
    except Exception as e:
        print(f"execution failed: {e}")
    finally:
        context.close()
        browser.close()


if __name__ == "__main__":
    if not TARGET_URL:
        raise ValueError("please set TARGET_URL in test/test_expert_tags.py before running")

    with sync_playwright() as playwright:
        run(playwright, TARGET_URL)
