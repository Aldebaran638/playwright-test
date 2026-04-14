from __future__ import annotations

import argparse
import asyncio
import copy
import sys
from dataclasses import replace
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.browser.build_context import build_browser_context
from zhy.modules.browser.context_config import BrowserContextUserInput
from zhy.modules.fetch.legal_status_mapping import refresh_legal_status_mapping_file
from zhy.modules.fetch.monthly_patents import run_monthly_patent_fetch
from zhy.modules.persist.json_io import load_json_file_any_utf, save_json
from zhy.modules.persist.page_path import (
    build_monthly_run_summary_path,
    iter_folder_page_files,
    iter_input_page_files,
)
from zhy.modules.report.competitor_patent_report import run_competitor_patent_report
from zhy.modules.transform.competitor_patent_pipeline import (
    build_competitor_patent_report_config,
    build_existing_output_enrichment_config,
    build_monthly_auth_config,
)
from zhy.tasks.competitor_patent_pipeline_task import (
    apply_default_mode,
    build_argument_parser,
    build_config,
    run_existing_output_enrichment,
)


def ensure_month_output_ready(config) -> Path:
    month_root = config.original_output_root.parent
    if not month_root.exists() or not month_root.is_dir():
        raise FileNotFoundError(f"month output root not found: {month_root}")
    return month_root


def load_required_summary(path: Path, *, label: str) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    payload = load_json_file_any_utf(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} is not a JSON object: {path}")
    return payload


def collect_failed_folder_ids(monthly_summary: dict) -> list[str]:
    failed_folder_ids: list[str] = []
    folders = monthly_summary.get("folders", [])
    if not isinstance(folders, list):
        return failed_folder_ids

    for item in folders:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").strip().lower() != "error":
            continue
        folder_id = str(item.get("folder_id") or "").strip()
        if folder_id:
            failed_folder_ids.append(folder_id)
    return sorted(set(failed_folder_ids))


def collect_retry_page_files(config, enrichment_summary: dict, failed_folder_ids: list[str]) -> list[Path]:
    page_file_map: dict[str, Path] = {}

    for folder_id in failed_folder_ids:
        folder_dir = config.original_output_root / f"{config.workspace_space_id}_{folder_id}"
        for page_file in iter_folder_page_files(folder_dir):
            page_file_map[str(page_file)] = page_file

    files = enrichment_summary.get("files", [])
    if isinstance(files, list):
        for item in files:
            if not isinstance(item, dict):
                continue
            input_file = str(item.get("input_file") or "").strip()
            if not input_file:
                continue
            status = str(item.get("status") or "").strip().lower()
            failure_count = item.get("failure_count") or 0
            try:
                failure_count_int = int(failure_count)
            except (TypeError, ValueError):
                failure_count_int = 0
            if status == "error" or failure_count_int > 0:
                path = Path(input_file)
                if path.exists():
                    page_file_map[str(path)] = path

    return sorted(page_file_map.values())


def merge_monthly_summary(original_summary: dict, retry_summary: dict) -> dict:
    merged = copy.deepcopy(original_summary)
    original_folders = merged.get("folders", [])
    retry_folders = retry_summary.get("folders", [])

    if not isinstance(original_folders, list):
        original_folders = []
    if not isinstance(retry_folders, list):
        retry_folders = []

    replacement_by_folder_id = {
        str(item.get("folder_id") or "").strip(): item
        for item in retry_folders
        if isinstance(item, dict) and str(item.get("folder_id") or "").strip()
    }

    merged_folders: list[dict] = []
    consumed: set[str] = set()
    for item in original_folders:
        if not isinstance(item, dict):
            continue
        folder_id = str(item.get("folder_id") or "").strip()
        replacement = replacement_by_folder_id.get(folder_id)
        if replacement is not None:
            merged_folders.append(replacement)
            consumed.add(folder_id)
        else:
            merged_folders.append(item)

    for folder_id, item in replacement_by_folder_id.items():
        if folder_id not in consumed:
            merged_folders.append(item)

    merged["folders"] = merged_folders
    return merged


def build_enrichment_summary_base(config) -> dict:
    return {
        "input_root": str(config.original_output_root),
        "output_root": str(config.enriched_output_root),
        "auth_state_file": str(config.auth_state_file),
        "total_page_files": len(iter_input_page_files(config.original_output_root)),
        "pages_written": 0,
        "pages_skipped": 0,
        "pages_failed": 0,
        "pages_with_row_failures": 0,
        "row_failures": 0,
        "files": [],
    }


def recalculate_enrichment_summary_counts(summary: dict) -> dict:
    files = summary.get("files", [])
    if not isinstance(files, list):
        files = []
        summary["files"] = files

    pages_written = 0
    pages_skipped = 0
    pages_failed = 0
    pages_with_row_failures = 0
    row_failures = 0

    for item in files:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").strip().lower()
        failure_count = item.get("failure_count") or 0
        try:
            failure_count_int = int(failure_count)
        except (TypeError, ValueError):
            failure_count_int = 0

        if status == "ok":
            pages_written += 1
        elif status.startswith("skipped"):
            pages_skipped += 1
        elif status == "error":
            pages_failed += 1

        if failure_count_int > 0:
            pages_with_row_failures += 1
            row_failures += failure_count_int

    summary["pages_written"] = pages_written
    summary["pages_skipped"] = pages_skipped
    summary["pages_failed"] = pages_failed
    summary["pages_with_row_failures"] = pages_with_row_failures
    summary["row_failures"] = row_failures
    return summary


def merge_enrichment_summary(config, original_summary: dict | None, retry_summary: dict) -> dict:
    merged = copy.deepcopy(original_summary) if isinstance(original_summary, dict) else build_enrichment_summary_base(config)
    files = merged.get("files", [])
    retry_files = retry_summary.get("files", [])
    if not isinstance(files, list):
        files = []
    if not isinstance(retry_files, list):
        retry_files = []

    replacement_by_input_file = {
        str(item.get("input_file") or "").strip(): item
        for item in retry_files
        if isinstance(item, dict) and str(item.get("input_file") or "").strip()
    }

    merged_files: list[dict] = []
    consumed: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            continue
        input_file = str(item.get("input_file") or "").strip()
        replacement = replacement_by_input_file.get(input_file)
        if replacement is not None:
            merged_files.append(replacement)
            consumed.add(input_file)
        else:
            merged_files.append(item)

    for input_file, item in replacement_by_input_file.items():
        if input_file not in consumed:
            merged_files.append(item)

    merged["input_root"] = str(config.original_output_root)
    merged["output_root"] = str(config.enriched_output_root)
    merged["auth_state_file"] = str(config.auth_state_file)
    merged["total_page_files"] = len(iter_input_page_files(config.original_output_root))
    merged["files"] = merged_files
    return recalculate_enrichment_summary_counts(merged)


def update_pipeline_summary_with_retry(pipeline_summary_path: Path, retry_record: dict) -> None:
    if pipeline_summary_path.exists():
        payload = load_json_file_any_utf(pipeline_summary_path)
        if not isinstance(payload, dict):
            payload = {}
    else:
        payload = {}

    retry_runs = payload.get("retry_runs", [])
    if not isinstance(retry_runs, list):
        retry_runs = []
    retry_runs.append(retry_record)
    payload["retry_runs"] = retry_runs
    save_json(pipeline_summary_path, payload)


async def retry_failed_monthly_fetch(config, failed_folder_ids: list[str], retry_summary_path: Path) -> tuple[Path, dict]:
    if not failed_folder_ids:
        empty_summary = {
            "month": config.month,
            "space_id": config.workspace_space_id,
            "folder_mapping_file": str(config.folder_mapping_file),
            "company_concurrency": config.patents_company_concurrency,
            "test_folder_ids": [],
            "force_folder_ids": [],
            "folders": [],
        }
        save_json(retry_summary_path, empty_summary)
        return retry_summary_path, empty_summary

    browser_input = BrowserContextUserInput(
        browser_executable_path=config.browser_executable_path,
        user_data_dir=config.user_data_dir,
    )

    retry_config = replace(config, patents_test_folder_ids=list(failed_folder_ids))

    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        managed = await build_browser_context(
            playwright=playwright,
            user_input=browser_input,
            headless=config.headless,
        )
        try:
            return await run_monthly_patent_fetch(
                config=retry_config,
                managed=managed,
                folder_mapping_file=config.folder_mapping_file,
                auth_config=build_monthly_auth_config(retry_config),
                force_folder_ids=list(failed_folder_ids),
                summary_path=retry_summary_path,
            )
        finally:
            await managed.close()


async def retry_failed_enrichment_pages(config, target_page_files: list[Path], retry_summary_path: Path) -> Path:
    retry_config = build_existing_output_enrichment_config(config)
    retry_config.resume = False
    retry_config.target_page_files = list(target_page_files)
    retry_config.summary_path = retry_summary_path
    return await run_existing_output_enrichment(retry_config)


async def run_retry_task(args: argparse.Namespace) -> Path:
    config = build_config(apply_default_mode(args))
    month_root = ensure_month_output_ready(config)

    monthly_summary_path = build_monthly_run_summary_path(config.original_output_root, config.month)
    enrichment_summary_path = config.enriched_output_root / "run_summary.json"
    pipeline_summary_path = config.pipeline_output_dir / f"competitor_patent_pipeline_{config.month}_summary.json"
    retry_summary_path = config.pipeline_output_dir / f"competitor_patent_retry_{config.month}_summary.json"
    monthly_retry_summary_path = config.pipeline_output_dir / f"monthly_patents_retry_{config.month}.json"
    enrichment_retry_summary_path = config.pipeline_output_dir / f"enrichment_retry_{config.month}.json"

    original_monthly_summary = load_required_summary(monthly_summary_path, label="monthly summary")
    original_enrichment_summary = (
        load_required_summary(enrichment_summary_path, label="enrichment summary")
        if enrichment_summary_path.exists()
        else build_enrichment_summary_base(config)
    )

    failed_folder_ids = collect_failed_folder_ids(original_monthly_summary)
    retry_page_files = collect_retry_page_files(config, original_enrichment_summary, failed_folder_ids)

    monthly_retry_result_path, monthly_retry_summary = await retry_failed_monthly_fetch(
        config,
        failed_folder_ids,
        monthly_retry_summary_path,
    )
    merged_monthly_summary = merge_monthly_summary(original_monthly_summary, monthly_retry_summary)
    save_json(monthly_summary_path, merged_monthly_summary)

    if failed_folder_ids:
        retry_page_files = collect_retry_page_files(config, original_enrichment_summary, failed_folder_ids)

    enrichment_retry_result_path = await retry_failed_enrichment_pages(
        config,
        retry_page_files,
        enrichment_retry_summary_path,
    )
    retry_enrichment_summary = load_required_summary(enrichment_retry_result_path, label="enrichment retry summary")
    merged_enrichment_summary = merge_enrichment_summary(config, original_enrichment_summary, retry_enrichment_summary)
    save_json(enrichment_summary_path, merged_enrichment_summary)

    await refresh_legal_status_mapping_file(
        config=config,
        folder_mapping_file=config.folder_mapping_file,
    )

    report_output_path = await asyncio.to_thread(
        run_competitor_patent_report,
        build_competitor_patent_report_config(config),
    )

    retry_summary = {
        "month": config.month,
        "month_root": str(month_root),
        "monthly_summary_path": str(monthly_summary_path),
        "enrichment_summary_path": str(enrichment_summary_path),
        "monthly_retry_summary_path": str(monthly_retry_result_path),
        "enrichment_retry_summary_path": str(enrichment_retry_result_path),
        "report_output_path": str(report_output_path),
        "failed_folder_ids_detected": list(failed_folder_ids),
        "retry_page_files_detected": [str(path) for path in retry_page_files],
        "monthly_retry_folder_count": len(monthly_retry_summary.get("folders", []))
        if isinstance(monthly_retry_summary, dict)
        else 0,
        "enrichment_retry_page_count": len(retry_enrichment_summary.get("files", []))
        if isinstance(retry_enrichment_summary, dict)
        else 0,
        "monthly_retry_error_count": len(
            [
                item
                for item in (monthly_retry_summary.get("folders", []) if isinstance(monthly_retry_summary, dict) else [])
                if isinstance(item, dict) and str(item.get("status") or "").strip().lower() == "error"
            ]
        ),
        "enrichment_retry_page_error_count": len(
            [
                item
                for item in (retry_enrichment_summary.get("files", []) if isinstance(retry_enrichment_summary, dict) else [])
                if isinstance(item, dict) and str(item.get("status") or "").strip().lower() == "error"
            ]
        ),
        "enrichment_retry_row_failure_count": int(retry_enrichment_summary.get("row_failures") or 0)
        if isinstance(retry_enrichment_summary, dict)
        else 0,
    }
    save_json(retry_summary_path, retry_summary)
    update_pipeline_summary_with_retry(pipeline_summary_path, retry_summary)
    logger.info("[competitor_patent_retry_task] summary written: {}", retry_summary_path)
    return retry_summary_path


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    summary_path = asyncio.run(run_retry_task(args))
    logger.info("[competitor_patent_retry_task] done: summary={}", summary_path)


if __name__ == "__main__":
    main()
