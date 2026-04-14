from __future__ import annotations

from pathlib import Path

from loguru import logger

from zhy.modules.common.types.enrichment import ExistingOutputEnrichmentConfig
from zhy.modules.common.types.folder_patents import FolderAuthState
from zhy.modules.fetch.folder_patents_auth import refresh_auth_state
from zhy.modules.persist.page_path import parse_space_folder_from_parent
from zhy.modules.transform.enrichment import build_enrichment_auth_refresh_config


async def ensure_enrichment_auth_state(
    *,
    config: ExistingOutputEnrichmentConfig,
    managed,
    page_files: list[Path],
    auth_state: FolderAuthState | None,
) -> FolderAuthState:
    if auth_state is not None:
        return auth_state
    if not page_files:
        raise ValueError("no page files found under input root")

    space_id, folder_id = parse_space_folder_from_parent(page_files[0].parent)
    if not space_id or not folder_id:
        raise ValueError(f"unable to parse space_id/folder_id from {page_files[0].parent}")

    logger.info(
        "[competitor_patent_pipeline] enrichment auth cache missing: space_id={} folder_id={}",
        space_id,
        folder_id,
    )
    return await refresh_auth_state(
        managed,
        build_enrichment_auth_refresh_config(config),
        space_id,
        folder_id,
    )
