from __future__ import annotations

import copy
from datetime import date


def parse_month_bounds(month_text: str) -> tuple[date, date]:
    """简介：把 YYYY-MM 文本转换成当月起始日和下月起始日。
    参数：month_text 为 YYYY-MM 格式月份文本。
    返回值：(month_start, next_month_start)。
    逻辑：后续所有专利是否命中目标月份，都统一基于这个半开区间判断。
    """

    year_text, month_part = month_text.split("-")
    year = int(year_text)
    month = int(month_part)
    month_start = date(year, month, 1)
    if month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month + 1, 1)
    return month_start, next_month_start


def parse_publication_date(value: object) -> date | None:
    """简介：解析专利 PBD 文本。
    参数：value 为原始 PBD 字段值。
    返回值：成功时返回 date，失败时返回 None。
    逻辑：当前只接受 YYYY-MM-DD 的公开日期字符串。
    """

    text = str(value or "").strip()
    if len(text) != 10:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def is_date_in_target_month(publication_date: date, month_start: date, next_month_start: date) -> bool:
    return month_start <= publication_date < next_month_start


def filter_patents_for_target_month(rows: list[dict], month_start: date, next_month_start: date) -> list[dict]:
    """简介：从单页专利列表中过滤出目标月份的数据。
    参数：rows 为单页 patents_data；month_start 和 next_month_start 为目标月份范围。
    返回值：仅包含目标月份专利的新列表。
    逻辑：按每条记录的 PBD 判断，未命中的行直接忽略。
    """

    matched_rows: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        publication_date = parse_publication_date(row.get("PBD"))
        if publication_date is None:
            continue
        if is_date_in_target_month(publication_date, month_start, next_month_start):
            matched_rows.append(row)
    return matched_rows


def get_page_publication_date_bounds(rows: list[dict]) -> tuple[date | None, date | None]:
    """简介：获取单页专利列表里的最新和最旧公开日期。
    参数：rows 为单页 patents_data。
    返回值：(newest_date, oldest_date)。
    逻辑：由于接口按 PBD 倒序排序，这两个边界可用于判断是否继续翻页。
    """

    dates = [parse_publication_date(row.get("PBD")) for row in rows if isinstance(row, dict)]
    valid_dates = [item for item in dates if item is not None]
    if not valid_dates:
        return None, None
    return max(valid_dates), min(valid_dates)


def build_monthly_patents_request_body(
    template: dict,
    *,
    space_id: str,
    folder_id: str,
    page: int,
    size: int,
    sort: str,
    view_type: str,
    is_init: bool,
    standard_only: bool,
) -> dict:
    """简介：基于模板构建按月抓取专利的请求体。
    参数：template 为已捕获的原始 body 模板；其余参数为当前页面和排序控制参数。
    返回值：可直接提交的请求体字典。
    """

    body = copy.deepcopy(template)
    body["space_id"] = space_id
    body["folder_id"] = folder_id
    body["page"] = page if isinstance(body.get("page"), int) else str(page)
    body["size"] = size
    body["sort"] = sort
    body["view_type"] = view_type
    body["is_init"] = is_init
    body["standard_only"] = standard_only
    return body


def build_monthly_page_output_payload(
    parsed: dict,
    matched_rows: list[dict],
    source_page_number: int,
    month_text: str,
) -> dict:
    """简介：把命中目标月份的数据写成新的页级输出结构。
    参数：parsed 为原始接口响应；matched_rows 为筛选后的记录；source_page_number 为原始请求页码；month_text 为目标月份文本。
    返回值：适合写入 page_XXXX.json 的 payload。
    """

    payload = copy.deepcopy(parsed) if isinstance(parsed, dict) else {}
    data = payload.get("data")
    if not isinstance(data, dict):
        data = {}
        payload["data"] = data
    data["patents_data"] = matched_rows
    data["month_filter"] = month_text
    data["source_page_number"] = source_page_number
    data["matched_patent_count"] = len(matched_rows)
    return payload
