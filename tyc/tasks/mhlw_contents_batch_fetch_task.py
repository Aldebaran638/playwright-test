#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.mhlw_contents_fetcher import (
    DEFAULT_OUTPUT_DIR,
    build_output_filename_from_url,
    fetch_and_save_contents,
)


DEFAULT_URLS = [
    "https://www.mhlw.go.jp/web/t_doc?dataId=81004000&dataType=0",
    "https://www.mhlw.go.jp/web/t_doc?dataId=81005000&dataType=0",
    "https://www.mhlw.go.jp/web/t_doc?dataId=81aa6966&dataType=0",
    "https://www.mhlw.go.jp/web/t_doc?dataId=81006000&dataType=0",
    "https://www.mhlw.go.jp/web/t_doc?dataId=00ta7225&dataType=1",
    "https://www.mhlw.go.jp/web/t_doc?dataId=81aa6392&dataType=0",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch contents text from a list of mhlw.go.jp URLs.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--url", action="append", dest="urls", help="Repeat this option to add multiple URLs.")
    return parser


def run_task(urls: list[str], output_dir: str, timeout: int) -> int:
    if not urls:
        logger.error("[mhlw_contents_batch_fetch_task] No URLs were provided.")
        return 1

    success_count = 0
    failure_count = 0

    for url in urls:
        try:
            logger.info(f"[mhlw_contents_batch_fetch_task] Fetching URL: {url}")
            output_path = fetch_and_save_contents(
                url=url,
                output_dir=output_dir,
                timeout=timeout,
            )
            logger.info(
                "[mhlw_contents_batch_fetch_task] Saved contents text to "
                f"{output_path} (default filename: {build_output_filename_from_url(url)})"
            )
            success_count += 1
        except Exception as exc:
            logger.exception(f"[mhlw_contents_batch_fetch_task] Failed to process URL: {url} | {exc}")
            failure_count += 1

    logger.info(
        "[mhlw_contents_batch_fetch_task] Finished. "
        f"success_count={success_count}, failure_count={failure_count}"
    )
    return 0 if failure_count == 0 else 1


def main() -> None:
    args = build_parser().parse_args()
    urls = args.urls or list(DEFAULT_URLS)
    raise SystemExit(run_task(urls=urls, output_dir=args.output_dir, timeout=args.timeout))


if __name__ == "__main__":
    main()
