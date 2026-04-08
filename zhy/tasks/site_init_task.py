import sys
from pathlib import Path

from loguru import logger
from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.site_init.initialize_site import initialize_site


DEFAULT_TARGET_HOME_URL = "https://analytics.zhihuiya.com/request_demo?project=search#/template"
DEFAULT_SUCCESS_URL = DEFAULT_TARGET_HOME_URL
DEFAULT_SUCCESS_HEADER_SELECTOR = "#header-wrapper"
DEFAULT_SUCCESS_LOGGED_IN_SELECTOR = ".patsnap-biz-user_center--logged .patsnap-biz-avatar"
DEFAULT_SUCCESS_CONTENT_SELECTOR = "#demo_user-info"
DEFAULT_LOADING_OVERLAY_SELECTOR = "#page-pre-loading-bg"
DEFAULT_GOTO_TIMEOUT_MS = 30000
DEFAULT_LOGIN_TIMEOUT_SECONDS = 600.0
DEFAULT_LOGIN_POLL_INTERVAL_SECONDS = 3.0


def main() -> None:
    logger.info("[site_init_task] prepare to open target page: {}", DEFAULT_TARGET_HOME_URL)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()

        try:
            page = initialize_site(
                context=context,
                target_home_url=DEFAULT_TARGET_HOME_URL,
                success_url=DEFAULT_SUCCESS_URL,
                success_header_selector=DEFAULT_SUCCESS_HEADER_SELECTOR,
                success_logged_in_selector=DEFAULT_SUCCESS_LOGGED_IN_SELECTOR,
                success_content_selector=DEFAULT_SUCCESS_CONTENT_SELECTOR,
                loading_overlay_selector=DEFAULT_LOADING_OVERLAY_SELECTOR,
                goto_timeout_ms=DEFAULT_GOTO_TIMEOUT_MS,
                timeout_seconds=DEFAULT_LOGIN_TIMEOUT_SECONDS,
                poll_interval_seconds=DEFAULT_LOGIN_POLL_INTERVAL_SECONDS,
            )
            logger.info("[site_init_task] site initialization finished, current url={}", page.url)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
