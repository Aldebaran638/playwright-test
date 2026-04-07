#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.korea_law_content_fetcher import (
    DEFAULT_OUTPUT_DIR,
    build_output_filename_from_url,
    fetch_and_save_content_body,
)


DEFAULT_URLS = [
    "https://law.go.kr/LSW/lsLinkProc.do?lsNm=%ED%99%94%EC%9E%A5%ED%92%88%EB%B2%95&chrClsCd=010202&mode=20&ancYnChk=0#",
    "https://law.go.kr/LSW/lsInfoP.do?lsiSeq=279367#0000",
    "https://law.go.kr/LSW/conAdmrulByLsPop.do?&lsiSeq=279367&joNo=0009&joBrNo=00&datClsCd=010102&dguBun=DEG&lnkText=%25EC%2584%25B1%25EB%25B6%2584%25E3%2586%258D%25ED%2595%25A8%25EB%259F%2589%25EC%259D%2584%2520%25EA%25B3%25A0%25EC%258B%259C%25ED%2595%259C&admRulPttninfSeq=17183",
    "https://law.go.kr/LSW/admRulLsInfoP.do?admRulId=36122&efYd=&admRulNm=%ED%99%94%EC%9E%A5%ED%92%88%20%EC%95%88%EC%A0%84%EA%B8%B0%EC%A4%80%20%EB%93%B1%EC%97%90%20%EA%B4%80%ED%95%9C%20%EA%B7%9C%EC%A0%95&lnkYn=Y",
    "https://law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000269816",
    "https://law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000246206",
    "https://law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000187188",
    "https://law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000209268",
    "https://law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000242530",
    "https://law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000257060",
    "https://law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000187191",
    "https://law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000187208",
    "https://law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000192523",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch contentBody text from a list of law.go.kr URLs.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--url", action="append", dest="urls", help="Repeat this option to add multiple URLs.")
    return parser


def run_task(urls: list[str], output_dir: str, timeout: int) -> int:
    if not urls:
        logger.error("[korea_law_batch_fetch_task] No URLs were provided.")
        return 1

    success_count = 0
    failure_count = 0

    for url in urls:
        try:
            logger.info(f"[korea_law_batch_fetch_task] Fetching URL: {url}")
            output_path = fetch_and_save_content_body(
                url=url,
                output_dir=output_dir,
                timeout=timeout,
            )
            logger.info(
                "[korea_law_batch_fetch_task] Saved contentBody text to "
                f"{output_path} (default filename: {build_output_filename_from_url(url)})"
            )
            success_count += 1
        except Exception as exc:
            logger.exception(f"[korea_law_batch_fetch_task] Failed to process URL: {url} | {exc}")
            failure_count += 1

    logger.info(
        "[korea_law_batch_fetch_task] Finished. "
        f"success_count={success_count}, failure_count={failure_count}"
    )
    return 0 if failure_count == 0 else 1


def main() -> None:
    args = build_parser().parse_args()
    urls = args.urls or list(DEFAULT_URLS)
    raise SystemExit(run_task(urls=urls, output_dir=args.output_dir, timeout=args.timeout))


if __name__ == "__main__":
    main()
