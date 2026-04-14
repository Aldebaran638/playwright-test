from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

from zhy.modules.common.types.pipeline import CompetitorPatentPipelineConfig
from zhy.modules.persist.json_io import save_json


def filter_competitor_folder_items(payload: dict, parent_folder_id: str) -> list[dict]:
    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []

    filtered: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("parent_id") or "").strip() != parent_folder_id:
            continue
        filtered.append(item)
    return filtered


def build_filtered_folder_mapping_payload(config: CompetitorPatentPipelineConfig, filtered_items: list[dict]) -> dict:
    return {
        "status": True,
        "space_id": config.workspace_space_id,
        "parent_folder_id": config.competitor_parent_folder_id,
        "total": len(filtered_items),
        "data": filtered_items,
    }


def is_target_competitor_list_response(response, request_url: str) -> bool:
    return response.request.method.upper() == "GET" and response.url == request_url


async def fetch_competitor_folder_mapping(managed, config: CompetitorPatentPipelineConfig) -> tuple[Path, int]:
    page = await managed.context.new_page()
    try:
        async def open_target_page() -> None:
            await page.goto(
                config.competitor_list_page_url,
                wait_until="domcontentloaded",
                timeout=config.competitor_list_capture_timeout_ms,
            )

        try:
            async with page.expect_response(
                lambda response: is_target_competitor_list_response(response, config.competitor_list_request_url),
                timeout=config.competitor_list_capture_timeout_ms,
            ) as response_info:
                await open_target_page()
            response = await response_info.value
        except Exception:
            async with page.expect_response(
                lambda response: is_target_competitor_list_response(response, config.competitor_list_request_url),
                timeout=config.competitor_list_capture_timeout_ms,
            ) as response_info:
                await page.reload(wait_until="domcontentloaded", timeout=config.competitor_list_capture_timeout_ms)
            response = await response_info.value

        payload = await response.json()
        config.folder_mapping_raw_file.parent.mkdir(parents=True, exist_ok=True)
        config.folder_mapping_raw_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        filtered_items = filter_competitor_folder_items(payload, config.competitor_parent_folder_id)
        filtered_payload = build_filtered_folder_mapping_payload(config, filtered_items)
        save_json(config.folder_mapping_file, filtered_payload)
        logger.info(
            "[competitor_patent_pipeline] competitor list captured: total={} filtered={} output={}",
            len(payload.get("data", [])) if isinstance(payload, dict) and isinstance(payload.get("data"), list) else 0,
            len(filtered_items),
            config.folder_mapping_file,
        )
        return config.folder_mapping_file, len(filtered_items)
    finally:
        await page.close()
