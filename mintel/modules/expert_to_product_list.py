"""Navigation helpers for moving from the expert page to the product list page."""

from __future__ import annotations

from typing import Protocol

from playwright.sync_api import Page

from getdata1.modules.retry import run_with_timeout_retry


class WaitBeforeAction(Protocol):
    def __call__(self, page: Page, milliseconds: float | None = None) -> None: ...


def go_from_expert_page_to_product_list(
    page: Page,
    wait_before_action: WaitBeforeAction,
) -> Page:
    """Navigate from the expert content page to the GNPD product list popup page."""
    run_with_timeout_retry(
        "点击地区标签",
        page,
        wait_before_action,
        lambda: page.get_by_role("tab", name="地区", exact=True).click(),
    )
    wait_before_action(page)
    run_with_timeout_retry(
        "点击北美标签",
        page,
        wait_before_action,
        lambda: page.get_by_role("tab", name="北美").click(),
    )
    wait_before_action(page)
    run_with_timeout_retry(
        "勾选北美(all)",
        page,
        wait_before_action,
        lambda: page.get_by_role("checkbox", name="北美\xa0(all)").click(),
    )
    wait_before_action(page)

    run_with_timeout_retry(
        "点击品类标签",
        page,
        wait_before_action,
        lambda: page.get_by_role("tab", name="品类").click(),
    )
    wait_before_action(page)
    run_with_timeout_retry(
        "点击美容与个人护理标签",
        page,
        wait_before_action,
        lambda: page.get_by_role("tab", name="美容与个人护理").click(),
    )
    wait_before_action(page)
    run_with_timeout_retry(
        "勾选头发护理",
        page,
        wait_before_action,
        lambda: page.get_by_role("checkbox", name="头发护理").click(),
    )
    wait_before_action(page)
    run_with_timeout_retry(
        "勾选面部护肤品",
        page,
        wait_before_action,
        lambda: page.get_by_role("checkbox", name="面部护肤品").click(),
    )
    wait_before_action(page)

    run_with_timeout_retry(
        "打开 GNPD 下拉菜单",
        page,
        wait_before_action,
        lambda: page.get_by_role("button", name="Open dropdown").click(),
    )
    wait_before_action(page)
    run_with_timeout_retry(
        "点击进入 GNPD 中心链接",
        page,
        wait_before_action,
        lambda: page.get_by_role("link", name="您的GNPD中心 从这里开启您的GNPD").click(),
    )
    wait_before_action(page)
    run_with_timeout_retry(
        "跳转到 GNPD Hub",
        page,
        wait_before_action,
        lambda: page.goto("https://clients.mintel.com/gnpd-hub"),
    )
    wait_before_action(page)

    run_with_timeout_retry(
        "打开品类下拉框",
        page,
        wait_before_action,
        lambda: page.locator("#category-select").get_by_role("img").click(),
    )
    wait_before_action(page)
    run_with_timeout_retry(
        "选择面部/颈部护理",
        page,
        wait_before_action,
        lambda: page.get_by_role("option", name="面部/颈部护理").click(),
    )
    wait_before_action(page)
    run_with_timeout_retry(
        "点击应用筛选项",
        page,
        wait_before_action,
        lambda: page.get_by_role("button", name="应用筛选项").click(),
    )
    wait_before_action(page)

    def open_product_list_popup() -> Page:
        with page.expect_popup() as page1_info:
            page.get_by_role("link", name="在GNPD中查看更多产品").click()
        return page1_info.value

    page1 = run_with_timeout_retry(
        "打开产品列表弹窗页",
        page,
        wait_before_action,
        open_product_list_popup,
    )
    wait_before_action(page1)
    return page1
