from __future__ import annotations

import asyncio
import copy
import re
from collections.abc import Iterable

import requests
from loguru import logger

from zhy.modules.common.types.folder_patents import AuthRefreshRequiredError, TransientRequestError


HTML_TAG_PATTERN = re.compile(r"<[^>]+>")


def build_basic_request_url(*, patent_id: str) -> str:
    """简介：构建单条专利 basic 接口 URL。
    参数：patent_id 为专利唯一标识。
    返回值：basic 接口请求 URL。
    逻辑：把 patent_id 直接拼到固定路径中，并默认携带 highlight=true。
    """

    return f"https://search-service.zhihuiya.com/core-search-api/search/patent/id/{patent_id}/basic?highlight=true"


def build_basic_request_body(*, template: dict, patent_id: str) -> dict:
    """简介：基于流程注入模板构建 basic 接口请求体。
    参数：template 为默认模板；patent_id 为当前专利标识。
    返回值：可直接提交的请求体字典。
    逻辑：复制模板并写入 patent_id，避免多次请求之间相互污染。
    """

    body = copy.deepcopy(template)
    body["patent_id"] = patent_id
    return body


def _contains_isd(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().upper() == "ISD"
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        return any(_contains_isd(item) for item in value)
    return False


def extract_grant_date_from_basic_payload(payload: dict) -> str:
    """简介：从 basic 接口响应中提取授权日期。
    参数：payload 为 basic 接口响应 JSON。
    返回值：ISD 日期字符串；若不存在则返回空字符串。
    逻辑：优先扫描 data.timeline 中 type 含 ISD 的事件，再回退到 data.ISD。
    """

    data = payload.get("data")
    if not isinstance(data, dict):
        return ""

    timeline = data.get("timeline")
    if isinstance(timeline, list):
        for item in timeline:
            if not isinstance(item, dict):
                continue
            if not _contains_isd(item.get("type")):
                continue
            date_text = str(item.get("date") or "").strip()
            if date_text:
                return date_text

    return str(data.get("ISD") or "").strip()


def strip_html_text(value: str) -> str:
    """简介：清洗摘要中的 HTML 标签并压缩空白。
    参数：value 为原始文本或 HTML 片段。
    返回值：去标签后的纯文本。
    """

    without_tags = HTML_TAG_PATTERN.sub(" ", value)
    return " ".join(without_tags.replace("&nbsp;", " ").split())


def extract_abstract_from_basic_payload(payload: dict) -> str:
    """简介：从 basic 接口响应中提取摘要文本。
    参数：payload 为 basic 接口响应 JSON。
    返回值：摘要文本；若不存在则返回空字符串。
    逻辑：优先取 ABST.CN，再取 ABST.EN，再回退到第一个可用语言字段。
    """

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


def post_basic_sync(
    *,
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
) -> dict:
    """简介：同步发送单条专利 basic 请求。
    参数：url/headers/body 为请求上下文；timeout_seconds/proxies 控制网络行为。
    返回值：basic 接口响应 JSON。
    逻辑：统一处理鉴权失效和临时错误，方便上层复用重试策略。
    """

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
    """简介：异步抓取单条专利 basic 响应完整载荷。
    参数：包含专利标识、请求头、请求体模板、节流器和重试配置。
    返回值：basic 接口响应 JSON。
    逻辑：复用与授权日期相同的请求和重试策略，但保留完整 payload 供多字段解析。
    """

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
    basic_request_body_template: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
    scheduler,
    retry_count: int,
    retry_backoff_base_seconds: float,
    request_concurrency: int,
) -> dict:
    """简介：为单页现有专利数据生成最小补充信息载荷（ABST + ISD）。
    参数：page_payload 为原页数据；space_id/folder_id 为上下文标识；其余为请求和并发配置。
    返回值：仅含 ABST/ISD 的页级输出字典。
    逻辑：逐条读取 PATENT_ID；摘要始终尝试补抓，授权日期仅在 LEGAL_STATUS 含 3 时请求。
    """

    rows = page_payload.get("data", {}).get("patents_data", [])
    if not isinstance(rows, list):
        raise ValueError("data.patents_data is not a list")

    async def process_row(row_index: int, row: object) -> tuple[int, dict, list[dict]]:
        row_failures: list[dict] = []
        if not isinstance(row, dict):
            return row_index, {"PATENT_ID": "", "PN": "", "ABST": "", "ISD": ""}, [
                {"row_index": row_index, "patent_id": "", "reason": "row_not_object"}
            ]

        patent_id = str(row.get("PATENT_ID") or "").strip()
        pn = str(row.get("PN") or "").strip()
        record = {
            "PATENT_ID": patent_id,
            "PN": pn,
            "ABST": "",
            "ISD": "",
        }

        if not patent_id:
            row_failures.append({"row_index": row_index, "patent_id": "", "reason": "missing_patent_id"})
            return row_index, record, row_failures

        # 判断是否已授权，用于决定是否请求 ISD。
        legal_status = row.get("LEGAL_STATUS")
        has_granted = _has_granted_status(legal_status)

        try:
            basic_payload = await fetch_patent_basic_payload(
                patent_id=patent_id,
                headers=basic_headers,
                body_template=basic_request_body_template,
                timeout_seconds=timeout_seconds,
                proxies=proxies,
                scheduler=scheduler,
                retry_count=retry_count,
                retry_backoff_base_seconds=retry_backoff_base_seconds,
            )
            record["ABST"] = extract_abstract_from_basic_payload(basic_payload)
            if has_granted:
                record["ISD"] = extract_grant_date_from_basic_payload(basic_payload)
        except AuthRefreshRequiredError:
            raise
        except Exception as exc:
            row_failures.append({"row_index": row_index, "patent_id": patent_id, "reason": f"basic: {exc}"})

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


def _has_granted_status(legal_status: object) -> bool:
    """检查专利法律状态是否包含授权状态码 "3"。"""

    if isinstance(legal_status, list):
        return any(str(item).strip() == "3" for item in legal_status)
    return str(legal_status).strip() == "3"
