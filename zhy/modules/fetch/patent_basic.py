from __future__ import annotations

import asyncio
import copy
import re

import requests
from loguru import logger

from zhy.modules.common.types.folder_patents import AuthRefreshRequiredError, TransientRequestError
from zhy.modules.fetch.folder_patents_abstract import (
    build_abstract_request_body,
    fetch_single_patent_abstract,
)


HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def build_basic_request_url(*, patent_id: str) -> str:
    return f"https://search-service.zhihuiya.com/core-search-api/search/patent/id/{patent_id}/basic?highlight=true"


def build_basic_request_body(*, template: dict, patent_id: str) -> dict:
    body = copy.deepcopy(template)
    body["patent_id"] = patent_id
    return body


def strip_html_text(value: str) -> str:
    without_tags = HTML_TAG_PATTERN.sub(" ", value)
    return " ".join(without_tags.replace("&nbsp;", " ").split())


def extract_abstract_from_basic_payload(payload: dict) -> str:
    data = payload.get("data")
    if not isinstance(data, dict):
        return ""

    abst = data.get("ABST")
    if isinstance(abst, dict):
        for preferred_key in ("CN", "EN"):
            preferred_value = abst.get(preferred_key)
            if isinstance(preferred_value, str) and preferred_value.strip():
                return strip_html_text(preferred_value)
        for value in abst.values():
            if isinstance(value, str) and value.strip():
                return strip_html_text(value)

    if isinstance(abst, str) and abst.strip():
        return strip_html_text(abst)
    return ""


def detect_text_language(value: str) -> str:
    text = str(value or "")
    if not text.strip():
        return ""
    has_hiragana = bool(re.search(r"[\u3040-\u309f]", text))
    has_katakana = bool(re.search(r"[\u30a0-\u30ff\u31f0-\u31ff]", text))
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", text))
    has_latin = bool(re.search(r"[A-Za-z]", text))
    if has_hiragana or has_katakana:
        return "ja"
    if has_cjk and not has_latin:
        return "zh"
    if has_latin and not has_cjk:
        return "en"
    if has_cjk and has_latin:
        return "mixed"
    return "other"


def post_basic_sync(
    *,
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
) -> dict:
    response = requests.post(url, headers=headers, json=body, timeout=timeout_seconds, proxies=proxies)
    if response.status_code == 401:
        raise AuthRefreshRequiredError("received 401 from basic API")
    if response.status_code == 429 or 500 <= response.status_code < 600:
        raise TransientRequestError(f"transient status code: {response.status_code}")
    response.raise_for_status()
    return response.json()


async def fetch_patent_basic_payload(
    *,
    patent_id: str,
    headers: dict[str, str],
    body_template: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
    scheduler,
    retry_count: int,
    retry_backoff_base_seconds: float,
) -> dict:
    url = build_basic_request_url(patent_id=patent_id)
    body = build_basic_request_body(template=body_template, patent_id=patent_id)
    attempts = max(retry_count, 1)

    for attempt_index in range(attempts):
        try:
            async with scheduler:
                return await asyncio.to_thread(
                    post_basic_sync,
                    url=url,
                    headers=headers,
                    body=body,
                    timeout_seconds=timeout_seconds,
                    proxies=proxies,
                )
        except AuthRefreshRequiredError:
            raise
        except (TransientRequestError, requests.Timeout, requests.ConnectionError) as exc:
            if attempt_index >= attempts - 1:
                raise
            backoff_seconds = retry_backoff_base_seconds * (2 ** attempt_index)
            logger.warning(
                "[patent_basic] retry basic payload patent_id={} attempt={}/{} error={} sleep={}s",
                patent_id,
                attempt_index + 1,
                attempts,
                exc,
                backoff_seconds,
            )
            await asyncio.sleep(backoff_seconds)
        except requests.HTTPError:
            raise

    raise RuntimeError(f"basic payload fetch exhausted for patent_id={patent_id}")


async def build_page_supplement_payload(
    *,
    page_payload: dict,
    page_file,
    space_id: str,
    folder_id: str,
    abstract_headers: dict[str, str],
    basic_headers: dict[str, str],
    abstract_request_url: str,
    abstract_request_template: dict,
    basic_request_body_template: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
    scheduler,
    retry_count: int,
    retry_backoff_base_seconds: float,
    request_concurrency: int,
) -> dict:
    rows = page_payload.get("data", {}).get("patents_data", [])
    if not isinstance(rows, list):
        raise ValueError("data.patents_data is not a list")

    async def process_row(row_index: int, row: object) -> tuple[int, dict, list[dict]]:
        row_failures: list[dict] = []
        if not isinstance(row, dict):
            return row_index, {"PATENT_ID": "", "PN": "", "ABST": ""}, [
                {"row_index": row_index, "patent_id": "", "reason": "row_not_object"}
            ]

        patent_id = str(row.get("PATENT_ID") or "").strip()
        pn = str(row.get("PN") or "").strip()
        record = {
            "PATENT_ID": patent_id,
            "PN": pn,
            "ABST": "",
            "ABST_ORIGINAL": "",
            "ABST_LANGUAGE": "",
            "ABST_TRANSLATED": False,
        }

        if not patent_id:
            row_failures.append({"row_index": row_index, "patent_id": "", "reason": "missing_patent_id"})
            return row_index, record, row_failures

        try:
            abstract_body = build_abstract_request_body(
                template=abstract_request_template,
                patent_id=patent_id,
                folder_id=folder_id,
                workspace_id=space_id,
            )
            basic_payload, translated_text = await asyncio.gather(
                fetch_patent_basic_payload(
                    patent_id=patent_id,
                    headers=basic_headers,
                    body_template=basic_request_body_template,
                    timeout_seconds=timeout_seconds,
                    proxies=proxies,
                    scheduler=scheduler,
                    retry_count=retry_count,
                    retry_backoff_base_seconds=retry_backoff_base_seconds,
                ),
                fetch_single_patent_abstract(
                    patent_id=patent_id,
                    url=abstract_request_url,
                    headers=abstract_headers,
                    body=abstract_body,
                    timeout_seconds=timeout_seconds,
                    proxies=proxies,
                    scheduler=scheduler,
                    retry_count=retry_count,
                    retry_backoff_base_seconds=retry_backoff_base_seconds,
                ),
            )
            original_text = extract_abstract_from_basic_payload(basic_payload)
            record["ABST_ORIGINAL"] = original_text
            record["ABST_LANGUAGE"] = detect_text_language(original_text)
            record["ABST"] = translated_text or original_text
            record["ABST_TRANSLATED"] = bool(translated_text and translated_text != original_text)
        except AuthRefreshRequiredError:
            raise
        except Exception as exc:
            row_failures.append({"row_index": row_index, "patent_id": patent_id, "reason": f"basic: {exc}"})

        if not record["ABST"] and record["ABST_ORIGINAL"]:
            record["ABST"] = record["ABST_ORIGINAL"]
        if not record["ABST_LANGUAGE"]:
            record["ABST_LANGUAGE"] = detect_text_language(record["ABST_ORIGINAL"])

        return row_index, record, row_failures

    worker_limit = max(int(request_concurrency), 1)
    semaphore = asyncio.Semaphore(worker_limit)

    async def guarded_process_row(row_index: int, row: object) -> tuple[int, dict, list[dict]]:
        async with semaphore:
            return await process_row(row_index, row)

    results = await asyncio.gather(
        *(guarded_process_row(index, row) for index, row in enumerate(rows))
    )
    results_sorted = sorted(results, key=lambda item: item[0])

    records: list[dict] = [record for _, record, _ in results_sorted]
    failures: list[dict] = []
    for _, _, row_failures in results_sorted:
        failures.extend(row_failures)

    return {
        "space_id": space_id,
        "folder_id": folder_id,
        "source_file": str(page_file),
        "record_count": len(records),
        "records": records,
        "failures": failures,
    }
