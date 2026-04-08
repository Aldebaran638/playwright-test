import json
import re
from datetime import date, datetime
from pathlib import Path

from zhy.modules.folder_table.models import FolderTarget, TableRowRecord
from zhy.modules.folder_table.writer import ensure_output_dir
from zhy.modules.folder_table_probe.models import FilteredPublicationRecord, PageProbeResult


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


def parse_filter_date(date_text: str) -> date:
    parsed_date = _parse_date(date_text)
    if parsed_date is None:
        raise ValueError(f"invalid date value: {date_text}")
    return parsed_date


def validate_date_range(start_date: date, end_date: date) -> None:
    if start_date >= end_date:
        raise ValueError("start_date must be earlier than end_date")


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


def _dedupe_publications(
    matched_records: list[FilteredPublicationRecord],
) -> list[FilteredPublicationRecord]:
    deduped_records: list[FilteredPublicationRecord] = []
    seen_publication_numbers: set[str] = set()

    for record in matched_records:
        publication_number = _normalize_value(record.publication_number)
        if not publication_number or publication_number in seen_publication_numbers:
            continue
        seen_publication_numbers.add(publication_number)
        deduped_records.append(record)

    return deduped_records


# 简介：从单个文件夹的页探测结果中筛选公开日期位于给定区间内的公开号。
# 参数：
# - target: 当前文件夹目标信息。
# - page_results: 当前文件夹全部页探测结果。
# - start_date: 起始日期，必须早于 end_date。
# - end_date: 结束日期，必须晚于 start_date。
# 返回值：
# - 命中的公开号记录列表。
# 逻辑：
# - 每行先找公开日期；如果没有公开日期，再找第一个字段名包含“日期”或“时间”的字段；解析日期成功且位于闭区间内时，提取公开号。
def select_publications_in_date_range_from_page_results(
    target: FolderTarget,
    page_results: list[PageProbeResult],
    start_date: date,
    end_date: date,
) -> list[FilteredPublicationRecord]:
    validate_date_range(start_date, end_date)
    matched_records: list[FilteredPublicationRecord] = []

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
            if parsed_date < start_date or parsed_date > end_date:
                continue

            matched_records.append(
                FilteredPublicationRecord(
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


def _load_rows_from_rows_jsonl(rows_path: Path) -> tuple[FolderTarget, list[TableRowRecord]]:
    folder_id = rows_path.parent.name
    space_id = rows_path.parent.parent.name
    target = FolderTarget(
        space_id=space_id,
        folder_id=folder_id,
        base_url="",
    )
    rows: list[TableRowRecord] = []

    for line in rows_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        rows.append(
            TableRowRecord(
                folder_id=payload["folder_id"],
                page_number=payload["page_number"],
                row_key=payload["row_key"],
                data=payload["data"],
            )
        )

    return target, rows


# 简介：从 folder_table_probe 输出目录中读取全部 rows.jsonl，并执行日期区间筛选。
# 参数：
# - output_root_dir: probe 输出根目录。
# - start_date: 起始日期，必须早于 end_date。
# - end_date: 结束日期，必须晚于 start_date。
# 返回值：
# - 命中的公开号记录列表。
# 逻辑：
# - 遍历输出根目录下每个 space/folder 的 rows.jsonl，逐文件夹构造成伪 page_results，再复用同一套筛选逻辑。
def select_publications_in_date_range_from_output(
    output_root_dir: Path,
    start_date: date,
    end_date: date,
) -> list[FilteredPublicationRecord]:
    validate_date_range(start_date, end_date)
    matched_records: list[FilteredPublicationRecord] = []

    for rows_path in sorted(output_root_dir.glob("*/*/rows.jsonl")):
        target, rows = _load_rows_from_rows_jsonl(rows_path)
        page_results = [
            PageProbeResult(
                page_number=0,
                success=True,
                schema=None,
                rows=rows,
            )
        ]
        matched_records.extend(
            select_publications_in_date_range_from_page_results(
                target=target,
                page_results=page_results,
                start_date=start_date,
                end_date=end_date,
            )
        )

    return _dedupe_publications(matched_records)


# 简介：把日期区间筛选得到的公开号写入单个 JSON 文件。
# 参数：
# - output_path: 输出 JSON 文件路径。
# - matched_records: 已筛选的公开号记录。
# - start_date: 筛选起始日期。
# - end_date: 筛选结束日期。
# 返回值：
# - 实际写出的 JSON 文件路径。
# 逻辑：
# - 先去重，再写出日期区间元数据、公开号列表以及完整命中记录。
def write_filtered_publication_numbers(
    output_path: Path,
    matched_records: list[FilteredPublicationRecord],
    start_date: date,
    end_date: date,
) -> Path:
    validate_date_range(start_date, end_date)
    ensure_output_dir(output_path.parent)
    deduped_records = _dedupe_publications(matched_records)

    output_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
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