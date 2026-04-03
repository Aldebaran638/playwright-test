#!/usr/bin/env python3
"""简单运行器：调用 risk_daily_converter.convert_risk_results_file
默认输入：tyc/modules/risk_2/risk_2_results.json
"""
from __future__ import annotations

import argparse
from loguru import logger

import sys
from pathlib import Path

# Ensure project root is on sys.path so imports like `tyc.modules...` work when
# running this script directly from the repository root or via the venv python.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2.risk_daily_converter import convert_risk_results_file


def main() -> None:
    # 硬编码参数：如果需要修改硬编码值，请在此处更改
    INPUT_FILE = "tyc/modules/risk_2/risk_2_results.json"
    OUTPUT_FILE: str | None = None
    START_DATE = "2026-03-26"
    END_DATE = "2026-04-02"

    logger.info(
        f"开始转换（硬编码参数），输入文件: {INPUT_FILE}, start_date={START_DATE}, end_date={END_DATE}"
    )

    output = convert_risk_results_file(
        INPUT_FILE, OUTPUT_FILE, start_date=START_DATE, end_date=END_DATE
    )

    logger.info(f"转换完成，记录数: {len(output)}")


if __name__ == "__main__":
    main()
