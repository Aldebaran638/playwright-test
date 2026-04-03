from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from loguru import logger


LEGAL_LITIGATION_TYPES = [
    "司法案件",
    "开庭公告",
    "裁判文书",
    "法院公告",
    "限制消费令",
    "限制出境",
    "终本案件",
    "失信被执行人",
    "被执行人",
    "股权冻结",
    "送达公告",
    "立案信息",
    "破产案件",
    "司法拍卖",
    "询价评估",
    "财产悬赏公告",
    "诉前调解",
    "执行公告",
    "法庭审理",
]

BUSINESS_RISK_TYPES = [
    "注销备案",
    "简易注销",
    "清算信息",
    "惩戒名单",
    "严重违法",
    "行政处罚",
    "环保处罚",
    "税收违法",
    "税务非正常户",
    "欠税公告",
    "违规处理",
    "经营异常",
    "政府约谈",
    "产品召回",
    "土地抵押",
    "股权出质",
    "股权质押",
    "对外担保",
    "担保风险",
    "动产抵押",
    "劳动仲裁",
    "公示催告"
]

RISK_TYPE_CONFIG: dict[str, dict[str, Any]] = {
    "司法案件": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "开庭公告": {
        "name_field": ["title","案由"],
        "date_fields_priority": ["开庭时间"],
    },
    "裁判文书": {
        "name_field": ["案由", "案号", "title"],
        "date_fields_priority": ["裁判日期", "发布日期"],
    },
    "法院公告": {
        "name_field": ["title", "公告类型", "案由"],
        "date_fields_priority": ["刊登时间"],
    },
    "限制消费令": {
        "name_field": ["title", "案号", "限消令对象"],
        "date_fields_priority": ["发布日期", "立案日期"],
    },
    "限制出境": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "终本案件": {
        "name_field": ["案号", "title"],
        "date_fields_priority": ["立案日期", "终本日期"],
    },
    "失信被执行人": {
        "name_field": ["案号", "失信被执行人", "title"],
        "date_fields_priority": [""],
    },
    "被执行人": {
        "name_field": ["案号", "title"],
        "date_fields_priority": [""],
    },
    "股权冻结": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "送达公告": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "立案信息": {
        "name_field": ["案由", "案号", "title"],
        "date_fields_priority": [""],
    },
    "破产案件": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "司法拍卖": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "询价评估": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "财产悬赏公告": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "诉前调解": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "执行公告": {
        "name_field": ["执行标的", "案号", "title"],
        "date_fields_priority": [""],
    },
    "法庭审理": {
        "name_field": ["案由", "title"],
        "date_fields_priority": [""],
    },
    "注销备案": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "简易注销": {
        "name_field": ["注销结果", "title"],
        "date_fields_priority": ["公告申请日期"],
    },
    "清算信息": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "惩戒名单": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "严重违法": {
        "name_field": ["违法原因", "title"],
        "date_fields_priority": [""],
    },
    "行政处罚": {
        "name_field": ["处罚原因", "title"],
        "date_fields_priority": ["处罚日期"],
    },
    "环保处罚": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "税收违法": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "税务非正常户": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "欠税公告": {
        "name_field": ["欠税税种", "title"],
        "date_fields_priority": [""],
    },
    "违规处理": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "经营异常": {
        "name_field": ["列入经营异常名录原因", "移出经营异常名录原因", "title"],
        "date_fields_priority": [""],
    },
    "政府约谈": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "产品召回": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "土地抵押": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "股权出质": {
        "name_field": ["出质人", "title"],
        "date_fields_priority": [""],
    },
    "股权质押": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "对外担保": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "担保风险": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "动产抵押": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
    "劳动仲裁": {
        "name_field": ["案由", "title"],
        "date_fields_priority": [""],
    },
    "公示催告": {
        "name_field": ["title"],
        "date_fields_priority": [""],
    },
}

DEFAULT_NAME_PLACEHOLDER = "-"


@dataclass
class ConversionStats:
    companies_total: int = 0
    records_total: int = 0
    records_converted: int = 0
    skipped_missing_date: int = 0
    skipped_unknown_type: int = 0


def convert_risk_results_file(
    input_file: str | Path,
    output_file: str | Path | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, str]]:
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"[risk_daily_converter] 输入文件不存在: {input_path}")
        return []

    output_path = Path(output_file) if output_file is not None else input_path.with_name(
        f"{input_path.stem}_daily_summary.json"
    )

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"[risk_daily_converter] 成功读取输入文件: {input_path}")

        output_records = convert_risk_results_data(data, start_date=start_date, end_date=end_date)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_records, f, ensure_ascii=False, indent=2)

        logger.info(f"[risk_daily_converter] 转换结果已保存到: {output_path}")
        return output_records

    except Exception as e:
        logger.error(f"[risk_daily_converter] 转换过程中发生错误: {e}")
        return []


def convert_risk_results_data(
    data: dict[str, Any],
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, str]]:
    successful_results = data.get("successful_results", [])
    if not isinstance(successful_results, list):
        raise ValueError("输入数据缺少 successful_results 列表")

    start_date_obj, end_date_obj = parse_date_range(start_date, end_date)

    stats = ConversionStats(companies_total=len(successful_results))
    unknown_type_counter: Counter[str] = Counter()
    output_records: list[dict[str, str]] = []

    for company_result in successful_results:
        company_name = str(company_result.get("company_name", "")).strip()
        risk_records = company_result.get("risk_records", [])
        if not isinstance(risk_records, list) or not risk_records:
            continue

        grouped_records: dict[str, dict[str, list[str]]] = {}

        for record in risk_records:
            stats.records_total += 1

            if not isinstance(record, dict):
                continue

            title = str(record.get("title", "")).strip()
            risk_type = str(record.get("risk_type", "")).strip()
            fields = record.get("fields", {})
            if not isinstance(fields, dict):
                fields = {}

            record_date = extract_record_date(
                risk_type,
                fields,
                start_date=start_date_obj,
                end_date=end_date_obj,
            )
            if not record_date:
                stats.skipped_missing_date += 1
                logger.warning(
                    f"[risk_daily_converter] 跳过缺失日期记录: company={company_name or '-'}, "
                    f"risk_type={risk_type or '-'}, title={title or '-'}"
                )
                continue

            risk_class = classify_risk(risk_type)
            if risk_class == "unknown":
                stats.skipped_unknown_type += 1
                unknown_type_counter[risk_type or "<空风险类型>"] += 1
                continue

            group = grouped_records.setdefault(
                record_date,
                {
                    "legal_types": [],
                    "legal_names": [],
                    "business_types": [],
                    "business_names": [],
                },
            )

            resolved_name = resolve_record_name(risk_type, fields, title)

            if risk_class == "legal":
                group["legal_types"].append(risk_type)
                group["legal_names"].append(resolved_name)
            elif risk_class == "business":
                group["business_types"].append(risk_type)
                group["business_names"].append(resolved_name)

            stats.records_converted += 1

        for record_date in sorted(grouped_records.keys()):
            group = grouped_records[record_date]
            output_records.append(
                {
                    "公司名称": company_name,
                    "时间": record_date,
                    "法律诉讼类型": join_record_values(group["legal_types"]),
                    "法律诉讼名称": join_record_values(group["legal_names"]),
                    "经营风险类型": join_record_values(group["business_types"]),
                    "经营风险名称": join_record_values(group["business_names"]),
                }
            )

    _log_conversion_summary(stats, unknown_type_counter)
    return output_records


def classify_risk(risk_type: str) -> str:
    if risk_type in LEGAL_LITIGATION_TYPES:
        return "legal"
    if risk_type in BUSINESS_RISK_TYPES:
        return "business"
    return "unknown"


def extract_record_date(
    risk_type: str,
    fields: dict[str, Any],
    start_date: date | None = None,
    end_date: date | None = None,
) -> str | None:
    config = RISK_TYPE_CONFIG.get(risk_type, {})
    for field_name in config.get("date_fields_priority", []):
        extracted_date = extract_date_from_value(
            fields.get(field_name),
            start_date=start_date,
            end_date=end_date,
        )
        if extracted_date:
            return extracted_date

    for value in fields.values():
        extracted_date = extract_date_from_value(
            value,
            start_date=start_date,
            end_date=end_date,
        )
        if extracted_date:
            return extracted_date

    return None


def extract_date_from_value(
    value: Any,
    start_date: date | None = None,
    end_date: date | None = None,
) -> str | None:
    for candidate in iterate_text_candidates(value):
        extracted_date = extract_date_from_text(candidate)
        if extracted_date and is_date_in_range(extracted_date, start_date, end_date):
            return extracted_date
    return None


def parse_date_range(
    start_date: str | None,
    end_date: str | None,
) -> tuple[date | None, date | None]:
    if not start_date and not end_date:
        return None, None

    if not start_date or not end_date:
        raise ValueError("start_date 和 end_date 必须同时提供")

    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

    if start_date_obj > end_date_obj:
        raise ValueError("start_date 不能晚于 end_date")

    return start_date_obj, end_date_obj


def is_date_in_range(
    date_text: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> bool:
    if start_date is None and end_date is None:
        return True

    current_date = datetime.strptime(date_text, "%Y-%m-%d").date()
    if start_date is not None and current_date < start_date:
        return False
    if end_date is not None and current_date > end_date:
        return False
    return True


def extract_date_from_text(text: str) -> str | None:
    if not text:
        return None

    patterns = [
        r"(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}",
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{4}年\d{2}月\d{2}日)\s+\d{2}:\d{2}",
        r"(\d{4}年\d{2}月\d{2}日)",
        r"(\d{4}/\d{2}/\d{2})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        date_value = match.group(1)
        return (
            date_value.replace("年", "-")
            .replace("月", "-")
            .replace("日", "")
            .replace("/", "-")
        )

    return None


def resolve_record_name(risk_type: str, fields: dict[str, Any], title: str) -> str:
    config = RISK_TYPE_CONFIG.get(risk_type, {})
    name_fields = config.get("name_field", [])

    for field_name in normalize_name_fields(name_fields):
        if field_name == "title":
            candidate_value = normalize_field_text(title)
        else:
            candidate_value = normalize_field_text(fields.get(field_name))

        if is_valid_name_value(candidate_value):
            return candidate_value

    return DEFAULT_NAME_PLACEHOLDER


def normalize_name_fields(name_fields: Any) -> list[str]:
    if isinstance(name_fields, list):
        return [str(field_name).strip() for field_name in name_fields if str(field_name).strip()]

    if isinstance(name_fields, str) and name_fields.strip():
        return [name_fields.strip()]

    return []


def is_valid_name_value(value: str) -> bool:
    normalized_value = str(value).strip()
    return bool(normalized_value) and normalized_value != DEFAULT_NAME_PLACEHOLDER


def normalize_field_text(value: Any) -> str:
    parts = [candidate for candidate in iterate_text_candidates(value) if candidate]
    if not parts:
        return ""
    return "；".join(parts)


def iterate_text_candidates(value: Any) -> list[str]:
    if isinstance(value, list):
        candidates: list[str] = []
        for item in value:
            item_text = str(item).strip()
            if item_text:
                candidates.append(item_text)
        return candidates

    if value is None:
        return []

    value_text = str(value).strip()
    return [value_text] if value_text else []


def join_record_values(values: list[str]) -> str:
    return "\n".join(values) if values else ""


def _log_conversion_summary(stats: ConversionStats, unknown_type_counter: Counter[str]) -> None:
    logger.info(
        "[risk_daily_converter] 转换统计: "
        f"companies={stats.companies_total}, "
        f"records_total={stats.records_total}, "
        f"records_converted={stats.records_converted}, "
        f"skipped_missing_date={stats.skipped_missing_date}, "
        f"skipped_unknown_type={stats.skipped_unknown_type}"
    )

    if unknown_type_counter:
        unknown_summary = ", ".join(
            f"{risk_type} x{count}" for risk_type, count in unknown_type_counter.most_common()
        )
        logger.warning(f"[risk_daily_converter] 检测到未知风险类型: {unknown_summary}")


__all__ = [
    "BUSINESS_RISK_TYPES",
    "DEFAULT_NAME_PLACEHOLDER",
    "LEGAL_LITIGATION_TYPES",
    "RISK_TYPE_CONFIG",
    "classify_risk",
    "convert_risk_results_data",
    "convert_risk_results_file",
    "extract_date_from_text",
    "extract_record_date",
    "is_date_in_range",
    "is_valid_name_value",
    "normalize_name_fields",
    "parse_date_range",
    "resolve_record_name",
]