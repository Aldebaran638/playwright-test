import re

from playwright.sync_api import Locator, Page


def open_target_card_detail(page: Page, target_card: Locator):
    # 点击目标卡片中的“阅读Analysis”链接，并等待详情页弹窗打开
    with page.expect_popup() as page1_info:
        target_card.get_by_role(
            "link",
            name=re.compile(r"阅读\s*Analysis|阅读", re.I),
        ).click()

    return page1_info.value
