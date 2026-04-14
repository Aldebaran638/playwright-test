from __future__ import annotations

import asyncio
from pathlib import Path

import requests
from loguru import logger

from zhy.modules.browser.build_context import build_browser_context
from zhy.modules.browser.context_config import BrowserContextUserInput
from zhy.modules.common.types.folder_patents import AuthRefreshRequiredError, TransientRequestError
from zhy.modules.common.types.pipeline import CompetitorPatentPipelineConfig
from zhy.modules.fetch.folder_patents_auth import refresh_auth_state
from zhy.modules.persist.auth_state_io import load_auth_state_from_file
from zhy.modules.persist.json_io import load_json_file_any_utf, save_json
from zhy.modules.transform.competitor_patent_pipeline import build_monthly_auth_config


LEGAL_STATUS_MAPPING_URL = "https://basic-service.zhihuiya.com/core-basic-api/analytics/config/legal-status"


def build_legal_status_headers(config: CompetitorPatentPipelineConfig, auth_state) -> dict[str, str]:
    headers = auth_state.to_headers(
        origin=config.workspace_origin,
        referer=config.workspace_referer,
        user_agent=config.workspace_user_agent,
        x_api_version=config.workspace_x_api_version,
        x_patsnap_from=config.workspace_x_patsnap_from,
        x_site_lang=config.workspace_x_site_lang,
    )
    headers["cache-control"] = "max-age=0"
    headers["priority"] = "u=1, i"
    return headers


def fetch_legal_status_mapping_sync(
    *,
    headers: dict[str, str],
    timeout_seconds: float,
    proxies: dict[str, str] | None,
) -> dict:
    response = requests.get(
        LEGAL_STATUS_MAPPING_URL,
        headers=headers,
        timeout=timeout_seconds,
        proxies=proxies,
    )
    if response.status_code == 401:
        raise AuthRefreshRequiredError("received 401 from legal status mapping API")
    if response.status_code == 429 or 500 <= response.status_code < 600:
        raise TransientRequestError(f"transient status code: {response.status_code}")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("legal status mapping payload is not a JSON object")
    return payload


async def fetch_legal_status_mapping_payload(
    *,
    headers: dict[str, str],
    timeout_seconds: float,
    proxies: dict[str, str] | None,
    retry_count: int,
    retry_backoff_base_seconds: float,
) -> dict:
    attempts = max(int(retry_count), 1)
    for attempt_index in range(attempts):
        try:
            return await asyncio.to_thread(
                fetch_legal_status_mapping_sync,
                headers=headers,
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
                "[legal_status_mapping] retry mapping fetch attempt={}/{} error={} sleep={}s",
                attempt_index + 1,
                attempts,
                exc,
                backoff_seconds,
            )
            await asyncio.sleep(backoff_seconds)
        except requests.HTTPError:
            raise
    raise RuntimeError("legal status mapping fetch exhausted")


def choose_auth_folder_id(config: CompetitorPatentPipelineConfig, folder_mapping_file: Path) -> str:
    for folder_id in config.patents_test_folder_ids:
        folder_id_text = str(folder_id).strip()
        if folder_id_text:
            return folder_id_text

    if folder_mapping_file.exists():
        payload = load_json_file_any_utf(folder_mapping_file)
        items = payload.get("data", []) if isinstance(payload, dict) else []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                folder_id = str(item.get("folder_id") or "").strip()
                if folder_id:
                    return folder_id

    raise ValueError("unable to determine folder_id for legal status auth refresh")


async def refresh_auth_state_for_legal_status(
    config: CompetitorPatentPipelineConfig,
    folder_mapping_file: Path,
):
    folder_id = choose_auth_folder_id(config, folder_mapping_file)
    browser_input = BrowserContextUserInput(
        browser_executable_path=config.browser_executable_path,
        user_data_dir=config.user_data_dir,
    )

    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        managed = await build_browser_context(
            playwright=playwright,
            user_input=browser_input,
            headless=config.headless,
        )
        try:
            return await refresh_auth_state(
                managed,
                build_monthly_auth_config(config),
                config.workspace_space_id,
                folder_id,
            )
        finally:
            await managed.close()


async def refresh_legal_status_mapping_file(
    *,
    config: CompetitorPatentPipelineConfig,
    folder_mapping_file: Path,
) -> Path:
    auth_state = load_auth_state_from_file(config.auth_state_file)
    proxies = {"http": config.patents_proxy, "https": config.patents_proxy} if config.patents_proxy else None

    for needs_refresh in (False, True):
        if auth_state is None or needs_refresh:
            logger.warning("[legal_status_mapping] refresh auth before mapping fetch")
            auth_state = await refresh_auth_state_for_legal_status(config, folder_mapping_file)

        try:
            headers = build_legal_status_headers(config, auth_state)
            payload = await fetch_legal_status_mapping_payload(
                headers=headers,
                timeout_seconds=config.patents_timeout_seconds,
                proxies=proxies,
                retry_count=config.patents_retry_count,
                retry_backoff_base_seconds=config.patents_retry_backoff_base_seconds,
            )
            save_json(config.legal_status_mapping_file, payload)
            logger.info(
                "[legal_status_mapping] mapping refreshed: output={} legal_status_count={}",
                config.legal_status_mapping_file,
                len(payload.get("data", {}).get("legalStatus", {})) if isinstance(payload.get("data"), dict) else 0,
            )
            return config.legal_status_mapping_file
        except AuthRefreshRequiredError:
            logger.warning("[legal_status_mapping] auth expired during mapping fetch, retrying with refreshed auth")
            auth_state = None
            continue

    raise RuntimeError("failed to refresh legal status mapping")
