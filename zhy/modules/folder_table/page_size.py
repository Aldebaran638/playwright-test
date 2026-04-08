from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError


def normalize_page_size_text(text: str) -> str:
    # 统一清理空白，方便比较分页大小文案。
    return " ".join((text or "").replace("\n", " ").split())


def is_expected_page_size_text(text: str, expected_page_size: int) -> bool:
    # 只判断数字前缀，降低对具体语言文案的依赖。
    normalized = normalize_page_size_text(text)
    return normalized.startswith(str(expected_page_size))


async def ensure_page_size(
    page: Page,
    expected_page_size: int,
    selectors: dict[str, str],
    timeout_ms: int,
) -> None:
    # 进入每一页后都先确保切到目标分页大小，避免后续抓取总量不一致。
    selected_text_selector = selectors["page_size_selected_text"]
    trigger_selector = selectors["page_size_trigger"]
    option_template = selectors["page_size_option_template"]
    table_container_selector = selectors["table_container"]

    selected_locator = page.locator(selected_text_selector)
    selected_text = ""
    if await selected_locator.count() > 0:
        selected_text = normalize_page_size_text(await selected_locator.first.inner_text())
    if is_expected_page_size_text(selected_text, expected_page_size):
        return

    await page.locator(trigger_selector).click()
    option_selector = option_template.format(size=expected_page_size)
    await page.locator(option_selector).click()

    try:
        await page.wait_for_function(
            """
            ([selector, expected]) => {
                const element = document.querySelector(selector);
                if (!element) {
                    return false;
                }
                const text = (element.textContent || "").replace(/\\s+/g, " ").trim();
                return text.startsWith(String(expected));
            }
            """,
            arg=[selected_text_selector, expected_page_size],
            timeout=timeout_ms,
        )
    except PlaywrightTimeoutError as exc:
        raise TimeoutError(
            f"failed to switch page size to {expected_page_size}"
        ) from exc

    await page.locator(table_container_selector).wait_for(state="visible", timeout=timeout_ms)
