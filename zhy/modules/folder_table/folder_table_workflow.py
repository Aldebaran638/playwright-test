import asyncio
from dataclasses import asdict

from loguru import logger
from playwright.async_api import BrowserContext, Page

from zhy.modules.folder_table.models import (
    FolderCollectResult,
    FolderTableConfig,
    FolderTarget,
    PageCollectResult,
    TableRowRecord,
    TableSchema,
)
from zhy.modules.folder_table.page_size import ensure_page_size
from zhy.modules.folder_table.page_url import build_folder_page_url, extract_folder_page_number
from zhy.modules.folder_table.table_extract import extract_visible_rows, normalize_cell_text, page_has_rows
from zhy.modules.folder_table.table_schema import extract_table_schema
from zhy.modules.folder_table.table_scroll import (
    ScrollSnapshot,
    is_scroll_stable,
    read_scroll_snapshot,
    scroll_table_by,
)
from zhy.modules.folder_table.writer import append_debug, append_rows, get_folder_output_dir, write_meta, write_schema
from zhy.modules.folder_table.writer import append_failure


MAX_FAILED_PAGES_WITHOUT_SUCCESS = 5


async def _safe_locator_count(page: Page, selector: str) -> int:
    try:
        return await page.locator(selector).count()
    except Exception:
        return -1


async def _safe_all_inner_texts(page: Page, selector: str, limit: int) -> list[str]:
    try:
        values = await page.locator(selector).all_inner_texts()
    except Exception:
        return []

    cleaned: list[str] = []
    for value in values:
        normalized = normalize_cell_text(value)
        if not normalized:
            continue
        cleaned.append(normalized)
        if len(cleaned) >= limit:
            break
    return cleaned


async def _safe_row_preview(page: Page, selectors: dict[str, str], limit: int) -> list[str]:
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


async def _build_page_debug_payload(
    page: Page,
    target: FolderTarget,
    page_number: int,
    selectors: dict[str, str],
    status: str,
    error_message: str | None = None,
    schema: TableSchema | None = None,
    rows: list[TableRowRecord] | None = None,
) -> dict:
    header_texts = await _safe_all_inner_texts(page, selectors["table_header_cells"], limit=10)
    first_row_preview = await _safe_row_preview(page, selectors, limit=8)
    selected_page_size_texts = await _safe_all_inner_texts(page, selectors["page_size_selected_text"], limit=3)
    actual_page_number = extract_folder_page_number(page.url)
    row_count = await _safe_locator_count(page, selectors["table_row_selector"])

    return {
        "folder_id": target.folder_id,
        "requested_page_number": page_number,
        "actual_page_number": actual_page_number,
        "status": status,
        "current_url": page.url,
        "error_message": error_message,
        "table_container_count": await _safe_locator_count(page, selectors["table_container"]),
        "scroll_container_count": await _safe_locator_count(page, selectors["table_scroll_container"]),
        "header_cell_count": await _safe_locator_count(page, selectors["table_header_cells"]),
        "header_text_preview": header_texts,
        "schema_columns": list(schema.columns) if schema is not None else [],
        "row_count": row_count,
        "first_row_preview": first_row_preview,
        "selected_page_size_preview": selected_page_size_texts,
        "extracted_row_count": len(rows or []),
        "extracted_row_key_preview": [row.row_key for row in (rows or [])[:3]],
    }


async def wait_for_table_ready(page: Page, selectors: dict[str, str], timeout_ms: int) -> None:
    # 表格主容器和内部滚动容器都出现后，才允许继续后续抓取步骤。
    await page.locator(selectors["table_container"]).wait_for(state="visible", timeout=timeout_ms)
    await page.locator(selectors["table_scroll_container"]).wait_for(
        state="visible",
        timeout=timeout_ms,
    )


async def apply_zoom(page: Page, zoom_ratio: float) -> None:
    # 页面缩放用于扩大同屏可见行数，降低单页滚动次数。
    zoom_percent = max(int(zoom_ratio * 100), 10)
    await page.evaluate(
        "(zoomPercent) => { document.body.style.zoom = `${zoomPercent}%`; }",
        zoom_percent,
    )


def _merge_rows_by_key(
    rows_by_key: dict[str, TableRowRecord],
    new_rows: list[TableRowRecord],
) -> bool:
    # 单页内用行主键去重，避免虚拟滚动导致重复收集同一条记录。
    changed = False
    for row in new_rows:
        if row.row_key in rows_by_key:
            continue
        rows_by_key[row.row_key] = row
        changed = True
    return changed


def _collect_new_rows_by_key(
    rows_by_key: dict[str, TableRowRecord],
    new_rows: list[TableRowRecord],
) -> list[TableRowRecord]:
    # 仅返回本轮真正新增的记录，避免重复页或重试页重复写盘。
    added_rows: list[TableRowRecord] = []
    for row in new_rows:
        if row.row_key in rows_by_key:
            continue
        rows_by_key[row.row_key] = row
        added_rows.append(row)
    return added_rows


def _resolve_redirected_page_number(requested_page_number: int, current_url: str) -> int | None:
    # 请求页码和最终落地页码不一致时，通常说明站点把越界页重定向到了已有页。
    actual_page_number = extract_folder_page_number(current_url)
    if actual_page_number is None or actual_page_number == requested_page_number:
        return None
    return actual_page_number


def _build_running_meta(
    target: FolderTarget,
    schema: TableSchema | None,
    collected_page_numbers: list[int],
    all_rows_by_key: dict[str, TableRowRecord],
    first_empty_page: int | None,
    failed_pages: list[int],
    failure_details: dict[int, str],
    status: str,
) -> dict:
    meta = {
        "space_id": target.space_id,
        "folder_id": target.folder_id,
        "base_url": target.base_url,
        "status": status,
        "total_pages_collected": len(collected_page_numbers),
        "total_rows_collected": len(all_rows_by_key),
        "empty_page_number": first_empty_page,
        "collected_page_numbers": sorted(collected_page_numbers),
        "failed_page_numbers": sorted(failed_pages),
        "failure_details": {
            str(page_number): message
            for page_number, message in sorted(failure_details.items())
        },
    }
    if schema is not None:
        meta["schema"] = asdict(schema)
    return meta


async def _wait_for_non_empty_schema(
    page: Page,
    selectors: dict[str, str],
    wait_seconds: float,
) -> TableSchema | None:
    # 页面骨架出现后再给一段缓冲时间，等待真实表头异步填充完成。
    deadline = asyncio.get_running_loop().time() + max(wait_seconds, 0.0)
    while True:
        try:
            schema = await extract_table_schema(page, selectors)
            if schema.columns:
                return schema
        except ValueError:
            pass

        if asyncio.get_running_loop().time() >= deadline:
            return None
        await page.wait_for_timeout(1000)


async def _wait_for_rows_or_schema(
    page: Page,
    selectors: dict[str, str],
    wait_seconds: float,
) -> tuple[bool, TableSchema | None]:
    # 给“短暂空表”留出缓冲期；缓冲后仍无表头且无数据，才判定为空页。
    deadline = asyncio.get_running_loop().time() + max(wait_seconds, 0.0)
    last_schema: TableSchema | None = None

    while True:
        has_rows = await page_has_rows(page, selectors)
        try:
            last_schema = await extract_table_schema(page, selectors)
        except ValueError:
            last_schema = None

        if has_rows or (last_schema is not None and last_schema.columns):
            return has_rows, last_schema

        if asyncio.get_running_loop().time() >= deadline:
            return False, None
        await page.wait_for_timeout(1000)


async def collect_single_page(
    page: Page,
    target: FolderTarget,
    page_number: int,
    config: FolderTableConfig,
    selectors: dict[str, str],
) -> PageCollectResult:
    # 负责抓取单页数据: 打开分页 URL, 统一页大小, 等待表头/数据稳定, 滚动到底并提取行。
    page_url = build_folder_page_url(target.base_url, page_number)
    logger.info("[folder_table] start collecting folder {} page {}", target.folder_id, page_number)

    try:
        await page.goto(page_url, wait_until="domcontentloaded", timeout=config.page_timeout_ms)
        redirected_page_number = _resolve_redirected_page_number(page_number, page.url)
        if redirected_page_number is not None:
            debug_payload = await _build_page_debug_payload(
                page=page,
                target=target,
                page_number=page_number,
                selectors=selectors,
                status="empty",
                error_message=(
                    f"requested page {page_number} redirected to page {redirected_page_number}"
                ),
            )
            logger.info(
                "[folder_table] folder {} page {} redirected to page {}, treat as terminal empty page",
                target.folder_id,
                page_number,
                redirected_page_number,
            )
            return PageCollectResult(
                folder_id=target.folder_id,
                page_number=page_number,
                status="empty",
                schema=None,
                rows=[],
                is_empty=True,
                error_message=(
                    f"requested page {page_number} redirected to page {redirected_page_number}"
                ),
                debug_payload=debug_payload,
            )

        await wait_for_table_ready(page, selectors, config.table_ready_timeout_ms)
        await ensure_page_size(page, config.expected_page_size, selectors, config.table_ready_timeout_ms)
        await apply_zoom(page, config.zoom_ratio)
        await wait_for_table_ready(page, selectors, config.table_ready_timeout_ms)

        has_rows, buffered_schema = await _wait_for_rows_or_schema(
            page=page,
            selectors=selectors,
            wait_seconds=config.empty_page_wait_seconds,
        )
        if not has_rows and buffered_schema is None:
            debug_payload = await _build_page_debug_payload(
                page=page,
                target=target,
                page_number=page_number,
                selectors=selectors,
                status="empty",
            )
            logger.info("[folder_table] folder {} page {} resolved as empty", target.folder_id, page_number)
            return PageCollectResult(
                folder_id=target.folder_id,
                page_number=page_number,
                status="empty",
                schema=None,
                rows=[],
                is_empty=True,
                debug_payload=debug_payload,
            )

        schema = buffered_schema or await _wait_for_non_empty_schema(
            page=page,
            selectors=selectors,
            wait_seconds=config.empty_page_wait_seconds,
        )
        if schema is None:
            debug_payload = await _build_page_debug_payload(
                page=page,
                target=target,
                page_number=page_number,
                selectors=selectors,
                status="error",
                error_message="failed to extract table schema after buffer wait",
            )
            return PageCollectResult(
                folder_id=target.folder_id,
                page_number=page_number,
                status="error",
                schema=None,
                rows=[],
                is_empty=False,
                error_message="failed to extract table schema after buffer wait",
                debug_payload=debug_payload,
            )

        rows_by_key: dict[str, TableRowRecord] = {}
        stable_rounds = 0
        previous_snapshot: ScrollSnapshot | None = None
        previous_count = 0

        while True:
            visible_rows = await extract_visible_rows(
                page,
                folder_id=target.folder_id,
                page_number=page_number,
                schema=schema,
                selectors=selectors,
            )
            changed = _merge_rows_by_key(rows_by_key, visible_rows)

            current_snapshot = await read_scroll_snapshot(page, selectors)
            if previous_snapshot is not None:
                if is_scroll_stable(previous_snapshot, current_snapshot) and not changed:
                    stable_rounds += 1
                elif len(rows_by_key) == previous_count and not changed:
                    stable_rounds += 1
                else:
                    stable_rounds = 0

            previous_snapshot = current_snapshot
            previous_count = len(rows_by_key)

            if stable_rounds >= config.max_stable_scroll_rounds:
                break

            await scroll_table_by(page, selectors, config.scroll_step_pixels)
            await page.wait_for_timeout(config.scroll_pause_seconds * 1000)

        logger.info(
            "[folder_table] folder {} page {} finished with {} rows",
            target.folder_id,
            page_number,
            len(rows_by_key),
        )
        debug_payload = await _build_page_debug_payload(
            page=page,
            target=target,
            page_number=page_number,
            selectors=selectors,
            status="success",
            schema=schema,
            rows=list(rows_by_key.values()),
        )
        logger.info(
            "[folder_table] folder {} page {} debug summary: headers={} row_count={} first_row={}",
            target.folder_id,
            page_number,
            debug_payload["header_text_preview"],
            debug_payload["row_count"],
            debug_payload["first_row_preview"],
        )
        return PageCollectResult(
            folder_id=target.folder_id,
            page_number=page_number,
            status="success",
            schema=schema,
            rows=list(rows_by_key.values()),
            is_empty=len(rows_by_key) == 0,
            debug_payload=debug_payload,
        )
    except Exception as exc:
        debug_payload = await _build_page_debug_payload(
            page=page,
            target=target,
            page_number=page_number,
            selectors=selectors,
            status="error",
            error_message=str(exc),
        )
        logger.exception(
            "[folder_table] folder {} page {} failed: {}",
            target.folder_id,
            page_number,
            exc,
        )
        return PageCollectResult(
            folder_id=target.folder_id,
            page_number=page_number,
            status="error",
            schema=None,
            rows=[],
            is_empty=False,
            error_message=str(exc),
            debug_payload=debug_payload,
        )


async def _collect_page_with_new_tab(
    context: BrowserContext,
    target: FolderTarget,
    page_number: int,
    config: FolderTableConfig,
    selectors: dict[str, str],
) -> PageCollectResult:
    # 每个页码都在独立标签页中抓取，并对短时超时类问题做有限次重试。
    last_error_message: str | None = None

    for attempt in range(1, max(config.retry_count, 1) + 1):
        page = await context.new_page()
        try:
            result = await collect_single_page(
                page=page,
                target=target,
                page_number=page_number,
                config=config,
                selectors=selectors,
            )
            if result.status != "error":
                return result

            last_error_message = result.error_message
            if attempt < config.retry_count:
                logger.warning(
                    "[folder_table] folder {} page {} attempt {}/{} failed, retry in {}s: {}",
                    target.folder_id,
                    page_number,
                    attempt,
                    config.retry_count,
                    config.retry_wait_seconds,
                    last_error_message or "<unknown>",
                )
                await page.wait_for_timeout(config.retry_wait_seconds * 1000)
        finally:
            await page.close()

    logger.error(
        "[folder_table] folder {} page {} failed after {} attempts: {}",
        target.folder_id,
        page_number,
        config.retry_count,
        last_error_message or "<unknown>",
    )

    return PageCollectResult(
        folder_id=target.folder_id,
        page_number=page_number,
        status="error",
        schema=None,
        rows=[],
        is_empty=False,
        error_message=last_error_message or "page collection failed after retries",
    )


async def collect_folder_table(
    context: BrowserContext,
    target: FolderTarget,
    config: FolderTableConfig,
    selectors: dict[str, str],
) -> FolderCollectResult:
    # 负责整个文件夹的分页调度和结果落盘: 并发抓页, 发现空页后停止派发, 最终汇总 meta。
    output_dir = get_folder_output_dir(config.output_root_dir, target)
    next_page_number = config.start_page
    first_empty_page: int | None = None
    schema: TableSchema | None = None
    all_rows_by_key: dict[str, TableRowRecord] = {}
    collected_page_numbers: list[int] = []
    failed_pages: list[int] = []
    failure_details: dict[int, str] = {}
    folder_status = "running"

    write_meta(
        output_dir,
        _build_running_meta(
            target=target,
            schema=schema,
            collected_page_numbers=collected_page_numbers,
            all_rows_by_key=all_rows_by_key,
            first_empty_page=first_empty_page,
            failed_pages=failed_pages,
            failure_details=failure_details,
            status="running",
        ),
    )

    pending_tasks: dict[asyncio.Task[PageCollectResult], int] = {}
    initial_task_count = max(config.concurrency, 1)
    for _ in range(initial_task_count):
        task = asyncio.create_task(
            _collect_page_with_new_tab(
                context=context,
                target=target,
                page_number=next_page_number,
                config=config,
                selectors=selectors,
            )
        )
        pending_tasks[task] = next_page_number
        next_page_number += 1

    while pending_tasks:
        done, _ = await asyncio.wait(
            pending_tasks.keys(),
            return_when=asyncio.FIRST_COMPLETED,
        )

        for finished_task in done:
            page_number = pending_tasks.pop(finished_task)
            result = await finished_task
            append_debug(
                output_dir,
                result.debug_payload
                or {
                    "folder_id": target.folder_id,
                    "requested_page_number": page_number,
                    "status": result.status,
                    "error_message": result.error_message,
                },
            )

            if result.status == "empty":
                if first_empty_page is None or page_number < first_empty_page:
                    first_empty_page = page_number
                    logger.info(
                        "[folder_table] folder {} first empty page is {}, stop scheduling larger pages",
                        target.folder_id,
                        page_number,
                    )
            elif result.status == "success":
                collected_page_numbers.append(page_number)
                if schema is None and result.schema is not None:
                    schema = result.schema
                    write_schema(output_dir, schema)
                new_rows = _collect_new_rows_by_key(all_rows_by_key, result.rows)
                if new_rows:
                    append_rows(output_dir, new_rows)
            else:
                failed_pages.append(page_number)
                failure_message = result.error_message or "<unknown>"
                failure_details[page_number] = failure_message
                append_failure(
                    output_dir,
                    {
                        "folder_id": target.folder_id,
                        "page_number": page_number,
                        "error_message": failure_message,
                    },
                )
                logger.warning(
                    "[folder_table] folder {} page {} failed but will not stop the whole folder: {}",
                    target.folder_id,
                    page_number,
                    failure_message,
                )

                if not collected_page_numbers and len(failed_pages) >= MAX_FAILED_PAGES_WITHOUT_SUCCESS:
                    folder_status = "failed"
                    logger.error(
                        "[folder_table] folder {} aborted after {} failed pages without any successful page",
                        target.folder_id,
                        len(failed_pages),
                    )
                    for pending_task in pending_tasks:
                        pending_task.cancel()
                    pending_tasks.clear()

            write_meta(
                output_dir,
                _build_running_meta(
                    target=target,
                    schema=schema,
                    collected_page_numbers=collected_page_numbers,
                    all_rows_by_key=all_rows_by_key,
                    first_empty_page=first_empty_page,
                    failed_pages=failed_pages,
                    failure_details=failure_details,
                    status=folder_status,
                ),
            )

            if folder_status == "failed":
                break

            if first_empty_page is None or next_page_number < first_empty_page:
                new_task = asyncio.create_task(
                    _collect_page_with_new_tab(
                        context=context,
                        target=target,
                        page_number=next_page_number,
                        config=config,
                        selectors=selectors,
                    )
                )
                pending_tasks[new_task] = next_page_number
                next_page_number += 1

        if folder_status == "failed":
            break

    write_meta(
        output_dir,
        _build_running_meta(
            target=target,
            schema=schema,
            collected_page_numbers=collected_page_numbers,
            all_rows_by_key=all_rows_by_key,
            first_empty_page=first_empty_page,
            failed_pages=failed_pages,
            failure_details=failure_details,
            status="completed" if folder_status != "failed" else "failed",
        ),
    )

    return FolderCollectResult(
        folder_id=target.folder_id,
        space_id=target.space_id,
        schema=schema,
        output_dir=output_dir,
        total_pages_collected=len(collected_page_numbers),
        total_rows_collected=len(all_rows_by_key),
        empty_page_number=first_empty_page,
        collected_page_numbers=sorted(collected_page_numbers),
    )
