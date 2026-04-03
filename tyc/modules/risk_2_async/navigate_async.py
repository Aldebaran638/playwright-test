from __future__ import annotations

import re

from loguru import logger
from playwright.async_api import Page

from tyc.modules.risk_2_async.run_step_async import run_step_async


async def navigate_to_risk_page_async(page: Page, company_name: str) -> bool:
    search_box = page.get_by_role("textbox").first
    await run_step_async(
        search_box.fill,
        company_name,
        step_name="填入公司名称到搜索框",
        critical=True,
        retries=1,
    )

    search_buttons = page.get_by_role("button")
    button_count = await search_buttons.count()
    found = False
    for index in range(button_count):
        button = search_buttons.nth(index)
        try:
            text = await button.inner_text()
            if "搜索" in text or "天眼一下" in text:
                await run_step_async(
                    button.click,
                    step_name="点击搜索按钮",
                    critical=True,
                    retries=1,
                )
                found = True
                break
        except Exception:
            continue

    if not found:
        await run_step_async(
            page.get_by_role("button").first.click,
            step_name="点击第一个按钮作为搜索按钮",
            critical=True,
            retries=1,
        )

    search_bar = page.locator("#search-bar")
    if await search_bar.count() > 0:
        sibling_div = search_bar.locator("+ div")
        if await sibling_div.count() > 0:
            first_child = sibling_div.locator("div:nth-child(1)")
            if await first_child.count() > 0:
                number_elements = first_child.locator("div, span")
                number_count = await number_elements.count()
                for index in range(number_count):
                    element = number_elements.nth(index)
                    try:
                        text = (await element.inner_text()).strip()
                        if re.fullmatch(r"\d+", text):
                            if text == "0":
                                logger.info(f"[risk_2_async.navigate] 未找到 {company_name} 的风险信息，跳过等待")
                                return False
                            logger.info(f"[risk_2_async.navigate] 找到了 {company_name} 的 {text} 条风险信息")
                            break
                    except Exception:
                        continue

    records_container = page.locator("#search-bar + div > div:nth-child(3)")
    await run_step_async(
        records_container.locator("xpath=./div[1]").wait_for,
        step_name="等待风险详情页加载完成",
        critical=True,
        retries=2,
    )
    return True