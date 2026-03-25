"""Download products directly from the Mintel product list page."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from loguru import logger
from playwright.sync_api import Page

from getdata1.modules.retry import run_with_timeout_retry


class WaitBeforeAction(Protocol):
    def __call__(self, page: Page, milliseconds: float | None = None) -> None: ...


def download_product_from_list(
    page: Page,
    item_id: str,
    download_dir: Path,
    wait_before_action: WaitBeforeAction,
) -> Path:
    """Download the given product directly from the list page and save it under downloads/."""
    logger.info("开始下载列表项: item_id={item_id}", item_id=item_id)
    download_dir.mkdir(parents=True, exist_ok=True)

    run_with_timeout_retry(
        f"点击列表项下载入口 item_id={item_id}",
        page,
        wait_before_action,
        lambda: page.locator(f"#item_{item_id}").get_by_role("link", name="下载").click(),
    )
    wait_before_action(page)

    def confirm_download():
        with page.expect_download() as download_info:
            page.get_by_role("button", name="下载").click()
        return download_info.value

    download = run_with_timeout_retry(
        f"确认下载 item_id={item_id}",
        page,
        wait_before_action,
        confirm_download,
    )
    target_path = _build_non_conflicting_path(download_dir, download.suggested_filename)
    download.save_as(str(target_path))
    logger.info("下载完成，已保存到: {path}", path=target_path)
    wait_before_action(page)
    return target_path


def _build_non_conflicting_path(download_dir: Path, filename: str) -> Path:
    candidate = download_dir / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1
    while True:
        deduped = download_dir / f"{stem}_{counter}{suffix}"
        if not deduped.exists():
            return deduped
        counter += 1
