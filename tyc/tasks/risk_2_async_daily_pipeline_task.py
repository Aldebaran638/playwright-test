#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
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
from tyc.modules.risk_daily.risk_daily_converter import convert_risk_results_file
from tyc.modules.risk_daily.risk_daily_db_uploader import (
    RiskDailyDbConfig,
    mask_db_config,
    test_db_connection,
    upload_risk_daily_summary_to_db,
)


DEFAULT_COMPANIES_FILE = "tyc/data/input/name_list_test.txt"
DEFAULT_RISK_OUTPUT_FILE = "tyc/data/output/risk_2_async_results.json"
DEFAULT_DAILY_OUTPUT_FILE = "tyc/data/output/risk_2_async_daily_summary.json"
DEFAULT_SEARCH_URL = "https://www.tianyancha.com/risk"
DEFAULT_HOME_URL = "https://www.tianyancha.com/"
DEFAULT_RISK_DATE_START = "2025-10-01"
DEFAULT_RISK_DATE_END = "2026-12-31"
DEFAULT_CONVERT_DATE_START = DEFAULT_RISK_DATE_START
DEFAULT_CONVERT_DATE_END = DEFAULT_RISK_DATE_END
DEFAULT_MAX_QUERY_COUNT = 100
DEFAULT_MAX_PAGE_TURNS = 20
DEFAULT_WORKER_COUNT = 4
DEFAULT_BROWSER_EXECUTABLE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DEFAULT_USER_DATA_DIR = r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2"
DEFAULT_HEADLESS = False
DEFAULT_PAUSE_EVERY_N_COMPANIES = 10
DEFAULT_PAUSE_SECONDS = 5.0
DEFAULT_DB_HOST = "localhost"
DEFAULT_DB_PORT = 3306
DEFAULT_DB_USER = "root"
DEFAULT_DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DEFAULT_DB_NAME = "winkeyai"
DEFAULT_DB_TABLE = "risk_info_test"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="执行异步 risk_2 查询、日汇总转换、数据库上传三步流水线")
    parser.add_argument("--companies-file", default=DEFAULT_COMPANIES_FILE)
    parser.add_argument("--risk-output-file", default=DEFAULT_RISK_OUTPUT_FILE)
    parser.add_argument("--daily-output-file", default=DEFAULT_DAILY_OUTPUT_FILE)
    parser.add_argument("--search-url", default=DEFAULT_SEARCH_URL)
    parser.add_argument("--home-url", default=DEFAULT_HOME_URL)
    parser.add_argument("--risk-date-start", default=DEFAULT_RISK_DATE_START)
    parser.add_argument("--risk-date-end", default=DEFAULT_RISK_DATE_END)
    parser.add_argument("--convert-date-start", default=DEFAULT_CONVERT_DATE_START)
    parser.add_argument("--convert-date-end", default=DEFAULT_CONVERT_DATE_END)
    parser.add_argument("--max-query-count", type=int, default=DEFAULT_MAX_QUERY_COUNT)
    parser.add_argument("--max-page-turns", type=int, default=DEFAULT_MAX_PAGE_TURNS)
    parser.add_argument("--worker-count", type=int, default=DEFAULT_WORKER_COUNT)
    parser.add_argument("--browser-executable-path", default=DEFAULT_BROWSER_EXECUTABLE_PATH)
    parser.add_argument("--user-data-dir", default=DEFAULT_USER_DATA_DIR)
    parser.add_argument("--pause-every-n-companies", type=int, default=DEFAULT_PAUSE_EVERY_N_COMPANIES)
    parser.add_argument("--pause-seconds", type=float, default=DEFAULT_PAUSE_SECONDS)
    parser.add_argument("--headless", action="store_true", default=DEFAULT_HEADLESS)
    parser.add_argument("--db-host", default=DEFAULT_DB_HOST)
    parser.add_argument("--db-port", type=int, default=DEFAULT_DB_PORT)
    parser.add_argument("--db-user", default=DEFAULT_DB_USER)
    parser.add_argument("--db-password", default=DEFAULT_DB_PASSWORD)
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME)
    parser.add_argument("--db-table", default=DEFAULT_DB_TABLE)
    parser.add_argument("--skip-connection-test", action="store_true", default=False)
    return parser


async def run_pipeline(args: argparse.Namespace) -> int:
    companies = load_companies_from_file(args.companies_file)
    if not companies:
        logger.error("[risk_2_async_daily_pipeline_task] 未读取到公司列表，流水线终止")
        return 1

    risk_config = Risk2AsyncConfig(
        search_url=args.search_url,
        home_url=args.home_url,
        date_start=args.risk_date_start,
        date_end=args.risk_date_end,
        max_query_count=args.max_query_count,
        max_page_turns=args.max_page_turns,
        worker_count=args.worker_count,
        browser_executable_path=Path(args.browser_executable_path) if args.browser_executable_path else None,
        user_data_dir=Path(args.user_data_dir) if args.user_data_dir else None,
        headless=args.headless,
        pause_every_n_companies=args.pause_every_n_companies,
        pause_seconds=args.pause_seconds,
    )
    db_config = RiskDailyDbConfig(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        table=args.db_table,
    )

    logger.info("[risk_2_async_daily_pipeline_task] 第一步：执行异步 risk_2 抓取")
    results, failed_companies = await process_risk_2_async(companies, config=risk_config)
    save_risk_results(
        args.risk_output_file,
        results,
        failed_companies,
        date_start=risk_config.date_start,
        date_end=risk_config.date_end,
        worker_count=risk_config.worker_count,
    )

    logger.info("[risk_2_async_daily_pipeline_task] 第二步：执行按日汇总转换")
    converted_records = convert_risk_results_file(
        args.risk_output_file,
        args.daily_output_file,
        start_date=args.convert_date_start,
        end_date=args.convert_date_end,
    )
    logger.info(f"[risk_2_async_daily_pipeline_task] 转换完成，记录数: {len(converted_records)}")

    logger.info(f"[risk_2_async_daily_pipeline_task] 第三步：执行数据库上传，配置: {mask_db_config(db_config)}")
    if not args.skip_connection_test and not test_db_connection(db_config):
        logger.error("[risk_2_async_daily_pipeline_task] 数据库连接测试失败，流水线终止")
        return 1

    if not upload_risk_daily_summary_to_db(args.daily_output_file, db_config):
        logger.error("[risk_2_async_daily_pipeline_task] 数据库上传失败")
        return 1

    logger.info(
        f"[risk_2_async_daily_pipeline_task] 流水线完成，成功公司数: {len(results)}，失败公司数: {len(failed_companies)}"
    )
    return 0


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run_pipeline(args)))


if __name__ == "__main__":
    main()