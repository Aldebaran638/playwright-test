#!/usr/bin/env python3
"""运行器：调用 risk_daily_db_uploader.upload_risk_daily_summary_to_db
默认使用按日聚合输出文件：tyc/modules/risk_2/risk_2_results_daily_summary.json
"""
from __future__ import annotations

import sys
from pathlib import Path
from loguru import logger

# Ensure project root is on sys.path so imports like `tyc.modules...` work
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2.risk_daily_db_uploader import (
    upload_risk_daily_summary_to_db,
    get_db_config,
)


def main() -> None:
    # 硬编码输入：按日聚合 JSON 文件（由转换器生成）
    INPUT_FILE = "tyc/modules/risk_2/risk_2_results_daily_summary.json"

    logger.info(f"开始上传按日聚合文件: {INPUT_FILE}")

    cfg = get_db_config()
    logger.info(f"数据库配置: host={cfg.get('host')} port={cfg.get('port')} db={cfg.get('database')} table={cfg.get('table')}")

    success = upload_risk_daily_summary_to_db(INPUT_FILE)

    if success:
        logger.info("上传完成：数据已写入数据库")
    else:
        logger.error("上传失败：请检查日志和数据库连接配置")


if __name__ == "__main__":
    main()
