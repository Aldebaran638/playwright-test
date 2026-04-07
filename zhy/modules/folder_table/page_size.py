from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError


def normalize_page_size_text(text: str) -> str:
    return " ".join((text or "").replace("\n", " ").split())


def is_expected_page_size_text(text: str, expected_page_size: int) -> bool:
    normalized = normalize_page_size_text(text)
    return normalized.startswith(str(expected_page_size))


async def ensure_page_size(
    page: Page,
    expected_page_size: int,
    selectors: dict[str, str],
    timeout_ms: int,
) -> None:
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
