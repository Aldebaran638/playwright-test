from playwright.sync_api import Page


def collect_visible_expert_cards(page: Page) -> list[dict]:
    # 读取当前结果页中已加载出来的卡片标题和链接
    cards = []
    card_locator = page.locator("div[role='group']")

    for index in range(card_locator.count()):
        card = card_locator.nth(index)
        title_locator = card.locator("h3").first
        link_locator = card.get_by_role("link").first

        title = title_locator.inner_text().strip() if title_locator.count() else ""
        href = link_locator.get_attribute("href") if link_locator.count() else None

        if not title:
            continue

        cards.append(
            {
                "index": index,
                "title": title,
                "href": href,
            }
        )

    return cards
