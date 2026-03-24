import random
import time

from playwright.sync_api import Page


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


def click_load_more(page: Page):
    # 点击“加载更多”按钮，扩展当前结果列表
    load_more_button = page.get_by_role("button", name="加载更多")
    load_more_button.wait_for(timeout=10000)
    load_more_button.click()
    human_wait()
