import asyncio

from loguru import logger
from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from zhy.modules.folder_table.models import FolderTarget, TableRowRecord, TableSchema
from zhy.modules.folder_table.page_size import ensure_page_size
from zhy.modules.folder_table.page_url import build_folder_page_url
from zhy.modules.folder_table.table_extract import extract_visible_rows, normalize_cell_text, page_has_rows
from zhy.modules.folder_table.table_schema import extract_schema_labels_from_title_attributes, extract_table_schema
from zhy.modules.folder_table.table_scroll import (
    ScrollSnapshot,
    is_scroll_stable,
    read_scroll_snapshot,
    scroll_table_by,
)
from zhy.modules.folder_table_probe.models import FolderTableProbeConfig, PageProbeResult


async def _safe_count(page: Page, selector: str) -> int:
    try:
        return await page.locator(selector).count()
    except Exception:
        return -1


async def _safe_visible(page: Page, selector: str) -> bool | None:
    try:
        locator = page.locator(selector)
        if await locator.count() == 0:
            return False
        return await locator.first.is_visible()
    except Exception:
        return None


async def _safe_all_inner_texts(page: Page, selector: str, limit: int) -> list[str]:
    try:
        values = await page.locator(selector).all_inner_texts()
    except Exception:
        return []

    results: list[str] = []
    for value in values:
        cleaned = normalize_cell_text(value)
        if not cleaned:
            continue
        results.append(cleaned)
        if len(results) >= limit:
            break
    return results


async def _safe_title_attributes(page: Page, selector: str, limit: int) -> list[str]:
    try:
        locator = page.locator(selector)
        count = await locator.count()
    except Exception:
        return []

    results: list[str] = []
    seen: set[str] = set()
    for index in range(count):
        raw_value = await locator.nth(index).get_attribute("title")
        cleaned = normalize_cell_text(raw_value or "")
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        results.append(cleaned)
        if len(results) >= limit:
            break
    return results


async def _safe_first_row_preview(page: Page, selectors: dict[str, str], limit: int) -> list[str]:
    try:
        row_locator = page.locator(selectors["table_row_selector"])
        if await row_locator.count() == 0:
            return []

        first_row = row_locator.nth(0)
        cell_locator = first_row.locator("td")
        cell_count = await cell_locator.count()
        preview: list[str] = []
        for index in range(min(cell_count, limit)):
            preview.append(normalize_cell_text(await cell_locator.nth(index).inner_text()))
        return preview
    except Exception:
        return []


async def wait_for_table_shell(page: Page, selectors: dict[str, str], timeout_ms: int) -> None:
    await page.locator(selectors["table_container"]).wait_for(state="visible", timeout=timeout_ms)
    await page.locator(selectors["table_scroll_container"]).wait_for(
        state="visible",
        timeout=timeout_ms,
    )


# 简介：输出当前页表格字段、首行、分页控件等调试信息。
# 参数：
# - page: 当前表格页面。
# - selectors: 当前表格相关选择器字典。
# - stage_name: 当前探测阶段名称。
# - page_number: 当前页码。
# 返回值：
# - 无返回值。
# 逻辑：
# - 读取表头、首行和分页控件状态，把页面可见信息打印到终端方便排查。
async def log_table_probe_snapshot(
    page: Page,
    selectors: dict[str, str],
    stage_name: str,
    page_number: int,
) -> None:
    table_container_count = await _safe_count(page, selectors["table_container"])
    scroll_container_count = await _safe_count(page, selectors["table_scroll_container"])
    header_cell_count = await _safe_count(page, selectors["table_header_cells"])
    row_count = await _safe_count(page, selectors["table_row_selector"])
    page_size_trigger_count = await _safe_count(page, selectors["page_size_trigger"])
    page_size_selected_count = await _safe_count(page, selectors["page_size_selected_text"])
    header_preview = await _safe_all_inner_texts(page, selectors["table_header_cells"], limit=10)
    header_title_preview = await _safe_title_attributes(
        page,
        f"{selectors['table_header_cells']} .field-col-header [title]",
        limit=10,
    )
    page_size_preview = await _safe_all_inner_texts(page, selectors["page_size_selected_text"], limit=3)
    first_row_preview = await _safe_first_row_preview(page, selectors, limit=8)
    schema_columns = await extract_schema_labels_from_title_attributes(page, selectors["table_header_cells"])
    mapped_first_row = {
        column: first_row_preview[index] if index < len(first_row_preview) else ""
        for index, column in enumerate(schema_columns)
    }

    logger.info("[folder_table_probe] page={} stage={} url={}", page_number, stage_name, page.url)
    logger.info(
        "[folder_table_probe] page={} stage={} counts: table_container={} scroll_container={} header_cells={} rows={} page_size_trigger={} page_size_selected={}",
        page_number,
        stage_name,
        table_container_count,
        scroll_container_count,
        header_cell_count,
        row_count,
        page_size_trigger_count,
        page_size_selected_count,
    )
    logger.info(
        "[folder_table_probe] page={} stage={} visibility: table_container={} scroll_container={} page_size_trigger={}",
        page_number,
        stage_name,
        await _safe_visible(page, selectors["table_container"]),
        await _safe_visible(page, selectors["table_scroll_container"]),
        await _safe_visible(page, selectors["page_size_trigger"]),
    )
    logger.info("[folder_table_probe] page={} stage={} header_preview={}", page_number, stage_name, header_preview)
    logger.info(
        "[folder_table_probe] page={} stage={} header_title_preview={}",
        page_number,
        stage_name,
        header_title_preview,
    )
    logger.info("[folder_table_probe] page={} stage={} schema_columns={}", page_number, stage_name, schema_columns)
    logger.info("[folder_table_probe] page={} stage={} page_size_preview={}", page_number, stage_name, page_size_preview)
    logger.info("[folder_table_probe] page={} stage={} first_row_preview={}", page_number, stage_name, first_row_preview)
    logger.info("[folder_table_probe] page={} stage={} first_row_mapped={}", page_number, stage_name, mapped_first_row)


def _merge_rows_by_key(
    rows_by_key: dict[str, TableRowRecord],
    new_rows: list[TableRowRecord],
) -> bool:
    changed = False
    for row in new_rows:
        if row.row_key in rows_by_key:
            continue
        rows_by_key[row.row_key] = row
        changed = True
    return changed


# 简介：等待当前页同时出现有效字段和至少一行数据。
# 参数：
# - page: 当前表格页面。
# - selectors: 当前表格选择器字典。
# - wait_seconds: 最长缓冲等待秒数。
# 返回值：
# - 提取成功的 TableSchema。
# 逻辑：
# - 在缓冲窗口内循环检查表头和行，直到两者都可用，否则抛出超时异常。
async def wait_for_probe_ready(
    page: Page,
    selectors: dict[str, str],
    wait_seconds: float,
) -> TableSchema:
    deadline = asyncio.get_running_loop().time() + max(wait_seconds, 0.0)

    while True:
        try:
            schema = await extract_table_schema(page, selectors)
        except ValueError:
            schema = None

        has_rows = await page_has_rows(page, selectors)
        if schema is not None and has_rows:
            return schema

        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError("table probe did not get both schema and rows within buffer wait")

        await page.wait_for_timeout(1000)


# 简介：滚动读取当前页整个表格，直到表格不再产生新行。
# 参数：
# - page: 当前表格页面。
# - target_folder_id: 当前文件夹 ID。
# - page_number: 当前页码。
# - schema: 已提取成功的字段结构。
# - selectors: 当前表格选择器字典。
# - scroll_step_pixels: 每轮滚动像素。
# - scroll_pause_seconds: 每轮滚动后的等待秒数。
# - max_stable_scroll_rounds: 连续多少轮稳定后判定滚到底。
# 返回值：
# - 当前页去重后的全部行记录。
# 逻辑：
# - 一边读取当前视口行，一边滚动内部表格容器，直到滚动状态稳定且没有新行。
async def collect_full_page_rows(
    page: Page,
    target_folder_id: str,
    page_number: int,
    schema: TableSchema,
    selectors: dict[str, str],
    scroll_step_pixels: int,
    scroll_pause_seconds: float,
    max_stable_scroll_rounds: int,
) -> list[TableRowRecord]:
    rows_by_key: dict[str, TableRowRecord] = {}
    previous_snapshot: ScrollSnapshot | None = None
    previous_count = 0
    stable_rounds = 0

    while True:
        visible_rows = await extract_visible_rows(
            page=page,
            folder_id=target_folder_id,
            page_number=page_number,
            schema=schema,
            selectors=selectors,
        )
        changed = _merge_rows_by_key(rows_by_key, visible_rows)
        current_snapshot = await read_scroll_snapshot(page, selectors)

        logger.info(
            "[folder_table_probe] page={} scroll snapshot: top={} height={} client_height={} collected_rows={}",
            page_number,
            current_snapshot.top,
            current_snapshot.height,
            current_snapshot.client_height,
            len(rows_by_key),
        )

        if previous_snapshot is not None:
            if is_scroll_stable(previous_snapshot, current_snapshot) and not changed:
                stable_rounds += 1
            elif len(rows_by_key) == previous_count and not changed:
                stable_rounds += 1
            else:
                stable_rounds = 0

        previous_snapshot = current_snapshot
        previous_count = len(rows_by_key)

        if stable_rounds >= max(max_stable_scroll_rounds, 1):
            break

        await scroll_table_by(page, selectors, scroll_step_pixels)
        await page.wait_for_timeout(scroll_pause_seconds * 1000)

    return list(rows_by_key.values())


# 简介：在独立标签页中完成单个页码的探测和单页采集。
# 参数：
# - context: 浏览器上下文。
# - target: 当前文件夹目标。
# - page_number: 待探测页码。
# - config: 单文件夹探测配置。
# - selectors: 当前表格选择器字典。
# 返回值：
# - PageProbeResult，成功时包含 schema 和 rows，失败时包含错误信息。
# 逻辑：
# - 打开目标页、等待表格壳层、切换页大小、等待字段和行，再滚动采集当前页全部数据。
async def probe_single_page(
    context: BrowserContext,
    target: FolderTarget,
    page_number: int,
    config: FolderTableProbeConfig,
    selectors: dict[str, str],
) -> PageProbeResult:
    probe_url = build_folder_page_url(target.base_url, page_number)
    page = await context.new_page()

    try:
        logger.info("[folder_table_probe] page={} goto table page: {}", page_number, probe_url)
        await page.goto(probe_url, wait_until="domcontentloaded", timeout=config.page_timeout_ms)
        logger.info("[folder_table_probe] page={} loaded: {}", page_number, page.url)

        try:
            await wait_for_table_shell(page, selectors, config.table_ready_timeout_ms)
            logger.info("[folder_table_probe] page={} table shell is visible", page_number)
        except PlaywrightTimeoutError as exc:
            logger.warning("[folder_table_probe] page={} table shell wait timed out: {}", page_number, exc)

        await log_table_probe_snapshot(page, selectors, stage_name="before_page_size", page_number=page_number)
        await ensure_page_size(page, config.page_size, selectors, config.table_ready_timeout_ms)
        logger.info("[folder_table_probe] page={} page size normalized to {}", page_number, config.page_size)

        schema = await wait_for_probe_ready(page, selectors, config.buffer_wait_seconds)
        await log_table_probe_snapshot(page, selectors, stage_name="after_probe_ready", page_number=page_number)

        rows = await collect_full_page_rows(
            page=page,
            target_folder_id=target.folder_id,
            page_number=page_number,
            schema=schema,
            selectors=selectors,
            scroll_step_pixels=config.scroll_step_pixels,
            scroll_pause_seconds=config.scroll_pause_seconds,
            max_stable_scroll_rounds=config.max_stable_scroll_rounds,
        )
        return PageProbeResult(
            page_number=page_number,
            success=True,
            schema=schema,
            rows=rows,
        )
    except Exception as exc:
        logger.exception("[folder_table_probe] page={} failed: {}", page_number, exc)
        return PageProbeResult(
            page_number=page_number,
            success=False,
            schema=None,
            rows=[],
            error_message=str(exc),
        )
    finally:
        await page.close()