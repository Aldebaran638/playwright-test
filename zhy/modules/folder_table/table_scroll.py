from dataclasses import dataclass

from playwright.async_api import Page


@dataclass(frozen=True)
class ScrollSnapshot:
    top: int
    height: int
    client_height: int


async def read_scroll_snapshot(page: Page, selectors: dict[str, str]) -> ScrollSnapshot:
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
    container_selector = selectors["table_scroll_container"]
    await page.locator(container_selector).evaluate(
        "(element, step) => { element.scrollTop = element.scrollTop + step; }",
        step_pixels,
    )
    return await read_scroll_snapshot(page, selectors)


def is_scroll_stable(previous: ScrollSnapshot, current: ScrollSnapshot) -> bool:
    return (
        previous.top == current.top
        and previous.height == current.height
        and previous.client_height == current.client_height
    )
