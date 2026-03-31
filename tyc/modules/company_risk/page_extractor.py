from pathlib import Path
from typing import Any

from loguru import logger
from playwright.sync_api import Page

from tyc.modules.company_risk.models import (
    DEFAULT_MAX_CAPTURE_COUNT,
    clean_risk_text,
    trim_risk_groups_by_count,
)
from tyc.modules.run_step import run_step


def extract_company_risk_page(
    page: Page,
    *,
    preferred_risk_type: str | None = None,
    max_capture_count: int = DEFAULT_MAX_CAPTURE_COUNT,
    source: str | Path | None = None,
) -> dict[str, Any]:
    logger.info("[company_risk.page_extractor] 开始提取风险详情页中的 mm 数据")
    run_step(
        page.wait_for_selector,
        ".risk-block",
        timeout=15000,
        step_name="等待风险详情页主容器加载",
        critical=True,
        retries=1,
    )

    mm_data_result = run_step(
        page.evaluate,
        """(preferredName) => {
            const parseScript = (scriptText) => {
                const source = scriptText || "";
                const match = source.match(/var\\s+mm\\s*=\\s*(\\{[\\s\\S]*\\})\\s*$/);
                if (!match) {
                    return null;
                }
                return Function('"use strict"; return (' + match[1] + ');')();
            };

            const blocks = Array.from(document.querySelectorAll(".risk-block"));
            const visibleBlock = blocks.find((block) => !block.classList.contains("hidden"));
            const orderedBlocks = visibleBlock
                ? [visibleBlock, ...blocks.filter((block) => block !== visibleBlock)]
                : blocks;

            const parsedItems = orderedBlocks
                .map((block) => {
                    const script = block.querySelector("script");
                    return script ? parseScript(script.textContent || "") : null;
                })
                .filter(Boolean);

            if (preferredName) {
                const preferredItem = parsedItems.find((item) => item.name === preferredName);
                if (preferredItem) {
                    return preferredItem;
                }
            }

            return parsedItems[0] || null;
        }""",
        preferred_risk_type,
        step_name="解析风险详情页脚本中的 mm 数据",
        critical=True,
        retries=0,
    )
    if mm_data_result.value is None:
        raise RuntimeError("unable to parse risk page data from current page")

    mm_data = mm_data_result.value
    groups: list[dict[str, Any]] = []
    for group in mm_data.get("list", []):
        items: list[dict[str, Any]] = []
        for item in group.get("list", []):
            items.append(
                {
                    "title": clean_risk_text(item.get("title")),
                    "risk_count": int(item.get("riskCount") or 0),
                    "desc": clean_risk_text(item.get("desc")),
                    "company_name": clean_risk_text(item.get("companyName")),
                }
            )

        groups.append(
            {
                "group_title": clean_risk_text(group.get("title")),
                "group_tag": clean_risk_text(group.get("tag")),
                "group_total_count": int(group.get("total") or 0),
                "items": items,
            }
        )

    trimmed_groups, captured_count = trim_risk_groups_by_count(groups, max_capture_count)
    result = {
        "risk_type": clean_risk_text(mm_data.get("name")),
        "total_risk_count": int(mm_data.get("count") or 0),
        "captured_risk_count": captured_count,
        "max_capture_count": max_capture_count,
        "has_more": int(mm_data.get("count") or 0) > captured_count,
        "groups": trimmed_groups,
        "page_title": clean_risk_text(page.title()),
    }

    if source is not None:
        result["source"] = str(source)

    logger.info("[company_risk.page_extractor] 风险详情页提取完成")
    return result
