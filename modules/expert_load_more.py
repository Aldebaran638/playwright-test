import random
import re
import time

from playwright.sync_api import Locator, Page


def human_wait(min_sec=0.5, max_sec=2):
    # 随机等待，避免点击节奏过于固定
    t = random.uniform(min_sec, max_sec)
    print(f"wait {t:.2f}s")
    time.sleep(t)


def is_near_page_bottom(page: Page, threshold=200) -> bool:
    # 执行一小段 js，判断当前是否已经滚动到页面底部附近
    return page.evaluate(
        """
        ([bottomThreshold]) => {
            const scrollTop = window.scrollY || document.documentElement.scrollTop;
            const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
            const pageHeight = Math.max(
                document.body.scrollHeight,
                document.documentElement.scrollHeight
            );
            return scrollTop + viewportHeight >= pageHeight - bottomThreshold;
        }
        """,
        [threshold],
    )


def scroll_page_to_bottom(page: Page, wheel_delta=1200, max_scrolls=30):
    # 使用鼠标滚轮逐步向下滚动，直到接近页面底部
    for _ in range(max_scrolls):
        # 让每次滚动像素围绕基础值上下浮动，避免节奏过于固定
        min_delta = max(1, int(wheel_delta * 0.7))
        max_delta = max(min_delta, int(wheel_delta * 1.3))
        current_delta = random.randint(min_delta, max_delta)

        # 模拟用户使用鼠标滚轮滚动页面
        page.mouse.wheel(0, current_delta)

        # 让每次滚动后的停顿时间落在 0.5~2 秒之间
        time.sleep(random.uniform(0.5, 2))

        if is_near_page_bottom(page):
            return True

    return False


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


def click_load_more(page: Page):
    # 点击“加载更多”按钮，扩展当前结果列表
    load_more_button = page.get_by_role("button", name="加载更多")
    load_more_button.wait_for(timeout=10000)
    load_more_button.click()
    human_wait()


def open_target_card_when_ready(page: Page, target_card_title: str, load_more_rounds=3):
    # 先寻找目标卡片；若不存在则滚动到底并点击“加载更多”；若存在则等待图片加载后进入详情页
    for round_index in range(load_more_rounds + 1):
        print(f"search target round {round_index + 1}")

        if has_target_card(page, target_card_title):
            target_card = find_target_card(page, target_card_title)
            target_card.scroll_into_view_if_needed()

            for _ in range(15):
                if is_card_image_loaded(target_card):
                    with page.expect_popup() as page1_info:
                        target_card.get_by_role(
                            "link",
                            name=re.compile(r"阅读\s*Analysis|阅读", re.I),
                        ).click()
                    return page1_info.value

                print("target card found, but image not loaded yet; scroll and retry...")
                scroll_page_down_a_bit(page)
                target_card.scroll_into_view_if_needed()

            raise RuntimeError("target card found, but its image was not loaded in time")

        if round_index == load_more_rounds:
            break

        reached_bottom = scroll_page_to_bottom(page)
        if not reached_bottom:
            raise RuntimeError("failed to scroll near the bottom of the page")

        click_load_more(page)

    raise RuntimeError("target card was not found after load more rounds")
