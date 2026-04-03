from datetime import date, datetime
from typing import Any

from loguru import logger
from playwright.sync_api import Locator, Page

from tyc.modules.business_risk.vip_detector import is_vip_section
from tyc.modules.common.run_step import run_step


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _validate_date_range(date_start: str, date_end: str) -> tuple[date, date]:
    start = _parse_date(date_start)
    end = _parse_date(date_end)
    if start is None or end is None:
        raise ValueError("日期格式必须为 YYYY-MM-DD")
    if end <= start:
        raise ValueError("结束日期必须晚于开始日期")
    return start, end


def _extract_section_snapshot(section: Locator) -> dict[str, Any]:
    return section.evaluate(
        """(node) => {
            const clean = (value) => (value || "").replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
            const allTexts = Array.from(node.querySelectorAll("*"))
                .map((item) => clean(item.innerText || item.textContent || ""))
                .filter(Boolean);

            const table = node.querySelector("table");
            const headers = table
                ? Array.from(table.querySelectorAll("thead th")).map((item, index) => clean(item.innerText || item.textContent || "") || `列${index + 1}`)
                : [];
            const rows = table
                ? Array.from(table.querySelectorAll("tbody tr")).map((tr) =>
                    Array.from(tr.querySelectorAll("td")).map((td) => clean(td.innerText || td.textContent || ""))
                )
                : [];

            return {
                section_title: allTexts[0] || "未知板块",
                has_table: Boolean(table),
                headers,
                rows,
                first_row_signature: rows.length > 0 ? rows[0].join("|") : "",
            };
        }"""
    )


def _find_date_column_indices(headers: list[str], rows: list[list[str]]) -> list[int]:
    indices = [index for index, header in enumerate(headers) if "日期" in header or "时间" in header]
    if indices:
        return indices

    if not rows:
        return []

    fallback_indices: list[int] = []
    for index, value in enumerate(rows[0]):
        if _parse_date(value) is not None:
            fallback_indices.append(index)
    return fallback_indices


def _build_field_names(headers: list[str], rows: list[list[str]]) -> list[str]:
    if headers:
        return headers

    if not rows:
        return []

    return [f"列{index + 1}" for index in range(len(rows[0]))]


def _filter_rows_by_date(
    rows: list[list[str]],
    field_names: list[str],
    date_col_indices: list[int],
    start: date,
    end: date,
) -> list[dict[str, str]]:
    filtered_rows: list[dict[str, str]] = []

    for row in rows:
        is_date_in_range = False
        for date_index in date_col_indices:
            if date_index >= len(row):
                continue

            row_date = _parse_date(row[date_index])
            if row_date is None:
                continue
            if start <= row_date <= end:
                is_date_in_range = True
                break

        if not is_date_in_range:
            continue

        row_data: dict[str, str] = {}
        for index, value in enumerate(row):
            field_name = field_names[index] if index < len(field_names) else f"列{index + 1}"
            row_data[field_name] = value
        filtered_rows.append(row_data)

    return filtered_rows


def extract_sections_by_date(
    page: Page,
    date_start: str,
    date_end: str,
    max_rows: int = 20,
) -> list[dict[str, Any]]:
    start, end = _validate_date_range(date_start, date_end)
    logger.info(
        f"[business_risk.date_range_filter] 开始提取日期范围内的板块数据: {date_start} ~ {date_end}"
    )

    elements_result = run_step(
        page.locator("[data-dim]").all,
        step_name="获取所有带有 data-dim 的板块",
        critical=False,
        retries=0,
    )
    if not elements_result.ok or elements_result.value is None:
        logger.warning("[business_risk.date_range_filter] 未获取到任何 data-dim 板块")
        return []

    result: list[dict[str, Any]] = []

    # 逐个处理经营风险板块，单个板块失败不影响其他板块继续提取。
    for section in elements_result.value:
        dim_result = run_step(
            section.get_attribute,
            "data-dim",
            step_name="读取板块 data-dim 属性",
            critical=False,
            retries=0,
        )
        dim = str(dim_result.value or "").strip()
        if not dim:
            logger.warning("[business_risk.date_range_filter] 遇到没有 data-dim 的板块，已跳过")
            continue

        try:
            vip_result = run_step(
                is_vip_section,
                page,
                dim,
                step_name=f"检查板块是否为 VIP: {dim}",
                critical=False,
                retries=0,
            )
            if vip_result.ok and vip_result.value:
                continue

            snapshot_result = run_step(
                _extract_section_snapshot,
                section,
                step_name=f"提取板块快照: {dim}",
                critical=False,
                retries=0,
            )
            if not snapshot_result.ok or snapshot_result.value is None:
                logger.warning(f"[business_risk.date_range_filter] 板块快照提取失败，已跳过: {dim}")
                continue

            snapshot = snapshot_result.value
            section_title = str(snapshot.get("section_title") or "未知板块")
            if not snapshot.get("has_table"):
                logger.warning(f"[business_risk.date_range_filter] 板块未找到表格，已跳过: {section_title}")
                continue

            headers = [str(item) for item in snapshot.get("headers", [])]
            rows = [[str(cell) for cell in row] for row in snapshot.get("rows", [])]
            date_col_indices = _find_date_column_indices(headers, rows)
            if not date_col_indices:
                logger.warning(f"[business_risk.date_range_filter] 板块未找到日期列，已跳过: {section_title}")
                continue

            field_names = _build_field_names(headers, rows)
            current_rows = [[str(cell) for cell in row] for row in snapshot.get("rows", [])]
            filtered_rows = _filter_rows_by_date(
                current_rows,
                field_names,
                date_col_indices,
                start,
                end,
            )
            
            # 限制最大行数
            if len(filtered_rows) > max_rows:
                filtered_rows = filtered_rows[:max_rows]
                logger.info(
                    f"[business_risk.date_range_filter] 板块抓取达到上限，板块: {section_title}，数量: {len(filtered_rows)}"
                )

            if not filtered_rows:
                logger.info(
                    f"[business_risk.date_range_filter] 板块存在日期列，但没有命中范围数据: {section_title}"
                )
                continue

            result.append(
                {
                    "section": section_title,
                    "dim": dim,
                    "rows": filtered_rows,
                }
            )
            logger.info(
                f"[business_risk.date_range_filter] 板块提取完成，板块: {section_title}，命中行数: {len(filtered_rows)}"
            )
        except Exception as exc:
            logger.warning(f"[business_risk.date_range_filter] 板块处理失败，已跳过: {dim} -> {exc}")
            continue

    logger.info(f"[business_risk.date_range_filter] 所有板块提取完成，有效板块数: {len(result)}")
    return result
