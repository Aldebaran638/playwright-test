from __future__ import annotations

import asyncio
import copy
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import requests
from loguru import logger

from zhy.modules.folder_patents_hybrid.models import AuthRefreshRequiredError, FolderAuthState, TransientRequestError

if TYPE_CHECKING:
    from zhy.modules.folder_patents_hybrid.api_fetch import RequestScheduler


def build_abstract_headers(
    *,
    auth_state: FolderAuthState,
    origin: str,
    referer: str,
    user_agent: str,
    x_api_version: str,
    x_patsnap_from: str,
    x_site_lang: str,
) -> dict[str, str]:
    """简介：构建摘要接口请求头，复用现有鉴权字段并覆盖摘要场景头部。
    参数：auth_state 为当前 folder 的鉴权上下文；其余参数为流程文件注入的请求头配置。
    返回值：可直接用于摘要接口请求的 headers 字典。
    逻辑：沿用鉴权 token/cookie/client 标识，再替换 origin/referer/x-patsnap-from 等场景字段。
    """

    return auth_state.to_headers(
        origin=origin,
        referer=referer,
        user_agent=user_agent,
        x_api_version=x_api_version,
        x_patsnap_from=x_patsnap_from,
        x_site_lang=x_site_lang,
    )


def build_abstract_request_body(
    *,
    template: dict,
    patent_id: str,
    folder_id: str,
    workspace_id: str,
) -> dict:
    """简介：基于流程注入的模板构建单条专利摘要请求体。
    参数：template 为任务文件提供的默认模板；patent_id/folder_id/workspace_id 为当前专利上下文。
    返回值：摘要接口请求体字典。
    逻辑：复制模板并写入当前专利、folder、workspace 标识，避免污染原模板。
    """

    body = copy.deepcopy(template)
    body["patent_id"] = patent_id
    body["folder_id"] = folder_id
    body["workspace_id"] = workspace_id
    return body


def extract_abstract_text(payload: dict) -> str:
    """简介：从摘要接口响应中尽量提取出可读摘要文本。
    参数：payload 为摘要接口响应 JSON。
    返回值：归一化后的摘要文本；若无法识别则返回空字符串。
    逻辑：优先匹配常见文本字段，再递归展开列表/字典中的文本片段。
    """

    preferred_keys = (
        "translation",
        "translated_text",
        "translate",
        "text",
        "content",
        "value",
        "result",
        "ABST",
        "abst",
    )

    def normalize_text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            normalized = " ".join(value.replace("\n", " ").split())
            if normalized in {"0", "0.0", "null", "None", "false", "False", "[]", "{}"}:
                return ""
            return normalized
        if isinstance(value, bool):
            return ""
        return ""

    def visit(value: object) -> str:
        direct = normalize_text(value)
        if direct:
            return direct
        if isinstance(value, list):
            parts = [visit(item) for item in value]
            cleaned = [item for item in parts if item]
            return " ".join(cleaned)
        if isinstance(value, dict):
            for key in preferred_keys:
                nested = visit(value.get(key))
                if nested:
                    return nested
            for nested_value in value.values():
                nested = visit(nested_value)
                if nested:
                    return nested
        return ""

    return visit(payload)


def summarize_abstract_payload(payload: dict) -> dict[str, object]:
    """简介：提取摘要响应中的调试摘要，方便日志定位误提取问题。
    参数：payload 为摘要接口响应 JSON。
    返回值：只包含浅层 key 与少量关键信息的调试字典。
    逻辑：避免整包打印，只输出最可能影响摘要提取判断的结构摘要。
    """

    data = payload.get("data")
    summary: dict[str, object] = {
        "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
        "data_type": type(data).__name__,
    }
    if isinstance(data, dict):
        summary["data_keys"] = sorted(data.keys())[:20]
        for key in ("translation", "translated_text", "translate", "text", "content", "value", "result", "ABST", "abst"):
            if key in data:
                value = data.get(key)
                summary[f"data.{key}.type"] = type(value).__name__
                if isinstance(value, str):
                    summary[f"data.{key}.preview"] = value[:120]
    return summary


def post_abstract_sync(
    *,
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
) -> dict:
    """简介：同步发送单条专利摘要请求。
    参数：url/headers/body 为请求上下文；timeout_seconds/proxies 控制网络行为。
    返回值：摘要接口响应 JSON。
    逻辑：统一处理 401、429、5xx 等状态，为上层重试和鉴权刷新提供异常信号。
    """

    response = requests.post(url, headers=headers, json=body, timeout=timeout_seconds, proxies=proxies)
    if response.status_code == 401:
        raise AuthRefreshRequiredError("received 401 from abstract API")
    if response.status_code == 429 or 500 <= response.status_code < 600:
        raise TransientRequestError(f"transient status code: {response.status_code}")
    response.raise_for_status()
    return response.json()


async def fetch_single_patent_abstract(
    *,
    patent_id: str,
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
    scheduler: RequestScheduler,
    retry_count: int,
    retry_backoff_base_seconds: float,
) -> str:
    """简介：异步抓取单条专利摘要，并返回提取后的纯文本。
    参数：包含专利标识、请求上下文、节流调度器和重试配置。
    返回值：抽取后的摘要文本。
    逻辑：沿用分页请求的指数退避策略，请求成功后再解析摘要文本。
    """

    attempts = max(retry_count, 1)
    for attempt_index in range(attempts):
        try:
            async with scheduler:
                payload = await asyncio.to_thread(
                    post_abstract_sync,
                    url=url,
                    headers=headers,
                    body=body,
                    timeout_seconds=timeout_seconds,
                    proxies=proxies,
                )
            text = extract_abstract_text(payload)
            if not text:
                logger.warning(
                    "[folder_patents_hybrid_abstract] empty abstract payload patent_id={} payload_summary={}",
                    patent_id,
                    summarize_abstract_payload(payload),
                )
                raise ValueError("abstract text missing from response payload")
            if text in {"0", "0.0"}:
                logger.warning(
                    "[folder_patents_hybrid_abstract] suspicious abstract patent_id={} text={} payload_summary={}",
                    patent_id,
                    text,
                    summarize_abstract_payload(payload),
                )
                raise ValueError("abstract text resolved to suspicious numeric placeholder")
            return text
        except AuthRefreshRequiredError:
            raise
        except (TransientRequestError, requests.Timeout, requests.ConnectionError) as exc:
            if attempt_index >= attempts - 1:
                raise
            backoff_seconds = retry_backoff_base_seconds * (2 ** attempt_index)
            logger.warning(
                "[folder_patents_hybrid_abstract] retry abstract patent_id={} attempt={}/{} error={} sleep={}s",
                patent_id,
                attempt_index + 1,
                attempts,
                exc,
                backoff_seconds,
            )
            await asyncio.sleep(backoff_seconds)
        except requests.HTTPError:
            raise

    raise RuntimeError(f"abstract fetch exhausted for patent_id={patent_id}")


async def enrich_page_patents_with_abstracts(
    *,
    page_payload: dict,
    text_field_name: str,
    request_url: str,
    request_template: dict,
    request_headers: dict[str, str],
    folder_id: str,
    workspace_id: str,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
    scheduler: RequestScheduler,
    retry_count: int,
    retry_backoff_base_seconds: float,
    fetcher: Callable[..., Awaitable[str]] | None = None,
) -> list[dict]:
    """简介：为单页专利列表逐条补抓摘要，并直接回写到页数据结构中。
    参数：page_payload 为列表页 JSON；其余参数为摘要接口请求配置。
    返回值：失败列表，每项包含 page 内失败专利的定位信息和错误原因。
    逻辑：遍历 patents_data，读取 PATENT_ID，逐条请求摘要；失败时继续处理后续记录。
    """

    data = page_payload.get("data")
    if not isinstance(data, dict):
        return [{"patent_id": "", "reason": "missing_data_object"}]

    patents_data = data.get("patents_data")
    if not isinstance(patents_data, list):
        return [{"patent_id": "", "reason": "missing_patents_data"}]

    if fetcher is None:
        fetcher = fetch_single_patent_abstract

    failures: list[dict] = []

    for row_index, row in enumerate(patents_data):
        if not isinstance(row, dict):
            failures.append({"row_index": row_index, "patent_id": "", "reason": "row_not_object"})
            continue

        patent_id = str(row.get("PATENT_ID") or "").strip()
        if not patent_id:
            failures.append({"row_index": row_index, "patent_id": "", "reason": "missing_patent_id"})
            continue

        if str(row.get(text_field_name) or "").strip():
            continue

        body = build_abstract_request_body(
            template=request_template,
            patent_id=patent_id,
            folder_id=folder_id,
            workspace_id=workspace_id,
        )

        try:
            abstract_text = await fetcher(
                patent_id=patent_id,
                url=request_url,
                headers=request_headers,
                body=body,
                timeout_seconds=timeout_seconds,
                proxies=proxies,
                scheduler=scheduler,
                retry_count=retry_count,
                retry_backoff_base_seconds=retry_backoff_base_seconds,
            )
            row[text_field_name] = abstract_text
        except AuthRefreshRequiredError:
            raise
        except Exception as exc:
            failures.append(
                {
                    "row_index": row_index,
                    "patent_id": patent_id,
                    "reason": str(exc),
                }
            )
            logger.warning(
                "[folder_patents_hybrid_abstract] abstract failed patent_id={} row_index={} error={}",
                patent_id,
                row_index,
                exc,
            )

    return failures
