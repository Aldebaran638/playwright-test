from __future__ import annotations

import asyncio
import copy
import math
from random import uniform
from time import monotonic

import requests
from loguru import logger

from zhy.modules.folder_patents_hybrid.models import AuthRefreshRequiredError, FolderAuthState, TransientRequestError
from zhy.modules.folder_patents_hybrid.storage import build_output_path, load_json_file_any_utf, save_json


class RequestScheduler:
    """请求调度器：控制并发上限和相邻请求最小间隔。"""

    def __init__(self, concurrency: int, min_interval_seconds: float, jitter_seconds: float) -> None:
        self._semaphore = asyncio.Semaphore(max(concurrency, 1))
        self._interval_lock = asyncio.Lock()
        self._last_request_started_at = 0.0
        self._min_interval_seconds = max(min_interval_seconds, 0.0)
        self._jitter_seconds = max(jitter_seconds, 0.0)

    async def __aenter__(self):
        await self._semaphore.acquire()
        await self._wait_for_slot()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._semaphore.release()

    async def _wait_for_slot(self) -> None:
        async with self._interval_lock:
            now = monotonic()
            target = self._last_request_started_at + self._min_interval_seconds
            wait_seconds = max(0.0, target - now)
            wait_seconds += uniform(0.0, self._jitter_seconds)
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            self._last_request_started_at = monotonic()


def build_request_body_for_page(template: dict, space_id: str, folder_id: str, page: int, size: int) -> dict:
    """基于模板构建指定页码请求体。"""

    body = copy.deepcopy(template)
    body["space_id"] = space_id
    body["folder_id"] = folder_id
    body["size"] = size
    body["page"] = page if isinstance(body.get("page"), int) else str(page)
    return body


def post_page_sync(url: str, headers: dict[str, str], body: dict, timeout_seconds: float, proxies: dict[str, str] | None) -> dict:
    """同步发送单页 POST 请求。"""

    response = requests.post(url, headers=headers, json=body, timeout=timeout_seconds, proxies=proxies)
    if response.status_code == 401:
        raise AuthRefreshRequiredError("received 401 from patents API")
    if response.status_code == 429 or 500 <= response.status_code < 600:
        raise TransientRequestError(f"transient status code: {response.status_code}")
    response.raise_for_status()
    return response.json()


async def post_page_async(
    *,
    page: int,
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout_seconds: float,
    proxies: dict[str, str] | None,
    scheduler: RequestScheduler,
    retry_count: int,
    retry_backoff_base_seconds: float,
) -> tuple[int, dict]:
    """异步发送单页请求，内置指数退避重试。"""

    attempts = max(retry_count, 1)
    for attempt_index in range(attempts):
        try:
            async with scheduler:
                parsed = await asyncio.to_thread(
                    post_page_sync,
                    url,
                    headers,
                    body,
                    timeout_seconds,
                    proxies,
                )
            return page, parsed
        except AuthRefreshRequiredError:
            raise
        except (TransientRequestError, requests.Timeout, requests.ConnectionError) as exc:
            if attempt_index >= attempts - 1:
                raise
            backoff_seconds = retry_backoff_base_seconds * (2 ** attempt_index)
            logger.warning(
                "[folder_patents_hybrid_api] retry request page={} attempt={}/{} error={} sleep={}s",
                page,
                attempt_index + 1,
                attempts,
                exc,
                backoff_seconds,
            )
            await asyncio.sleep(backoff_seconds)
        except requests.HTTPError:
            raise


async def fetch_folder_pages(
    *,
    space_id: str,
    folder_id: str,
    auth_state: FolderAuthState,
    output_root,
    start_page: int,
    max_pages: int | None,
    page_concurrency: int,
    size: int,
    timeout_seconds: float,
    retry_count: int,
    retry_backoff_base_seconds: float,
    resume: bool,
    scheduler: RequestScheduler,
    proxies: dict[str, str] | None,
    headers: dict[str, str],
) -> dict:
    """
    简介：抓取单个文件夹的分页专利数据并按页落盘。
    参数：包含分页范围、并发、重试、输出目录和请求上下文等。
    返回值：folder_summary 字典，描述抓取结果与停止原因。
    逻辑：批次并发请求页面 -> 检测空页/总页数边界 -> 命中停止条件后返回。
    """

    request_url = auth_state.request_url or (
        "https://workspace-service.zhihuiya.com/"
        f"workspace/web/{space_id}/folder/{folder_id}/patents"
    )

    folder_summary = {
        "space_id": space_id,
        "folder_id": folder_id,
        "status": "ok",
        "reason": "",
        "total": None,
        "limit": None,
        "pages_saved": 0,
        "last_page_requested": None,
        "last_page_patent_count": None,
        "saved_files": [],
        "error": None,
        "auth_refresh_count": 0,
    }

    next_page = start_page
    while True:
        if max_pages is not None:
            remaining = max_pages - folder_summary["pages_saved"]
            if remaining <= 0:
                folder_summary["reason"] = "reached_max_pages_limit"
                break
            batch_size = min(page_concurrency, remaining)
        else:
            batch_size = page_concurrency

        pages = list(range(next_page, next_page + batch_size))
        tasks = []

        for page_number in pages:
            output_path = build_output_path(output_root, space_id, folder_id, page_number)
            if resume and output_path.exists():
                try:
                    parsed = load_json_file_any_utf(output_path)
                    tasks.append(asyncio.create_task(asyncio.sleep(0, result=(page_number, parsed))))
                    continue
                except Exception:
                    logger.warning(
                        "[folder_patents_hybrid_api] resume read failed and will refetch: {}",
                        output_path,
                    )

            body = build_request_body_for_page(auth_state.body_template, space_id, folder_id, page_number, size)
            tasks.append(
                asyncio.create_task(
                    post_page_async(
                        page=page_number,
                        url=request_url,
                        headers=headers,
                        body=body,
                        timeout_seconds=timeout_seconds,
                        proxies=proxies,
                        scheduler=scheduler,
                        retry_count=retry_count,
                        retry_backoff_base_seconds=retry_backoff_base_seconds,
                    )
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        auth_error = next((item for item in results if isinstance(item, AuthRefreshRequiredError)), None)
        if auth_error is not None:
            raise auth_error

        for item in results:
            if isinstance(item, Exception):
                raise item

        batch_results = sorted(results, key=lambda item: item[0])
        should_stop_folder = False

        for page_number, parsed in batch_results:
            output_path = build_output_path(output_root, space_id, folder_id, page_number)
            save_json(output_path, parsed)
            folder_summary["saved_files"].append(str(output_path))
            folder_summary["pages_saved"] += 1
            folder_summary["last_page_requested"] = page_number

            data = parsed.get("data") if isinstance(parsed, dict) else None
            if not isinstance(data, dict):
                folder_summary["reason"] = "missing_data_object"
                should_stop_folder = True
                break

            patents_data = data.get("patents_data")
            patent_count = len(patents_data) if isinstance(patents_data, list) else 0
            folder_summary["last_page_patent_count"] = patent_count

            total = data.get("total")
            limit = data.get("limit")
            try:
                total_int = int(total) if total is not None else None
            except (TypeError, ValueError):
                total_int = None
            try:
                limit_int = int(limit) if limit is not None else None
            except (TypeError, ValueError):
                limit_int = None

            folder_summary["total"] = total_int
            folder_summary["limit"] = limit_int

            if patent_count == 0:
                folder_summary["reason"] = "empty_page_detected"
                should_stop_folder = True
                break

            if total_int is not None and limit_int and limit_int > 0:
                max_page_by_total = math.ceil(total_int / limit_int)
                if page_number >= max_page_by_total:
                    folder_summary["reason"] = "reached_total_page"
                    should_stop_folder = True
                    break

        if should_stop_folder:
            break

        next_page += batch_size

    return folder_summary
