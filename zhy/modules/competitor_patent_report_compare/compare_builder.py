from __future__ import annotations

import json
import re
import zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree as ET

from loguru import logger

from zhy.modules.competitor_patent_report_compare.models import (
    CompetitorPatentReportCompareConfig,
    ComparedPatentRecord,
)


XLSX_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

REPORT_HEADERS = (
    "序号",
    "主要竞争对手",
    "发明创造名称",
    "申请人/专利权人",
    "发明人",
    "申请号/专利号",
    "申请日期",
    "授权日期",
    "法律状态",
    "技术方案",
)

COMPARE_FIELDS = REPORT_HEADERS[1:]
DATE_FIELDS = {"申请日期", "授权日期"}
ABSTRACT_FIELD = "技术方案"
AUTHORIZATION_DATE_FIELD = "授权日期"
COMPETITOR_FIELD = "主要竞争对手"
COMPETITOR_ALIAS_GROUPS = (
    ("croda", "禾大", "CRODA"),
    ("elc", "雅诗兰黛", "ELC"),
)


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"[，,；;、]", "", text)
    return re.sub(r"\s+", "", text)


def try_convert_excel_serial_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if not re.fullmatch(r"\d+(?:\.0+)?", text):
        return text

    try:
        serial = int(float(text))
    except ValueError:
        return text
    if serial < 1 or serial > 60000:
        return text

    converted = date(1899, 12, 30) + timedelta(days=serial)
    return f"{converted.year}/{converted.month}/{converted.day}"


def try_normalize_calendar_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = re.fullmatch(r"(\d{4})\s*[-/.]\s*(\d{1,2})\s*[-/.]\s*(\d{1,2})", text)
    if not match:
        return text
    year, month, day = (int(part) for part in match.groups())
    try:
        normalized = date(year, month, day)
    except ValueError:
        return text
    return f"{normalized.year}/{normalized.month}/{normalized.day}"


def normalize_competitor_alias(value: str) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return ""
    lowered = normalized.lower()
    for aliases in COMPETITOR_ALIAS_GROUPS:
        alias_keys = {normalize_text(alias).lower() for alias in aliases}
        if lowered in alias_keys:
            return normalize_text(aliases[0])
    return normalized


def canonicalize_field_value(field_name: str, value: str) -> str:
    text = value
    if field_name in DATE_FIELDS:
        text = try_convert_excel_serial_date(text)
        text = try_normalize_calendar_date(text)
    if field_name == COMPETITOR_FIELD:
        return normalize_competitor_alias(text)
    return normalize_text(text)


def detect_text_language(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    has_hiragana = bool(re.search(r"[\u3040-\u309f]", text))
    has_katakana = bool(re.search(r"[\u30a0-\u30ff\u31f0-\u31ff]", text))
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", text))
    has_latin = bool(re.search(r"[A-Za-z]", text))
    if has_hiragana or has_katakana:
        return "ja"
    if has_cjk and not has_latin:
        return "zh"
    if has_latin and not has_cjk:
        return "en"
    if has_cjk and has_latin:
        return "mixed"
    return "other"


def build_field_difference(field_name: str, manual_value: str, generated_value: str) -> dict | None:
    if manual_value == generated_value:
        return None
    if field_name == ABSTRACT_FIELD:
        manual_language = detect_text_language(manual_value)
        generated_language = detect_text_language(generated_value)
        if manual_language and generated_language and manual_language != generated_language:
            return {
                "field": field_name,
                "manual": "",
                "generated": "",
                "comparison_note": "语言不同，暂不比较",
            }
    return {
        "field": field_name,
        "manual": manual_value,
        "generated": generated_value,
    }


def excel_column_name_to_index(column_name: str) -> int:
    value = 0
    for char in column_name:
        if not char.isalpha():
            break
        value = value * 26 + (ord(char.upper()) - 64)
    return value


def split_cell_ref(cell_ref: str) -> tuple[int, int]:
    column_part = "".join(char for char in cell_ref if char.isalpha())
    row_part = "".join(char for char in cell_ref if char.isdigit())
    return int(row_part), excel_column_name_to_index(column_part)


def load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        shared_xml = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    root = ET.fromstring(shared_xml)
    strings: list[str] = []
    for item in root.findall("main:si", XLSX_NS):
        texts = [node.text or "" for node in item.findall(".//main:t", XLSX_NS)]
        strings.append("".join(texts))
    return strings


def extract_cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        texts = [node.text or "" for node in cell.findall(".//main:t", XLSX_NS)]
        return "".join(texts)
    if cell_type == "s":
        value_node = cell.find("main:v", XLSX_NS)
        if value_node is None or value_node.text is None:
            return ""
        try:
            index = int(value_node.text)
        except ValueError:
            return ""
        return shared_strings[index] if 0 <= index < len(shared_strings) else ""

    value_node = cell.find("main:v", XLSX_NS)
    return value_node.text or "" if value_node is not None else ""


def parse_sheet_cells(archive: zipfile.ZipFile, sheet_path: str) -> tuple[dict[tuple[int, int], str], list[str]]:
    sheet_xml = archive.read(sheet_path)
    root = ET.fromstring(sheet_xml)
    shared_strings = load_shared_strings(archive)

    cell_values: dict[tuple[int, int], str] = {}
    merged_ranges: list[str] = []

    for row in root.findall("main:sheetData/main:row", XLSX_NS):
        for cell in row.findall("main:c", XLSX_NS):
            cell_ref = cell.get("r") or ""
            if not cell_ref:
                continue
            row_index, column_index = split_cell_ref(cell_ref)
            cell_values[(row_index, column_index)] = normalize_text(extract_cell_text(cell, shared_strings))

    merge_cells = root.find("main:mergeCells", XLSX_NS)
    if merge_cells is not None:
        for merge_cell in merge_cells.findall("main:mergeCell", XLSX_NS):
            merge_ref = merge_cell.get("ref") or ""
            if merge_ref:
                merged_ranges.append(merge_ref)

    return cell_values, merged_ranges


def apply_merged_ranges(cell_values: dict[tuple[int, int], str], merged_ranges: list[str]) -> dict[tuple[int, int], str]:
    filled = dict(cell_values)
    for merge_ref in merged_ranges:
        if ":" not in merge_ref:
            continue
        start_ref, end_ref = merge_ref.split(":", 1)
        start_row, start_col = split_cell_ref(start_ref)
        end_row, end_col = split_cell_ref(end_ref)
        top_left_value = filled.get((start_row, start_col), "")
        for row_index in range(start_row, end_row + 1):
            for col_index in range(start_col, end_col + 1):
                if not filled.get((row_index, col_index)):
                    filled[(row_index, col_index)] = top_left_value
    return filled


def resolve_first_sheet_path(archive: zipfile.ZipFile) -> str:
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    sheet = workbook_root.find("main:sheets/main:sheet", XLSX_NS)
    if sheet is None:
        raise ValueError("xlsx workbook has no sheet")
    relation_id = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
    if not relation_id:
        raise ValueError("xlsx first sheet missing relationship id")

    rels_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for rel in rels_root.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
        if rel.get("Id") == relation_id:
            target = rel.get("Target") or ""
            if not target:
                break
            return f"xl/{target}"
    raise ValueError("unable to resolve first sheet path from workbook relationships")


def load_report_records(report_path: Path) -> dict[str, ComparedPatentRecord]:
    """简介：读取一份竞争对手专利报表，并转换成按专利主键索引的记录字典。
    参数：report_path 为要对比的 xlsx 文件路径。
    返回值：key -> ComparedPatentRecord 字典。
    逻辑：解析首个 sheet、还原合并单元格值，再按表头列顺序提取每条专利记录。
    """

    with zipfile.ZipFile(report_path, "r") as archive:
        sheet_path = resolve_first_sheet_path(archive)
        raw_cells, merged_ranges = parse_sheet_cells(archive, sheet_path)
        cell_values = apply_merged_ranges(raw_cells, merged_ranges)

    header_row_index = 2
    header_by_column = {
        column_index: normalize_text(cell_values.get((header_row_index, column_index), ""))
        for column_index in range(1, len(REPORT_HEADERS) + 1)
    }
    if tuple(header_by_column[index] for index in range(1, len(REPORT_HEADERS) + 1)) != REPORT_HEADERS:
        raise ValueError(f"unexpected report header in {report_path}")

    max_row = max((row_index for row_index, _ in cell_values.keys()), default=0)
    records: dict[str, ComparedPatentRecord] = {}
    for row_index in range(3, max_row + 1):
        key = normalize_text(cell_values.get((row_index, 6), ""))
        if not key:
            continue
        fields = {}
        for column_index in range(1, len(REPORT_HEADERS) + 1):
            field_name = REPORT_HEADERS[column_index - 1]
            raw_value = cell_values.get((row_index, column_index), "")
            fields[field_name] = canonicalize_field_value(field_name, raw_value)
        records[key] = ComparedPatentRecord(
            key=key,
            fields=fields,
            source_row_number=row_index,
        )
    return records


def compare_report_records(
    manual_records: dict[str, ComparedPatentRecord],
    generated_records: dict[str, ComparedPatentRecord],
) -> dict:
    """简介：对比两份报表的专利记录差异。
    参数：manual_records 和 generated_records 分别为人工表、程序表标准化记录。
    返回值：结构化差异字典。
    逻辑：按“申请号/专利号”主键分为三类：只在人工表、只在程序表、双方共有但字段不一致。
    """

    manual_keys = set(manual_records)
    generated_keys = set(generated_records)

    only_in_manual = sorted(manual_keys - generated_keys)
    only_in_generated = sorted(generated_keys - manual_keys)
    shared_keys = sorted(manual_keys & generated_keys)

    differing_records: list[dict] = []
    authorization_date_different_records: list[dict] = []
    language_different_records: list[dict] = []
    for key in shared_keys:
        manual_record = manual_records[key]
        generated_record = generated_records[key]
        field_differences: list[dict] = []
        authorization_date_differences: list[dict] = []
        language_differences: list[dict] = []
        for field_name in COMPARE_FIELDS:
            manual_value = manual_record.fields.get(field_name, "")
            generated_value = generated_record.fields.get(field_name, "")
            difference = build_field_difference(field_name, manual_value, generated_value)
            if difference is None:
                continue
            if difference.get("comparison_note"):
                language_differences.append(difference)
            elif difference.get("field") == AUTHORIZATION_DATE_FIELD:
                authorization_date_differences.append(difference)
            else:
                field_differences.append(difference)
        if field_differences:
            differing_records.append(
                {
                    "key": key,
                    "manual_row_number": manual_record.source_row_number,
                    "generated_row_number": generated_record.source_row_number,
                    "manual_competitor": manual_record.fields.get("主要竞争对手", ""),
                    "generated_competitor": generated_record.fields.get("主要竞争对手", ""),
                    "field_differences": field_differences,
                }
            )
        if authorization_date_differences:
            authorization_date_different_records.append(
                {
                    "key": key,
                    "manual_row_number": manual_record.source_row_number,
                    "generated_row_number": generated_record.source_row_number,
                    "competitor_name": manual_record.fields.get("主要竞争对手", "") or generated_record.fields.get("主要竞争对手", ""),
                    "field_differences": authorization_date_differences,
                }
            )
        if language_differences:
            language_different_records.append(
                {
                    "key": key,
                    "manual_row_number": manual_record.source_row_number,
                    "generated_row_number": generated_record.source_row_number,
                    "competitor_name": manual_record.fields.get("主要竞争对手", "") or generated_record.fields.get("主要竞争对手", ""),
                    "field_differences": language_differences,
                }
            )

    return {
        "summary": {
            "manual_total": len(manual_records),
            "generated_total": len(generated_records),
            "shared_total": len(shared_keys),
            "only_in_manual_total": len(only_in_manual),
            "only_in_generated_total": len(only_in_generated),
            "different_total": len(differing_records),
            "authorization_date_different_total": len(authorization_date_different_records),
            "language_different_total": len(language_different_records),
        },
        "only_in_manual": [
            {
                "key": key,
                "row_number": manual_records[key].source_row_number,
                "competitor_name": manual_records[key].fields.get("主要竞争对手", ""),
                "title": manual_records[key].fields.get("发明创造名称", ""),
            }
            for key in only_in_manual
        ],
        "only_in_generated": [
            {
                "key": key,
                "row_number": generated_records[key].source_row_number,
                "competitor_name": generated_records[key].fields.get("主要竞争对手", ""),
                "title": generated_records[key].fields.get("发明创造名称", ""),
            }
            for key in only_in_generated
        ],
        "different_records": group_records_by_competitor(differing_records),
        "authorization_date_different_records": group_records_by_competitor(authorization_date_different_records),
        "language_different_records": group_records_by_competitor(language_different_records),
    }


def group_records_by_competitor(records: list[dict]) -> list[dict]:
    """简介：按竞争对手名称聚合差异记录。
    参数：records 为差异记录列表。
    返回值：按竞争对手分组后的记录列表 [{competitor_name, records [...]}, ...]。
    逻辑：遍历所有差异记录，按 competitor_name 分组聚合，便于报告分块展示。
    """
    grouped: dict[str, list[dict]] = {}
    for record in records:
        competitor_name = (
            record.get("competitor_name", "")
            or record.get("manual_competitor", "")
            or record.get("generated_competitor", "")
            or "未识别竞争对手"
        )
        grouped.setdefault(competitor_name, []).append(record)
    return [
        {
            "competitor_name": competitor_name,
            "records": grouped[competitor_name],
        }
        for competitor_name in sorted(grouped)
    ]


def build_markdown_report(config: CompetitorPatentReportCompareConfig, report_payload: dict) -> str:
    """简介：生成 Markdown 格式的差异报告。
    参数：config 为对比流程配置；report_payload 为 compare_report_records() 的输出。
    返回值：Markdown 文本字符串。
    逻辑：先生成汇总表格，再按竞争对手逐条展示差异明细，便于人工审查和追踪。
    """
    summary = report_payload["summary"]
    lines = [
        "# 竞争对手专利报表差异报告",
        "",
        f"- 人工表：`{config.manual_report_path}`",
        f"- 程序表：`{config.generated_report_path}`",
        "",
        "## 汇总",
        "",
        f"- 人工表专利数：{summary['manual_total']}",
        f"- 程序表专利数：{summary['generated_total']}",
        f"- 双方共有专利数：{summary['shared_total']}",
        f"- 仅人工表存在：{summary['only_in_manual_total']}",
        f"- 仅程序表存在：{summary['only_in_generated_total']}",
        f"- 共有但字段不同：{summary['different_total']}",
        f"- 授权日期不一致：{summary['authorization_date_different_total']}",
        f"- 语言不同暂不比较：{summary['language_different_total']}",
        "",
    ]

    lines.append("## 仅人工表存在")
    lines.append("")
    manual_groups = group_records_by_competitor(report_payload["only_in_manual"])
    if manual_groups:
        for group in manual_groups:
            lines.append(f"### {group['competitor_name']}")
            lines.append("")
            for item in group["records"]:
                lines.append(f"- `{item['key']}` | 发明创造名称：{item['title']} | 行号：{item['row_number']}")
            lines.append("")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 仅程序表存在")
    lines.append("")
    generated_groups = group_records_by_competitor(report_payload["only_in_generated"])
    if generated_groups:
        for group in generated_groups:
            lines.append(f"### {group['competitor_name']}")
            lines.append("")
            for item in group["records"]:
                lines.append(f"- `{item['key']}` | 发明创造名称：{item['title']} | 行号：{item['row_number']}")
            lines.append("")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 共有但字段不同")
    lines.append("")
    if report_payload["different_records"]:
        for group in report_payload["different_records"]:
            lines.append(f"### {group['competitor_name']}")
            lines.append("")
            for item in group["records"]:
                lines.append(f"- `{item['key']}` | 人工表行号：{item['manual_row_number']} | 程序表行号：{item['generated_row_number']}")
                for diff in item["field_differences"]:
                    lines.append(
                        f"  - 字段：{diff['field']} | 人工表：{diff['manual']} | 程序表：{diff['generated']}"
                    )
            lines.append("")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 授权日期不一致")
    lines.append("")
    if report_payload["authorization_date_different_records"]:
        for group in report_payload["authorization_date_different_records"]:
            lines.append(f"### {group['competitor_name']}")
            lines.append("")
            for item in group["records"]:
                lines.append(f"- `{item['key']}` | 人工表行号：{item['manual_row_number']} | 程序表行号：{item['generated_row_number']}")
                for diff in item["field_differences"]:
                    lines.append(
                        f"  - 字段：{diff['field']} | 人工表：{diff['manual']} | 程序表：{diff['generated']}"
                    )
            lines.append("")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 语言不同暂不比较")
    lines.append("")
    if report_payload["language_different_records"]:
        for group in report_payload["language_different_records"]:
            lines.append(f"### {group['competitor_name']}")
            lines.append("")
            for item in group["records"]:
                lines.append(f"- `{item['key']}` | 人工表行号：{item['manual_row_number']} | 程序表行号：{item['generated_row_number']}")
                for diff in item["field_differences"]:
                    lines.append(f"  - 字段：{diff['field']} | {diff['comparison_note']}")
            lines.append("")
    else:
        lines.append("- 无")
    lines.append("")

    return "\n".join(lines)


def run_competitor_patent_report_compare(config: CompetitorPatentReportCompareConfig) -> Path:
    """简介：对比人工表与程序表，输出结构化差异报告。
    参数：config 为对比流程配置。
    返回值：Markdown 报告路径。
    逻辑：先读取两份 xlsx，再按专利主键对比字段，最后同时输出 JSON 和 Markdown 两份报告。
    """

    if not config.manual_report_path.exists():
        raise FileNotFoundError(f"manual report not found: {config.manual_report_path}")
    if not config.generated_report_path.exists():
        raise FileNotFoundError(f"generated report not found: {config.generated_report_path}")

    manual_records = load_report_records(config.manual_report_path)
    generated_records = load_report_records(config.generated_report_path)
    report_payload = compare_report_records(manual_records, generated_records)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = config.output_dir / f"{config.report_basename}.json"
    markdown_path = config.output_dir / f"{config.report_basename}.md"
    json_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(build_markdown_report(config, report_payload), encoding="utf-8")

    logger.info(
        "[competitor_patent_report_compare] manual_total={} generated_total={} different_total={} output_json={} output_md={}",
        report_payload["summary"]["manual_total"],
        report_payload["summary"]["generated_total"],
        report_payload["summary"]["different_total"],
        json_path,
        markdown_path,
    )
    return markdown_path
