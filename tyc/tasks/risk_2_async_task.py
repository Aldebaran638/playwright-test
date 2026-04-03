#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2_async.main import (
    Risk2AsyncConfig,
    load_companies_from_file,
    process_risk_2_async,
    save_risk_results,
)


DEFAULT_COMPANIES_FILE = "tyc/data/input/name_list_test.txt"
DEFAULT_OUTPUT_FILE = "tyc/data/output/risk_2_async_results.json"
DEFAULT_SEARCH_URL = "https://www.tianyancha.com/risk"
DEFAULT_HOME_URL = "https://www.tianyancha.com/"
DEFAULT_DATE_START = "2020-01-01"
DEFAULT_DATE_END = "2026-12-31"
DEFAULT_MAX_QUERY_COUNT = 100
DEFAULT_MAX_PAGE_TURNS = 20
DEFAULT_WORKER_COUNT = 2
DEFAULT_BROWSER_EXECUTABLE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DEFAULT_USER_DATA_DIR = r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2"
DEFAULT_HEADLESS = False
DEFAULT_PAUSE_EVERY_N_COMPANIES = 10
DEFAULT_PAUSE_SECONDS = 5.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="执行天眼查 risk_2 异步抓取任务")
    parser.add_argument("--companies-file", default=DEFAULT_COMPANIES_FILE)
    parser.add_argument("--output-file", default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--search-url", default=DEFAULT_SEARCH_URL)
    parser.add_argument("--home-url", default=DEFAULT_HOME_URL)
    parser.add_argument("--date-start", default=DEFAULT_DATE_START)
    parser.add_argument("--date-end", default=DEFAULT_DATE_END)
    parser.add_argument("--max-query-count", type=int, default=DEFAULT_MAX_QUERY_COUNT)
    parser.add_argument("--max-page-turns", type=int, default=DEFAULT_MAX_PAGE_TURNS)
    parser.add_argument("--worker-count", type=int, default=DEFAULT_WORKER_COUNT)
    parser.add_argument("--browser-executable-path", default=DEFAULT_BROWSER_EXECUTABLE_PATH)
    parser.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--pause-every-n-companies", type=int, default=DEFAULT_PAUSE_EVERY_N_COMPANIES)
    parser.add_argument("--pause-seconds", type=float, default=DEFAULT_PAUSE_SECONDS)
    parser.add_argument("--headless", action="store_true", default=DEFAULT_HEADLESS)
    return parser


async def run_task(args: argparse.Namespace) -> int:
    companies = load_companies_from_file(args.companies_file)
    if not companies:
        logger.error("[risk_2_async_task] 未读取到公司列表，任务终止")
        return 1

    config = Risk2AsyncConfig(
        search_url=args.search_url,
        home_url=args.home_url,
        date_start=args.date_start,
        date_end=args.date_end,
        max_query_count=args.max_query_count,
        max_page_turns=args.max_page_turns,
        worker_count=args.worker_count,
        browser_executable_path=Path(args.browser_executable_path) if args.browser_executable_path else None,
        user_data_dir=Path(args.user_data_dir) if args.user_data_dir else None,
        headless=args.headless,
        pause_every_n_companies=args.pause_every_n_companies,
        pause_seconds=args.pause_seconds,
    )

    results, failed_companies = await process_risk_2_async(companies, config=config)
    save_risk_results(
        args.output_file,
        results,
        failed_companies,
        date_start=config.date_start,
        date_end=config.date_end,
        worker_count=config.worker_count,
    )

    logger.info(
        f"[risk_2_async_task] 任务完成，成功公司数: {len(results)}，失败公司数: {len(failed_companies)}"
    )
    return 0


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run_task(args)))


if __name__ == "__main__":
    main()