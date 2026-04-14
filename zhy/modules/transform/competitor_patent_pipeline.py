from __future__ import annotations

import json
from pathlib import Path

from zhy.modules.common.types.enrichment import ExistingOutputEnrichmentConfig
from zhy.modules.common.types.folder_patents import HybridTaskConfig
from zhy.modules.common.types.pipeline import CompetitorPatentPipelineConfig
from zhy.modules.common.types.report import CompetitorPatentReportConfig
from zhy.modules.common.types.translation import PatentAbstractTranslationConfig


def build_existing_output_enrichment_config(config: CompetitorPatentPipelineConfig) -> ExistingOutputEnrichmentConfig:
    return ExistingOutputEnrichmentConfig(
        input_root=config.original_output_root,
        output_root=config.enriched_output_root,
        auth_state_file=config.auth_state_file,
        cookie_file=config.cookie_file,
        browser_executable_path=config.browser_executable_path,
        user_data_dir=config.user_data_dir,
        target_home_url=config.target_home_url,
        success_url=config.success_url,
        success_header_selector=config.success_header_selector,
        success_logged_in_selector=config.success_logged_in_selector,
        success_content_selector=config.success_content_selector,
        loading_overlay_selector=config.loading_overlay_selector,
        goto_timeout_ms=config.goto_timeout_ms,
        login_timeout_seconds=config.login_timeout_seconds,
        login_poll_interval_seconds=config.login_poll_interval_seconds,
        capture_timeout_ms=config.patents_capture_timeout_ms,
        max_auth_refreshes=config.patents_max_auth_refreshes,
        headless=config.headless,
        timeout_seconds=config.patents_timeout_seconds,
        retry_count=config.patents_retry_count,
        retry_backoff_base_seconds=config.patents_retry_backoff_base_seconds,
        min_request_interval_seconds=config.patents_min_request_interval_seconds,
        request_jitter_seconds=config.patents_request_jitter_seconds,
        resume=config.enrichment_resume,
        proxy=config.patents_proxy,
        user_agent=config.workspace_user_agent,
        x_api_version=config.workspace_x_api_version,
        x_site_lang=config.workspace_x_site_lang,
        analytics_origin=config.analytics_origin,
        analytics_referer=config.analytics_referer,
        analytics_x_patsnap_from=config.analytics_x_patsnap_from,
        abstract_request_url=config.abstract_request_url,
        abstract_request_template=config.abstract_request_template,
        basic_request_body_template=config.basic_request_body_template,
        request_concurrency=config.enrichment_request_concurrency,
        target_page_files=None,
        summary_path=None,
    )


def build_competitor_patent_report_config(config: CompetitorPatentPipelineConfig) -> CompetitorPatentReportConfig:
    return CompetitorPatentReportConfig(
        month=config.month,
        original_root=config.original_output_root,
        enriched_root=config.enriched_output_root,
        translated_root=config.translated_output_root if config.abstract_translation_enabled else None,
        folder_mapping_file=config.folder_mapping_file,
        legal_status_mapping_file=config.legal_status_mapping_file,
        output_dir=config.report_output_dir,
    )


def build_patent_abstract_translation_config(config: CompetitorPatentPipelineConfig) -> PatentAbstractTranslationConfig:
    return PatentAbstractTranslationConfig(
        input_root=config.enriched_output_root,
        output_root=config.translated_output_root,
        enabled=config.abstract_translation_enabled,
        resume=config.abstract_translation_resume,
        request_concurrency=config.abstract_translation_request_concurrency,
        target_language=config.abstract_translation_target_language,
        client=config.abstract_translation_client,
    )


def load_pages_written(summary_path: Path) -> int:
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    try:
        return int(payload.get("pages_written") or 0)
    except (TypeError, ValueError):
        return 0


def build_monthly_auth_config(config: CompetitorPatentPipelineConfig) -> HybridTaskConfig:
    return HybridTaskConfig(
        browser_executable_path=config.browser_executable_path,
        user_data_dir=config.user_data_dir,
        cookie_file=config.cookie_file,
        auth_state_file=config.auth_state_file,
        output_root=str(config.original_output_root),
        target_home_url=config.target_home_url,
        success_url=config.success_url,
        success_header_selector=config.success_header_selector,
        success_logged_in_selector=config.success_logged_in_selector,
        success_content_selector=config.success_content_selector,
        loading_overlay_selector=config.loading_overlay_selector,
        goto_timeout_ms=config.goto_timeout_ms,
        login_timeout_seconds=config.login_timeout_seconds,
        login_poll_interval_seconds=config.login_poll_interval_seconds,
        origin=config.workspace_origin,
        referer=config.workspace_referer,
        user_agent=config.workspace_user_agent,
        x_api_version=config.workspace_x_api_version,
        x_patsnap_from=config.workspace_x_patsnap_from,
        x_site_lang=config.workspace_x_site_lang,
        abstract_request_url=config.abstract_request_url,
        abstract_origin=config.analytics_origin,
        abstract_referer=config.analytics_referer,
        abstract_x_patsnap_from=config.analytics_x_patsnap_from,
        abstract_request_template=config.abstract_request_template,
        abstract_text_field_name="ABST",
        start_page=config.patents_start_page,
        max_pages=None,
        page_concurrency=1,
        size=config.patents_page_size,
        timeout_seconds=config.patents_timeout_seconds,
        capture_timeout_ms=config.patents_capture_timeout_ms,
        max_auth_refreshes=config.patents_max_auth_refreshes,
        retry_count=config.patents_retry_count,
        retry_backoff_base_seconds=config.patents_retry_backoff_base_seconds,
        min_request_interval_seconds=config.patents_min_request_interval_seconds,
        request_jitter_seconds=config.patents_request_jitter_seconds,
        resume=True,
        proxy=config.patents_proxy,
        headless=config.headless,
        fail_fast=False,
    )
