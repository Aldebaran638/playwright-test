import random
import time

from playwright.sync_api import Locator, Page


def scroll_page_down_a_bit(page: Page):
    # 目标卡片已出现但图片未加载时，继续向下滚一点触发懒加载
    page.mouse.wheel(0, random.randint(250, 600))
    time.sleep(random.uniform(0.5, 2))


def find_target_card(page: Page, target_card_title: str) -> Locator:
    # 根据卡片标题查找目标卡片容器
    return page.locator("div[role='group']").filter(
        has=page.get_by_text(target_card_title, exact=False)
    ).first


def has_target_card(page: Page, target_card_title: str) -> bool:
    # 判断当前结果列表里是否已经出现目标卡片
    return find_target_card(page, target_card_title).count() > 0


def is_card_image_loaded(card: Locator) -> bool:
    # 判断卡片内图片是否已经完成加载
    image = card.locator("img").first
    if image.count() == 0:
        return False

    return image.evaluate(
        """
        (img) => Boolean(
            img &&
            img.complete &&
            img.naturalWidth > 0 &&
            (img.currentSrc || img.getAttribute("src"))
        )
        """
    )


def wait_for_target_card_image(page: Page, target_card_title: str, max_retries=15) -> Locator:
    # 定位目标卡片，并等待其图片加载完成后返回卡片对象
    if not has_target_card(page, target_card_title):
        raise RuntimeError("target card is not visible on the current page")

    target_card = find_target_card(page, target_card_title)
    target_card.scroll_into_view_if_needed()

    for _ in range(max_retries):
        if is_card_image_loaded(target_card):
            return target_card

        print("target card found, but image not loaded yet; scroll and retry...")
        scroll_page_down_a_bit(page)
        target_card.scroll_into_view_if_needed()

    raise RuntimeError("target card found, but its image was not loaded in time")
