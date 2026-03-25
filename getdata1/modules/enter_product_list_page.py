"""Open the Mintel product list page with a valid logged-in session."""

from __future__ import annotations

from typing import Protocol

from playwright.sync_api import BrowserContext, Page, Playwright

from getdata1.modules.expert_to_product_list import go_from_expert_page_to_product_list
from modules.browser_context import launch_main2_browser_context
from modules.login import PASSWORD, USERNAME, do_login, is_logged_in


class WaitBeforeAction(Protocol):
    def __call__(self, page: Page, milliseconds: float | None = None) -> None: ...


def enter_product_list_page(
    playwright: Playwright,
    wait_before_action: WaitBeforeAction,
) -> tuple[BrowserContext, Page]:
    """Launch the browser context, ensure login, and enter the GNPD product list page."""
    context = launch_main2_browser_context(playwright)
    page = context.pages[0] if context.pages else context.new_page()

    if not is_logged_in(page):
        if not USERNAME or not PASSWORD:
            raise ValueError("missing Mintel credentials in keyring for re-login")
        do_login(page)

    wait_before_action(page)
    page.goto("https://clients.mintel.com/content")
    wait_before_action(page)
    product_list_page = go_from_expert_page_to_product_list(page, wait_before_action)
    return context, product_list_page
