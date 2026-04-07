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
from zhy.modules.folder_table.page_url import build_folder_page_url
from zhy.modules.folder_table.table_extract import extract_visible_rows, page_has_rows
from zhy.modules.folder_table.table_schema import extract_table_schema
from zhy.modules.folder_table.table_scroll import (
    ScrollSnapshot,
    is_scroll_stable,
    read_scroll_snapshot,
    scroll_table_by,
)
from zhy.modules.folder_table.writer import append_rows, get_folder_output_dir, write_meta, write_schema


async def wait_for_table_ready(page: Page, selectors: dict[str, str], timeout_ms: int) -> None:
    await page.locator(selectors["table_container"]).wait_for(state="visible", timeout=timeout_ms)
    await page.locator(selectors["table_scroll_container"]).wait_for(
        state="visible",
        timeout=timeout_ms,
    )


async def apply_zoom(page: Page, zoom_ratio: float) -> None:
    zoom_percent = max(int(zoom_ratio * 100), 10)
    await page.evaluate(
        "(zoomPercent) => { document.body.style.zoom = `${zoomPercent}%`; }",
        zoom_percent,
    )


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


async def collect_single_page(
    page: Page,
    target: FolderTarget,
    page_number: int,
    config: FolderTableConfig,
    selectors: dict[str, str],
) -> PageCollectResult:
    page_url = build_folder_page_url(target.base_url, page_number)
    logger.info("[folder_table] start collecting folder {} page {}", target.folder_id, page_number)

    await page.goto(page_url, wait_until="domcontentloaded", timeout=config.page_timeout_ms)
    await wait_for_table_ready(page, selectors, config.table_ready_timeout_ms)
    await ensure_page_size(page, config.expected_page_size, selectors, config.table_ready_timeout_ms)
    await apply_zoom(page, config.zoom_ratio)
    await wait_for_table_ready(page, selectors, config.table_ready_timeout_ms)

    if not await page_has_rows(page, selectors):
        logger.info("[folder_table] folder {} page {} has no rows", target.folder_id, page_number)
        return PageCollectResult(
            folder_id=target.folder_id,
            page_number=page_number,
            schema=None,
            rows=[],
            is_empty=True,
        )

    schema = await extract_table_schema(page, selectors)
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
    return PageCollectResult(
        folder_id=target.folder_id,
        page_number=page_number,
        schema=schema,
        rows=list(rows_by_key.values()),
        is_empty=len(rows_by_key) == 0,
    )


async def _collect_page_with_new_tab(
    context: BrowserContext,
    target: FolderTarget,
    page_number: int,
    config: FolderTableConfig,
    selectors: dict[str, str],
) -> PageCollectResult:
    page = await context.new_page()
    try:
        return await collect_single_page(
            page=page,
            target=target,
            page_number=page_number,
            config=config,
            selectors=selectors,
        )
    finally:
        await page.close()


async def collect_folder_table(
    context: BrowserContext,
    target: FolderTarget,
    config: FolderTableConfig,
    selectors: dict[str, str],
) -> FolderCollectResult:
    output_dir = get_folder_output_dir(config.output_root_dir, target)
    next_page_number = config.start_page
    first_empty_page: int | None = None
    schema: TableSchema | None = None
    all_rows_by_key: dict[str, TableRowRecord] = {}
    collected_page_numbers: list[int] = []

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

            if result.is_empty:
                if first_empty_page is None or page_number < first_empty_page:
                    first_empty_page = page_number
                    logger.info(
                        "[folder_table] folder {} first empty page is {}, stop scheduling larger pages",
                        target.folder_id,
                        page_number,
                    )
            else:
                collected_page_numbers.append(page_number)
                if schema is None and result.schema is not None:
                    schema = result.schema
                    write_schema(output_dir, schema)
                _merge_rows_by_key(all_rows_by_key, result.rows)
                append_rows(output_dir, result.rows)

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

    meta = {
        "space_id": target.space_id,
        "folder_id": target.folder_id,
        "base_url": target.base_url,
        "total_pages_collected": len(collected_page_numbers),
        "total_rows_collected": len(all_rows_by_key),
        "empty_page_number": first_empty_page,
        "collected_page_numbers": sorted(collected_page_numbers),
    }
    if schema is not None:
        meta["schema"] = asdict(schema)
    write_meta(output_dir, meta)

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
