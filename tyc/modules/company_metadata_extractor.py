import re
from pathlib import Path
from typing import Any

from loguru import logger
from playwright.sync_api import Locator, Page

from tyc.modules.run_step import run_step


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" :：\t\r\n")


def safe_inner_text(locator: Locator) -> str:
    if locator.count() == 0:
        return ""
    return normalize_text(locator.first.inner_text())

def extract_company_metadata(page: Page, source: str | Path | None = None) -> dict[str, Any]:
    logger.info("[模块] 开始等待公司详情主容器出现")
    run_step(
        lambda: page.wait_for_selector("#J_CompanyHeaderContent", timeout=15000),
        "等待公司详情主容器加载",
        page_getter=lambda: page,
    )
    root = page.locator("#J_CompanyHeaderContent")

    data = run_step(
        lambda: root.evaluate(
            """node => {
                const clean = (text) => (text || "")
                    .replace(/\\u00a0/g, " ")
                    .replace(/\\s+/g, " ")
                    .replace(/[：:]\\s*$/, "")
                    .trim();

                const stripNoise = (element) => {
                    element.querySelectorAll("script, style, svg, img, button, i").forEach((item) => item.remove());
                    element.querySelectorAll(
                        ".index_copy-btn__o_0ZV, .hooks_copyOut__ZhgqX, .introduceRich_btn__sfAyp, .red-dots"
                    ).forEach((item) => item.remove());
                    return element;
                };

                const textOf = (selector) => {
                    const element = node.querySelector(selector);
                    if (!element) {
                        return "";
                    }

                    const clone = stripNoise(element.cloneNode(true));
                    return clean(clone.innerText || clone.textContent || "");
                };

                const detailItems = {};
                node.querySelectorAll(".index_detail-info-item__oAOqL").forEach((item) => {
                    const labelElement = item.querySelector(".index_detail-label__oRf2J");
                    if (!labelElement) {
                        return;
                    }

                    const label = clean((labelElement.innerText || labelElement.textContent || "").replace(/[：:]/g, ""));
                    if (!label) {
                        return;
                    }

                    const clone = stripNoise(item.cloneNode(true));
                    clone.querySelectorAll(".index_detail-label__oRf2J").forEach((labelNode) => labelNode.remove());

                    const value = clean(clone.innerText || clone.textContent || "");
                    if (value) {
                        detailItems[label] = value;
                    }
                });

                const companyTags = Array.from(
                    node.querySelectorAll(".index_tag-list-content__E8sLp > .index_company-tag__ZcJFV")
                )
                    .map((item) => clean(item.innerText || item.textContent || ""))
                    .filter(Boolean);

                let introduction = "";
                const introElement = node.querySelector(".introduceRich_collapse-left__5Vvd5");
                if (introElement) {
                    const clone = stripNoise(introElement.cloneNode(true));
                    clone.querySelectorAll(".introduceRich_collapse-title__XzjQz").forEach((item) => item.remove());
                    introduction = clean(clone.innerText || clone.textContent || "");
                }

                const fullClone = stripNoise(node.cloneNode(true));
                fullClone.querySelectorAll(".introduceRich_collapse-title__XzjQz").forEach((item) => item.remove());

                return {
                    company_name: textOf(".index_name__dz4jY"),
                    company_status: textOf(".index_reg-status-tag__ES7dF"),
                    company_tags: companyTags,
                    last_update: textOf(".Refresh_company-refresh__52K8W span"),
                    detail_items: detailItems,
                    introduction,
                    full_text: clean(fullClone.innerText || fullClone.textContent || ""),
                };
            }"""
        ),
        "提取公司详情页元信息",
        page_getter=lambda: page,
    )

    data["page_title"] = normalize_text(page.title())
    data["header_text"] = safe_inner_text(root)
    if source is not None:
        data["source"] = str(source)
    return data
