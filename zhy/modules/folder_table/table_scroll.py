from dataclasses import dataclass

from playwright.async_api import Page


@dataclass(frozen=True)
class ScrollSnapshot:
    # 记录一次滚动容器的状态，用来判断是否已经滚到底。
    top: int
    height: int
    client_height: int


async def read_scroll_snapshot(page: Page, selectors: dict[str, str]) -> ScrollSnapshot:
    # 读取表格内部滚动容器的当前位置和尺寸。
    container_selector = selectors["table_scroll_container"]
    top, height, client_height = await page.locator(container_selector).evaluate(
        """
        (element) => [
            Math.floor(element.scrollTop || 0),
            Math.floor(element.scrollHeight || 0),
            Math.floor(element.clientHeight || 0),
        ]
        """
    )
    return ScrollSnapshot(top=top, height=height, client_height=client_height)


async def scroll_table_by(
    page: Page,
    selectors: dict[str, str],
    step_pixels: int,
) -> ScrollSnapshot:
    # 只滚动表格内部容器，不滚整个页面。
    container_selector = selectors["table_scroll_container"]
    await page.locator(container_selector).evaluate(
        "(element, step) => { element.scrollTop = element.scrollTop + step; }",
        step_pixels,
    )
    return await read_scroll_snapshot(page, selectors)


def is_scroll_stable(previous: ScrollSnapshot, current: ScrollSnapshot) -> bool:
    # 当滚动位置和滚动高度都不再变化时，说明这一轮已经接近底部。
    return (
        previous.top == current.top
        and previous.height == current.height
        and previous.client_height == current.client_height
    )
