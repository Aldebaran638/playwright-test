from typing import Any, List, Dict
from datetime import datetime
import re

from playwright.sync_api import Page, Locator
from tyc.modules.run_step import run_step


def extract_risk_data(page: Page, company_name: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    前置状态：page 停在该公司风险详情页
    后置状态：page 仍停在该公司风险详情页（不做任何跳转）
    返回：list[dict]，每个 dict 代表一条风险记录
    失败：异常向上抛，由外层 run_step 捕获，整个公司跳过
    """
    records_container = page.locator("#search-bar + div > div:nth-child(3)")

    run_step(
        lambda: records_container.locator("xpath=./div[1]").wait_for(),
        step_name="等待记录列表",
        critical=True,
        retries=2,
    )

    records_result = run_step(
        lambda: records_container.locator("xpath=./div").all(),
        step_name="获取记录列表",
        critical=True,
        retries=1,
    )
    records = getattr(records_result, "value", records_result)

    result: List[Dict[str, Any]] = []

    for wrapper in records:
        try:
            # 这层 wrapper 下面第一层才是真正的公告主体 _fb6b9
            record_root = wrapper.locator("xpath=./div[1]")
            if record_root.count() == 0:
                record_root = wrapper

            # record_root 下：
            #   第1块 = 标题块 _82793
            #   第2块 = 详情块 _033d9
            header = record_root.locator("xpath=./div[1]")
            detail_root = record_root.locator("xpath=./div[2]")

            title = ""
            risk_type = ""

            if header.count() > 0:
                title = _safe_inner_text(header.locator("xpath=./div[1]"))
                risk_type = _safe_inner_text(header.locator("xpath=./div[2]"))

            fields = _parse_detail_fields(detail_root)

            item = {
                "title": title,
                "risk_type": risk_type,
                "fields": fields,
            }
            result.append(item)

        except Exception:
            # 单条失败不影响整体
            continue

    return _filter_by_date(result, start_date, end_date)


def _parse_detail_fields(detail_root: Locator) -> Dict[str, Any]:
    """
    解析详情字段：
    - 不用 class
    - 仍然用冒号识别 label
    - 每条公告字段动态生成
    - 同名字段保留为 list
    """
    fields: Dict[str, Any] = {}

    if detail_root.count() == 0:
        return fields

    # 只抓叶子节点，避免把外层容器误判成 label
    candidates = detail_root.locator(
        "xpath=.//*[contains(normalize-space(string(.)), '：') or contains(normalize-space(string(.)), ':')]"
    ).all()

    for label_el in candidates:
        try:
            # 只处理叶子节点
            if label_el.locator("xpath=./*").count() != 0:
                continue

            label_text = _safe_inner_text(label_el)
            key = _clean_label(label_text)
            if not key:
                continue

            value_text = _extract_value_after_label(label_el)
            if not value_text:
                continue

            _append_field(fields, key, value_text)

        except Exception:
            continue

    # 兜底：如果结构化解析一个字段都没抓到，再做一次弱文本兜底
    if not fields:
        raw_text = _safe_inner_text(detail_root)
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


def _extract_value_after_label(label_el: Locator) -> str:
    """
    label 节点后面的兄弟节点，就是 value。
    不依赖 class，只依赖兄弟关系。
    """
    try:
        # 先找直接后续兄弟
        sibling = label_el.locator("xpath=following-sibling::*[1]")
        if sibling.count() > 0:
            value_text = _safe_inner_text(sibling)
            if value_text:
                return value_text

        # 兜底：某些结构里 label 的父节点下，第二个子节点就是 value
        parent = label_el.locator("xpath=..")
        if parent.count() > 0:
            second_child = parent.locator("xpath=./*[2]")
            if second_child.count() > 0:
                value_text = _safe_inner_text(second_child)
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
    """
    最后兜底：从整段文本中抽取“字段：值”。
    """
    pairs: List[tuple[str, str]] = []
    if not text:
        return pairs

    # 分段后再抽，减少误切
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


def _safe_inner_text(locator: Locator) -> str:
    try:
        if locator.count() == 0:
            return ""
        text = locator.inner_text()
        return re.sub(r"\s+", " ", text).strip()
    except Exception:
        return ""


def _filter_by_date(records: List[Dict[str, Any]], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    根据日期范围筛选记录：
    - 只要该条记录里任意一个日期字段命中范围，就保留
    - 如果没有日期字段，也保留
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    filtered = []

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
                    if len(date_str) == 10:
                        record_date = datetime.strptime(date_str, "%Y-%m-%d")
                    else:
                        record_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")

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
    if not text:
        return None

    text = str(text)

    match = re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", text)
    if match:
        return match.group(0)

    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)

    match = re.search(r"\d{4}年\d{2}月\d{2}日\s+\d{2}:\d{2}", text)
    if match:
        return match.group(0).replace("年", "-").replace("月", "-").replace("日", "")

    match = re.search(r"\d{4}年\d{2}月\d{2}日", text)
    if match:
        return match.group(0).replace("年", "-").replace("月", "-").replace("日", "")

    return None