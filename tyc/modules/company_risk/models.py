import html
import re
from dataclasses import dataclass
from typing import Any


RISK_LABEL_ORDER = (
    "自身风险",
    "周边风险",
    "历史风险",
    "预警提醒",
)
DEFAULT_MAX_CAPTURE_COUNT = 10

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class RiskSummaryItem:
    label: str
    count: int


@dataclass(frozen=True)
class RiskNavigationResult:
    selected_risk_type: str | None
    selected_risk_count: int
    available_risks: list[RiskSummaryItem]
    should_collect: bool


def clean_risk_text(value: str | None) -> str:
    # 统一清理风险文案里的 HTML 标签、实体和多余空白。
    if not value:
        return ""

    value = html.unescape(value)
    value = HTML_TAG_PATTERN.sub("", value)
    value = WHITESPACE_PATTERN.sub(" ", value)
    return value.strip()


def trim_risk_groups_by_count(
    groups: list[dict[str, Any]],
    max_capture_count: int = DEFAULT_MAX_CAPTURE_COUNT,
) -> tuple[list[dict[str, Any]], int]:
    # 按和 mm.count 相同的 risk_count 单位截断内容，而不是按行数截断。
    trimmed_groups: list[dict[str, Any]] = []
    captured_count = 0

    for group in groups:
        trimmed_items: list[dict[str, Any]] = []

        for item in group.get("items", []):
            risk_count = max(int(item.get("risk_count") or 0), 0)

            # 已经达到上限后，不再继续收集后续条目。
            if captured_count >= max_capture_count:
                return trimmed_groups, captured_count

            # 除了第一条外，后续条目一旦会突破上限，就停止继续收集。
            if captured_count > 0 and captured_count + risk_count > max_capture_count:
                return trimmed_groups, captured_count

            trimmed_items.append(dict(item))
            captured_count += risk_count

        if trimmed_items:
            trimmed_group = dict(group)
            trimmed_group["items"] = trimmed_items
            trimmed_groups.append(trimmed_group)

    return trimmed_groups, captured_count
