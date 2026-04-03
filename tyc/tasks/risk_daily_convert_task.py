#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_daily.risk_daily_converter import convert_risk_results_file


DEFAULT_INPUT_FILE = "tyc/data/output/risk_2_async_results.json"
DEFAULT_OUTPUT_FILE = "tyc/data/output/risk_2_async_daily_summary.json"
DEFAULT_START_DATE = "2026-03-26"
DEFAULT_END_DATE = "2026-04-02"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="执行 risk_daily 日汇总转换任务")
    parser.add_argument("--input-file", default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output-file", default=DEFAULT_OUTPUT_FILE)
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    return parser


def main() -> None:
    args = build_parser().parse_args()

    logger.info(
        f"[risk_daily_convert_task] 开始转换，输入文件: {args.input_file}, "
        f"start_date={args.start_date}, end_date={args.end_date}"
    )

    output = convert_risk_results_file(
        args.input_file,
        args.output_file,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    logger.info(f"[risk_daily_convert_task] 转换完成，记录数: {len(output)}")


if __name__ == "__main__":
    main()
