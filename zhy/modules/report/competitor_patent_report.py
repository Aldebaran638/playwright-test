from __future__ import annotations

import json
import re
import zipfile
from dataclasses import asdict
from pathlib import Path
from xml.sax.saxutils import escape

from loguru import logger

from zhy.modules.common.types.report import CompetitorPatentReportConfig, CompetitorPatentReportRow


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

COLUMN_WIDTHS = (8, 18, 28, 24, 24, 20, 14, 14, 18, 40)

MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")
LEGAL_STATUS_NORMALIZATION_MAP = {
    "PCT未进入指定国（指定期内）": "公开",
}


def validate_month_text(month_text: str) -> None:
    if not MONTH_PATTERN.match(month_text):
        raise ValueError("month must use YYYY-MM format")


def load_json_any_utf(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.replace("\n", " ").split())
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        cleaned = [normalize_text(item) for item in value]
        return "；".join(item for item in cleaned if item)
    return ""


def normalize_line_wrapped_text(value: object) -> str:
    if isinstance(value, list):
        cleaned = [normalize_text(item) for item in value]
        return "；".join(item for item in cleaned if item)
    return normalize_text(value)


def parse_folder_key(folder_dir_name: str) -> tuple[str, str]:
    if "_" not in folder_dir_name:
        return "", folder_dir_name
    return folder_dir_name.split("_", 1)


def load_folder_name_mapping(path: Path) -> dict[str, str]:
    """简介：读取 folder_id 到主要竞争对手名称的映射。
    参数：path 为 mid3.json 路径。
    返回值：folder_id 到 folder_name 的映射字典。
    逻辑：直接使用接口返回中的 folder_name，满足当前"文件夹 id 对应竞争对手名称"的口径。
    """

    payload = load_json_any_utf(path)
    items = payload.get("data") if isinstance(payload, dict) else None
    mapping: dict[str, str] = {}
    if not isinstance(items, list):
        return mapping
    for item in items:
        if not isinstance(item, dict):
            continue
        folder_id = str(item.get("folder_id") or "").strip()
        folder_name = normalize_text(item.get("folder_name"))
        if folder_id and folder_name:
            mapping[folder_id] = folder_name
    return mapping


def load_legal_status_mapping(path: Path) -> dict[str, str]:
    """简介：读取法律状态码到中文标题的映射。
    参数：path 为 mid1.json 路径。
    返回值：状态码到中文标题的映射字典。
    逻辑：优先取 title.cn，缺失时回退到 title.en。
    """

    payload = load_json_any_utf(path)
    legal_status = payload.get("data", {}).get("legalStatus", {}) if isinstance(payload, dict) else {}
    mapping: dict[str, str] = {}
    if not isinstance(legal_status, dict):
        return mapping
    for code, item in legal_status.items():
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        if not isinstance(title, dict):
            continue
        label = normalize_text(title.get("cn")) or normalize_text(title.get("en"))
        if label:
            mapping[str(code)] = label
    return mapping


def resolve_legal_status_text(codes: object, mapping: dict[str, str]) -> str:
    """简介：把一条专利的 LEGAL_STATUS 列表映射为中文文本。
    参数：codes 为状态码或状态码列表；mapping 为状态码映射表。
    返回值：拼接后的中文法律状态；全部映射失败则返回空字符串。
    逻辑：对每个状态码单独映射，缺失时打 warning，但不写入未映射值。
    """

    if isinstance(codes, list):
        code_list = [str(item).strip() for item in codes if str(item).strip()]
    else:
        single_code = str(codes).strip()
        code_list = [single_code] if single_code else []

    labels: list[str] = []
    for code in code_list:
        label = mapping.get(code)
        if not label:
            logger.warning("[competitor_patent_report] legal status code missing mapping: {}", code)
            continue
        label = LEGAL_STATUS_NORMALIZATION_MAP.get(label, label)
        labels.append(label)
    return "；".join(labels)


def resolve_authorization_date(*, publication_date: str, legal_status_text: str) -> str:
    if "授权" not in legal_status_text:
        return "/"
    return publication_date or "/"


def build_enriched_page_path(enriched_root: Path, original_root: Path, original_page_path: Path) -> Path:
    return enriched_root / original_page_path.relative_to(original_root)


def build_output_xlsx_path(output_dir: Path, month_text: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"竞争对手专利情报_{month_text}.xlsx"


def make_report_title(month_text: str) -> str:
    year, month = month_text.split("-")
    return f"竞争对手专利情报({int(year)}年{int(month)}月)"


def collect_report_rows(config: CompetitorPatentReportConfig) -> list[CompetitorPatentReportRow]:
    """简介：扫描原始页数据和补充页数据，生成 Excel 报表行列表。
    参数：config 为报表流程配置。
    返回值：排序并补序号后的报表行列表。
    逻辑：按月份筛选 PBD，结合 folder 映射、法律状态映射和补充信息，构造成表格行。
    """

    validate_month_text(config.month)
    folder_name_mapping = load_folder_name_mapping(config.folder_mapping_file)
    legal_status_mapping = load_legal_status_mapping(config.legal_status_mapping_file)

    rows: list[CompetitorPatentReportRow] = []
    page_paths = sorted(config.original_root.rglob("page_*.json"))

    for original_page_path in page_paths:
        if not original_page_path.is_file():
            continue
        original_payload = load_json_any_utf(original_page_path)
        original_rows = original_payload.get("data", {}).get("patents_data", [])
        if not isinstance(original_rows, list):
            logger.warning("[competitor_patent_report] invalid patents_data list: {}", original_page_path)
            continue

        enriched_page_path = build_enriched_page_path(config.enriched_root, config.original_root, original_page_path)
        translated_page_path = (
            build_enriched_page_path(config.translated_root, config.original_root, original_page_path)
            if config.translated_root is not None
            else None
        )
        supplement_page_path = translated_page_path if translated_page_path is not None and translated_page_path.exists() else enriched_page_path
        enriched_records_by_patent_id: dict[str, dict] = {}
        if supplement_page_path.exists():
            enriched_payload = load_json_any_utf(supplement_page_path)
            enriched_records = enriched_payload.get("records", [])
            if isinstance(enriched_records, list):
                for enriched_record in enriched_records:
                    if not isinstance(enriched_record, dict):
                        continue
                    patent_id = str(enriched_record.get("PATENT_ID") or "").strip()
                    if patent_id:
                        enriched_records_by_patent_id[patent_id] = enriched_record

        _, folder_id = parse_folder_key(original_page_path.parent.name)
        competitor_name = folder_name_mapping.get(folder_id, "")
        if not competitor_name:
            logger.warning("[competitor_patent_report] folder_id missing competitor mapping: {}", folder_id)

        for original_row in original_rows:
            if not isinstance(original_row, dict):
                continue
            publication_date = normalize_text(original_row.get("PBD"))
            if not publication_date.startswith(config.month):
                continue

            patent_id = str(original_row.get("PATENT_ID") or "").strip()
            enriched_record = enriched_records_by_patent_id.get(patent_id, {})
            application_number = normalize_text(original_row.get("APN"))
            publication_number = normalize_text(original_row.get("PN"))
            application_or_publication_number = application_number or publication_number
            legal_status_text = resolve_legal_status_text(original_row.get("LEGAL_STATUS"), legal_status_mapping)

            rows.append(
                CompetitorPatentReportRow(
                    sequence=0,
                    competitor_name=competitor_name,
                    invention_title=normalize_text(original_row.get("TITLE")),
                    applicant_or_patentee=normalize_line_wrapped_text(original_row.get("ANCS")),
                    inventors=normalize_line_wrapped_text(original_row.get("IN")),
                    application_or_publication_number=application_or_publication_number,
                    application_date=normalize_text(original_row.get("APD")),
                    publication_date=publication_date,
                    authorization_date=resolve_authorization_date(
                        publication_date=publication_date,
                        legal_status_text=legal_status_text,
                    ),
                    legal_status_text=legal_status_text,
                    technical_solution=normalize_text(enriched_record.get("ABST")),
                    source_folder_id=folder_id,
                    source_page_file=str(original_page_path),
                )
            )

    rows.sort(
        key=lambda item: (
            item.competitor_name,
            item.publication_date,
            item.application_or_publication_number,
            item.invention_title,
        )
    )

    for index, row in enumerate(rows, start=1):
        row.sequence = index
    return rows


def build_merge_ranges(rows: list[CompetitorPatentReportRow]) -> list[tuple[int, int]]:
    """简介：计算"主要竞争对手"列需要合并的连续行区间。
    参数：rows 为已排序的报表行列表。
    返回值：[(start_row, end_row)] 列表，行号按 Excel 真实行号返回。
    逻辑：只有相邻且名称相同的竞争对手才会合并，空名称不合并。
    """

    ranges: list[tuple[int, int]] = []
    if not rows:
        return ranges

    start_index = 0
    current_name = rows[0].competitor_name
    for index in range(1, len(rows) + 1):
        next_name = rows[index].competitor_name if index < len(rows) else None
        if next_name == current_name:
            continue
        if current_name and index - start_index > 1:
            ranges.append((start_index + 3, index + 2))
        if index < len(rows):
            start_index = index
            current_name = rows[index].competitor_name
    return ranges


def excel_column_name(index: int) -> str:
    result = ""
    value = index
    while value > 0:
        value, remainder = divmod(value - 1, 26)
        result = chr(65 + remainder) + result
    return result


def build_styles_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/><diagonal/></border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="5">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
  </cellXfs>
</styleSheet>"""


def build_sheet_xml(rows: list[CompetitorPatentReportRow], title_text: str) -> str:
    def inline_cell(cell_ref: str, text: str, style_id: int) -> str:
        escaped = escape(text)
        return f'<c r="{cell_ref}" t="inlineStr" s="{style_id}"><is><t xml:space="preserve">{escaped}</t></is></c>'

    def number_cell(cell_ref: str, value: int, style_id: int) -> str:
        return f'<c r="{cell_ref}" s="{style_id}"><v>{value}</v></c>'

    row_xml: list[str] = []
    row_xml.append(f'<row r="1" ht="26" customHeight="1">{inline_cell("A1", title_text, 1)}</row>')

    header_cells = []
    for index, header in enumerate(REPORT_HEADERS, start=1):
        header_cells.append(inline_cell(f"{excel_column_name(index)}2", header, 2))
    row_xml.append(f'<row r="2" ht="24" customHeight="1">{"".join(header_cells)}</row>')

    for row_number, row in enumerate(rows, start=3):
        cells = [
            number_cell(f"A{row_number}", row.sequence, 4),
            inline_cell(f"B{row_number}", row.competitor_name, 4),
            inline_cell(f"C{row_number}", row.invention_title, 3),
            inline_cell(f"D{row_number}", row.applicant_or_patentee, 3),
            inline_cell(f"E{row_number}", row.inventors, 3),
            inline_cell(f"F{row_number}", row.application_or_publication_number, 4),
            inline_cell(f"G{row_number}", row.application_date, 4),
            inline_cell(f"H{row_number}", row.authorization_date, 4),
            inline_cell(f"I{row_number}", row.legal_status_text, 3),
            inline_cell(f"J{row_number}", row.technical_solution, 3),
        ]
        row_xml.append(f'<row r="{row_number}">{"".join(cells)}</row>')

    cols_xml = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(COLUMN_WIDTHS, start=1)
    )
    merge_ranges = ['A1:J1'] + [f'B{start}:B{end}' for start, end in build_merge_ranges(rows)]
    merges_xml = "".join(f'<mergeCell ref="{merge_ref}"/>' for merge_ref in merge_ranges)

    dimension_end = max(len(rows) + 2, 2)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:J{dimension_end}"/>
  <sheetViews><sheetView workbookViewId="0"/></sheetViews>
  <sheetFormatPr defaultRowHeight="18"/>
  <cols>{cols_xml}</cols>
  <sheetData>{''.join(row_xml)}</sheetData>
  <mergeCells count="{len(merge_ranges)}">{merges_xml}</mergeCells>
</worksheet>"""


def write_report_xlsx(path: Path, title_text: str, rows: list[CompetitorPatentReportRow]) -> None:
    """简介：使用标准库生成最小可用的 XLSX 报表文件。
    参数：path 为输出文件路径；title_text 为表头标题；rows 为报表数据。
    返回值：无。
    逻辑：手动写入 Open XML 所需的几个核心文件，支持标题合并与竞争对手列合并。
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    sheet_xml = build_sheet_xml(rows, title_text)
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="竞争对手专利情报" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""
    workbook_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    root_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", root_rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", build_styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def run_competitor_patent_report(config: CompetitorPatentReportConfig) -> Path:
    """简介：执行竞争对手专利情报表生成流程。
    参数：config 为报表配置。
    返回值：生成的 xlsx 文件路径。
    逻辑：先收集行数据，再生成标题和 xlsx 文件，最后输出日志。
    """

    rows = collect_report_rows(config)
    output_path = build_output_xlsx_path(config.output_dir, config.month)
    write_report_xlsx(output_path, make_report_title(config.month), rows)
    logger.info(
        "[competitor_patent_report] month={} rows={} output={}",
        config.month,
        len(rows),
        output_path,
    )
    return output_path
