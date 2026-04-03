from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List

from playwright.async_api import Locator, Page

from tyc.modules.risk_2_async.run_step_async import run_step_async


async def extract_risk_data_async(
    page: Page,
    company_name: str,
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    del company_name

    records_container = page.locator("#search-bar + div > div:nth-child(3)")
    await run_step_async(
        records_container.locator("xpath=./div[1]").wait_for,
        step_name="等待记录列表",
        critical=True,
        retries=2,
    )

    wrappers = records_container.locator("xpath=./div")
    wrapper_count = await wrappers.count()
    result: List[Dict[str, Any]] = []

    for index in range(wrapper_count):
        wrapper = wrappers.nth(index)
        try:
            record_root = wrapper.locator("xpath=./div[1]")
            if await record_root.count() == 0:
                record_root = wrapper

            header = record_root.locator("xpath=./div[1]")
            detail_root = record_root.locator("xpath=./div[2]")

            title = ""
            risk_type = ""
            if await header.count() > 0:
                title = await _safe_inner_text(header.locator("xpath=./div[1]"))
                risk_type = await _safe_inner_text(header.locator("xpath=./div[2]"))

            fields = await _parse_detail_fields_async(detail_root)
            result.append({"title": title, "risk_type": risk_type, "fields": fields})
        except Exception:
            continue

    return _filter_by_date(result, start_date, end_date)


async def _parse_detail_fields_async(detail_root: Locator) -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    if await detail_root.count() == 0:
        return fields

    candidates = detail_root.locator(
        "xpath=.//*[contains(normalize-space(string(.)), '：') or contains(normalize-space(string(.)), ':')]"
    )
    candidate_count = await candidates.count()

    for index in range(candidate_count):
        label_el = candidates.nth(index)
        try:
            if await label_el.locator("xpath=./*").count() != 0:
                continue

            label_text = await _safe_inner_text(label_el)
            key = _clean_label(label_text)
            if not key:
                continue

            value_text = await _extract_value_after_label_async(label_el)
            if not value_text:
                continue

            _append_field(fields, key, value_text)
        except Exception:
            continue

    if not fields:
        raw_text = await _safe_inner_text(detail_root)
        for key, value in _extract_inline_kv_pairs(raw_text):
            _append_field(fields, key, value)

    return fields


def _clean_label(text: str) -> str:
    if not text:
        return ""

    text = re.sub(r"\s+", " ", text).strip()
    if "：" in text:
        key = text.split("：", 1)[0]
    elif ":" in text:
        key = text.split(":", 1)[0]
    else:
        return ""
    return key.strip().rstrip("：:").strip()


async def _extract_value_after_label_async(label_el: Locator) -> str:
    try:
        sibling = label_el.locator("xpath=following-sibling::*[1]")
        if await sibling.count() > 0:
            value_text = await _safe_inner_text(sibling)
            if value_text:
                return value_text

        parent = label_el.locator("xpath=..")
        if await parent.count() > 0:
            second_child = parent.locator("xpath=./*[2]")
            if await second_child.count() > 0:
                value_text = await _safe_inner_text(second_child)
                if value_text:
                    return value_text

        return ""
    except Exception:
        return ""


def _append_field(fields: Dict[str, Any], key: str, value: str) -> None:
    if key not in fields:
        fields[key] = value
        return

    old = fields[key]
    if isinstance(old, list):
        old.append(value)
    else:
        fields[key] = [old, value]


def _extract_inline_kv_pairs(text: str) -> List[tuple[str, str]]:
    pairs: List[tuple[str, str]] = []
    if not text:
        return pairs

    chunks = re.split(r"(?<=。)|(?<=；)|(?<=\n)", text)
    for chunk in chunks:
        if "：" not in chunk and ":" not in chunk:
            continue
        if "：" in chunk:
            left, right = chunk.split("：", 1)
        else:
            left, right = chunk.split(":", 1)
        key = left.strip()
        value = right.strip()
        if key and value and len(key) <= 20:
            pairs.append((key, value))

    return pairs


async def _safe_inner_text(locator: Locator) -> str:
    try:
        if await locator.count() == 0:
            return ""
        text = await locator.inner_text()
        return re.sub(r"\s+", " ", text).strip()
    except Exception:
        return ""


def _filter_by_date(records: List[Dict[str, Any]], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    filtered: List[Dict[str, Any]] = []
    for record in records:
        fields = record.get("fields", {})
        matched = False
        has_date_field = False

        for key, value in fields.items():
            if not any(keyword in key for keyword in ["日期", "时间", "刊登", "发布", "发生"]):
                continue

            has_date_field = True
            values = value if isinstance(value, list) else [value]
            for one_value in values:
                date_str = _extract_date_from_string(str(one_value))
                if not date_str:
                    continue
                try:
                    record_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if start <= record_date <= end:
                        filtered.append(record)
                        matched = True
                        break
                except ValueError:
                    continue
            if matched:
                break

        if not matched and not has_date_field:
            filtered.append(record)

    return filtered


def _extract_date_from_string(text: str) -> str:
    patterns = [
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{4}/\d{2}/\d{2})",
        r"(\d{4}年\d{1,2}月\d{1,2}日)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        raw = match.group(1)
        if "年" in raw:
            raw = raw.replace("年", "-").replace("月", "-").replace("日", "")
        return raw.replace("/", "-")
    return ""