from __future__ import annotations

from loguru import logger

from zhy.modules.common.types.pipeline import CompetitorPatentPipelineConfig


async def ensure_pipeline_logged_in(managed, config: CompetitorPatentPipelineConfig) -> str:
    from zhy.modules.common.browser_cookies import load_cookies_if_present, save_cookies
    from zhy.modules.init.initialize_site_async import initialize_site

    await load_cookies_if_present(managed.context, config.cookie_file)
    page = await initialize_site(
        context=managed.context,
        target_home_url=config.target_home_url,
        success_url=config.success_url,
        success_header_selector=config.success_header_selector,
        success_logged_in_selector=config.success_logged_in_selector,
        success_content_selector=config.success_content_selector,
        loading_overlay_selector=config.loading_overlay_selector,
        goto_timeout_ms=config.goto_timeout_ms,
        timeout_seconds=config.login_timeout_seconds,
        poll_interval_seconds=config.login_poll_interval_seconds,
    )
    final_url = page.url
    await save_cookies(managed.context, config.cookie_file)
    await page.close()
    logger.info("[competitor_patent_pipeline] login complete: final_url={}", final_url)
    return final_url
