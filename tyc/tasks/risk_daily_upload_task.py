#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_daily.risk_daily_db_uploader import (
    RiskDailyDbConfig,
    mask_db_config,
    test_db_connection,
    upload_risk_daily_summary_to_db,
)


DEFAULT_INPUT_FILE = "tyc/data/output/risk_2_results_daily_summary.json"
DEFAULT_DB_HOST = "192.168.2.212"
DEFAULT_DB_PORT = 3306
DEFAULT_DB_USER = "root"
DEFAULT_DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DEFAULT_DB_NAME = "winkeyai"
DEFAULT_DB_TABLE = "risk_info"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="执行 risk_daily 数据库上传任务")
    parser.add_argument("--input-file", default=DEFAULT_INPUT_FILE)
    parser.add_argument("--db-host", default=DEFAULT_DB_HOST)
    parser.add_argument("--db-port", type=int, default=DEFAULT_DB_PORT)
    parser.add_argument("--db-user", default=DEFAULT_DB_USER)
    parser.add_argument("--db-password", default=DEFAULT_DB_PASSWORD)
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME)
    parser.add_argument("--db-table", default=DEFAULT_DB_TABLE)
    parser.add_argument("--skip-connection-test", action="store_true", default=False)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db_config = RiskDailyDbConfig(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        table=args.db_table,
    )

    logger.info(f"[risk_daily_upload_task] 开始上传按日聚合文件: {args.input_file}")
    logger.info(f"[risk_daily_upload_task] 数据库配置: {mask_db_config(db_config)}")

    if not args.skip_connection_test and not test_db_connection(db_config):
        logger.error("[risk_daily_upload_task] 数据库连接测试失败，任务终止")
        raise SystemExit(1)

    success = upload_risk_daily_summary_to_db(args.input_file, db_config)

    if success:
        logger.info("[risk_daily_upload_task] 上传完成：数据已写入数据库")
    else:
        logger.error("[risk_daily_upload_task] 上传失败：请检查日志和数据库连接配置")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
