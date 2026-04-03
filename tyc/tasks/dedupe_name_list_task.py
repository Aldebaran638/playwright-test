#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_INPUT_FILE = "tyc/data/input/name_list.txt"
DEFAULT_OUTPUT_FILE = "tyc/data/input/name_list_unique.txt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="对公司名单文件去重，会新建去重后的文件")
    parser.add_argument("--input-file", default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output-file", default=DEFAULT_OUTPUT_FILE)
    return parser


def dedupe_name_list(input_file: str | Path, output_file: str | Path) -> tuple[int, int, int]:
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")

    lines = input_path.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    unique_names: list[str] = []
    skipped_blank = 0

    for raw_line in lines:
        company_name = raw_line.strip()
        if not company_name:
            skipped_blank += 1
            continue
        if company_name in seen:
            continue
        seen.add(company_name)
        unique_names.append(company_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(unique_names) + "\n", encoding="utf-8")
    return len(lines), len(unique_names), skipped_blank


def main() -> None:
    args = build_parser().parse_args()
    original_count, unique_count, skipped_blank = dedupe_name_list(args.input_file, args.output_file)
    logger.info(
        f"[dedupe_name_list_task] 去重完成，输入行数: {original_count}，输出行数: {unique_count}，"
        f"移除重复/空白行数: {original_count - unique_count}，其中空白行数: {skipped_blank}"
    )


if __name__ == "__main__":
    main()