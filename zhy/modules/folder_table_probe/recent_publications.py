import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from zhy.modules.folder_table.models import FolderTarget, TableRowRecord
from zhy.modules.folder_table.writer import ensure_output_dir
from zhy.modules.folder_table_probe.models import PageProbeResult, RecentPatentPublication


PUBLICATION_NUMBER_FIELD_EXACT_NAMES = (
    "公开(公告)号",
    "公开（公告）号",
    "公开号",
    "公告号",
    "公开公告号",
)

PUBLICATION_DATE_FIELD_EXACT_NAMES = (
    "公开日期",
    "公开(公告)日",
    "公开（公告）日",
    "公开(公告)日期",
    "公开（公告）日期",
    "公开日",
    "公告日",
    "公告日期",
)

DATE_LIKE_FIELD_KEYWORDS = (
    "日期",
    "时间",
)

DATE_PATTERNS = (
    re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"),
    re.compile(r"(\d{4})/(\d{1,2})/(\d{1,2})"),
    re.compile(r"(\d{4})\.(\d{1,2})\.(\d{1,2})"),
    re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日"),
)


def _normalize_label(label: str) -> str:
    return "".join((label or "").strip().split())


def _normalize_value(value: str) -> str:
    return " ".join((value or "").replace("\n", " ").split())


def _find_publication_number_field(row: TableRowRecord) -> tuple[str, str] | None:
    normalized_to_original = {
        _normalize_label(field_name): field_name
        for field_name in row.data.keys()
    }

    for exact_name in PUBLICATION_NUMBER_FIELD_EXACT_NAMES:
        normalized_name = _normalize_label(exact_name)
        if normalized_name not in normalized_to_original:
            continue
        field_name = normalized_to_original[normalized_name]
        field_value = _normalize_value(row.data.get(field_name, ""))
        if field_value:
            return field_name, field_value

    for field_name, raw_value in row.data.items():
        normalized_name = _normalize_label(field_name)
        if "公开" in normalized_name and "号" in normalized_name:
            field_value = _normalize_value(raw_value)
            if field_value:
                return field_name, field_value
        if "公告" in normalized_name and "号" in normalized_name:
            field_value = _normalize_value(raw_value)
            if field_value:
                return field_name, field_value

    return None


def _find_date_field(row: TableRowRecord) -> tuple[str, str] | None:
    normalized_to_original = {
        _normalize_label(field_name): field_name
        for field_name in row.data.keys()
    }

    for exact_name in PUBLICATION_DATE_FIELD_EXACT_NAMES:
        normalized_name = _normalize_label(exact_name)
        if normalized_name not in normalized_to_original:
            continue
        field_name = normalized_to_original[normalized_name]
        field_value = _normalize_value(row.data.get(field_name, ""))
        if field_value:
            return field_name, field_value

    for field_name, raw_value in row.data.items():
        normalized_name = _normalize_label(field_name)
        if not any(keyword in normalized_name for keyword in DATE_LIKE_FIELD_KEYWORDS):
            continue
        field_value = _normalize_value(raw_value)
        if field_value:
            return field_name, field_value

    return None


def _parse_date(value: str) -> date | None:
    cleaned = _normalize_value(value)
    if not cleaned:
        return None

    for pattern in DATE_PATTERNS:
        match = pattern.search(cleaned)
        if match is None:
            continue
        try:
            year, month, day = (int(part) for part in match.groups())
            return date(year, month, day)
        except ValueError:
            continue
    return None


# 简介：从单个文件夹的页探测结果中筛选最近一年的专利公开号。
# 参数：
# - target: 当前文件夹目标信息。
# - page_results: 当前文件夹全部页探测结果。
# - reference_date: 参考日期，默认使用当天。
# 返回值：
# - 满足最近一年条件的公开号记录列表。
# 逻辑：
# - 每行先找公开日期；如果没有公开日期，再找第一个字段名包含“日期”或“时间”的字段；解析日期成功且位于最近一年窗口内时，提取公开号。
def select_recent_publications(
    target: FolderTarget,
    page_results: list[PageProbeResult],
    reference_date: date | None = None,
) -> list[RecentPatentPublication]:
    today = reference_date or date.today()
    cutoff_date = today - timedelta(days=365)
    matched_records: list[RecentPatentPublication] = []

    for page_result in page_results:
        if not page_result.success:
            continue

        for row in page_result.rows:
            publication_field = _find_publication_number_field(row)
            if publication_field is None:
                continue

            date_field = _find_date_field(row)
            if date_field is None:
                continue

            parsed_date = _parse_date(date_field[1])
            if parsed_date is None:
                continue
            if parsed_date < cutoff_date or parsed_date > today:
                continue

            matched_records.append(
                RecentPatentPublication(
                    space_id=target.space_id,
                    folder_id=target.folder_id,
                    page_number=row.page_number,
                    row_key=row.row_key,
                    publication_number=publication_field[1],
                    date_field_name=date_field[0],
                    date_value=date_field[1],
                    parsed_date=parsed_date.isoformat(),
                )
            )

    return matched_records


def _dedupe_publications(
    matched_records: list[RecentPatentPublication],
) -> list[RecentPatentPublication]:
    deduped_records: list[RecentPatentPublication] = []
    seen_publication_numbers: set[str] = set()

    for record in matched_records:
        publication_number = _normalize_value(record.publication_number)
        if not publication_number or publication_number in seen_publication_numbers:
            continue
        seen_publication_numbers.add(publication_number)
        deduped_records.append(record)

    return deduped_records


# 简介：把最近一年专利的公开号聚合写入单个 JSON 文件。
# 参数：
# - output_root_dir: probe 输出根目录。
# - matched_records: 当前任务累计命中的最近一年公开号记录。
# - reference_date: 参考日期，默认使用当天。
# 返回值：
# - 写出的 JSON 文件路径。
# 逻辑：
# - 对公开号去重后统一重写同一个 JSON 文件，既保留纯公开号列表，也保留每条记录所使用的日期字段信息。
def write_recent_publication_numbers(
    output_root_dir: Path,
    matched_records: list[RecentPatentPublication],
    reference_date: date | None = None,
) -> Path:
    output_dir = ensure_output_dir(output_root_dir)
    output_path = output_dir / "recent_publication_numbers.json"
    today = reference_date or date.today()
    cutoff_date = today - timedelta(days=365)
    deduped_records = _dedupe_publications(matched_records)

    output_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "reference_date": today.isoformat(),
                "cutoff_date": cutoff_date.isoformat(),
                "publication_number_count": len(deduped_records),
                "publication_numbers": [record.publication_number for record in deduped_records],
                "records": [
                    {
                        "space_id": record.space_id,
                        "folder_id": record.folder_id,
                        "page_number": record.page_number,
                        "row_key": record.row_key,
                        "publication_number": record.publication_number,
                        "date_field_name": record.date_field_name,
                        "date_value": record.date_value,
                        "parsed_date": record.parsed_date,
                    }
                    for record in deduped_records
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_path