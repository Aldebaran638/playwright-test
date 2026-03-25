"""Playwright automation that uses the main2 browser environment."""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.sync_api import Playwright, sync_playwright

if __package__ in {None, ""}:
    import sys

    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from playwright_detection_demo.browser_env import launch_main2_browser_context
else:
    from .browser_env import launch_main2_browser_context

LOGGER = logging.getLogger("playwright_detection_demo.automation")
DOWNLOAD_DIR = Path("downloads") / "playwright_detection_demo"


def run_automation(playwright: Playwright, base_url: str) -> dict[str, str]:
    """Visit the demo site, open the detail page, and download the file."""

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    context = launch_main2_browser_context(playwright)
    page = context.new_page()

    try:
        LOGGER.info("opening demo home page: %s", base_url)
        page.goto(base_url, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)

        LOGGER.info("clicking detail button")
        page.locator("#go-detail-button").click()
        page.wait_for_url(f"{base_url.rstrip('/')}/detail")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)

        LOGGER.info("clicking download button")
        with page.expect_download() as download_info:
            page.locator("#download-button").click()

        download = download_info.value
        target_path = DOWNLOAD_DIR / download.suggested_filename
        download.save_as(str(target_path))
        LOGGER.info("download saved to: %s", target_path)

        page.wait_for_timeout(1000)
        return {
            "download_path": str(target_path.resolve()),
            "current_url": page.url,
            "title": page.title(),
        }
    finally:
        page.close()
        context.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    with sync_playwright() as playwright:
        result = run_automation(playwright, "http://127.0.0.1:8008/")
    LOGGER.info("automation result: %s", result)


if __name__ == "__main__":
    main()
