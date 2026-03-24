import sys
import time
from pathlib import Path

from playwright.sync_api import Playwright, TimeoutError, sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.expert_download import download_pdf_from_detail_page

STORAGE_STATE = PROJECT_ROOT / "auth.json"
TARGET_URL = "https://clients.mintel.com/content/innovative-product/you-hui-shou-su-liao-ping-zhi-cheng-de-ya-shua-ji-qi-bao-zhuang?fromSearch=%3Ffilters.product-development%3D8%252C2%252C11%26resultPosition%3D107"
ARTICLE_TITLE = "由回收塑料瓶制成的牙刷及其包装"
SHOULD_DOWNLOAD = True
ALLOW_DETAIL_SCROLL = True


def run(playwright: Playwright, target_url: str) -> None:
    # 启动可见浏览器，测试详情页下载模块
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=100,
    )

    if not STORAGE_STATE.exists():
        raise FileNotFoundError(f"missing storage state file: {STORAGE_STATE}")

    context = browser.new_context(storage_state=str(STORAGE_STATE))
    page = context.new_page()

    try:
        # 打开用户提供的详情页链接
        page.goto(target_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")

        # 执行详情页动作流程
        download_pdf_from_detail_page(
            page,
            ARTICLE_TITLE,
            should_download=SHOULD_DOWNLOAD,
            allow_detail_scroll=ALLOW_DETAIL_SCROLL,
        )

        print("expert_download test complete, keeping browser open for 10 seconds...")
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
        raise ValueError("please set TARGET_URL in test/test_expert_download.py before running")
    if not ARTICLE_TITLE:
        raise ValueError("please set ARTICLE_TITLE in test/test_expert_download.py before running")

    with sync_playwright() as playwright:
        run(playwright, TARGET_URL)
