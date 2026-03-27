from loguru import logger
from playwright.sync_api import Page

from tyc.modules.company_risk.models import RISK_LABEL_ORDER, RiskNavigationResult, RiskSummaryItem
from tyc.modules.run_step import run_step


def scan_company_risk_summary(page: Page) -> list[RiskSummaryItem]:
    # 扫描公司详情页风险概览区，按固定顺序拿到四类风险的数量。
    logger.info("[模块] 开始扫描公司详情页风险概览")
    raw_items = run_step(
        lambda: page.evaluate(
            """(labels) => {
                const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();

                const readCount = (label) => {
                    const nodes = Array.from(document.querySelectorAll("div, span"));
                    const titleNode = nodes.find((node) => normalize(node.textContent) === label);
                    if (!titleNode || !titleNode.parentElement) {
                        return { label, count: 0 };
                    }

                    const parent = titleNode.parentElement;
                    const childTexts = Array.from(parent.children)
                        .map((child) => normalize(child.textContent))
                        .filter(Boolean);
                    const numberText = childTexts.find((text) => /^\\d+$/.test(text));

                    if (numberText) {
                        return { label, count: Number.parseInt(numberText, 10) || 0 };
                    }

                    const mergedText = normalize(parent.textContent).replace(/ /g, "");
                    const match = mergedText.match(new RegExp(label + "(\\\\d+)"));
                    return { label, count: match ? Number.parseInt(match[1], 10) || 0 : 0 };
                };

                return labels.map((label) => readCount(label));
            }""",
            list(RISK_LABEL_ORDER),
        ),
        "扫描公司详情页风险概览",
        page_getter=lambda: page,
    )

    return [
        RiskSummaryItem(label=item["label"], count=int(item["count"] or 0))
        for item in raw_items
    ]


def open_first_available_risk_page(page: Page) -> tuple[RiskNavigationResult, Page | None]:
    # 依次选择第一个数量大于 0 的风险入口，并打开对应的新风险页面。
    summaries = scan_company_risk_summary(page)
    selected_item = next((item for item in summaries if item.count > 0), None)

    if selected_item is None:
        logger.info("[模块] 四类风险入口的数量都为 0，本次不进入风险详情页")
        return (
            RiskNavigationResult(
                selected_risk_type=None,
                selected_risk_count=0,
                available_risks=summaries,
                should_collect=False,
            ),
            None,
        )

    logger.info(
        f"[模块] 命中第一个可进入的风险入口: {selected_item.label}，数量: {selected_item.count}"
    )
    risk_item = page.locator(
        f"xpath=//*[normalize-space(text())='{selected_item.label}']/parent::*"
    ).first

    def open_risk_popup() -> Page:
        with page.context.expect_page() as popup_info:
            risk_item.click()
        popup_page = popup_info.value
        popup_page.wait_for_load_state("domcontentloaded")
        return popup_page

    popup_page = run_step(
        open_risk_popup,
        f"点击风险入口并打开新页面: {selected_item.label}",
        page_getter=lambda: page,
    )
    return (
        RiskNavigationResult(
            selected_risk_type=selected_item.label,
            selected_risk_count=selected_item.count,
            available_risks=summaries,
            should_collect=True,
        ),
        popup_page,
    )
