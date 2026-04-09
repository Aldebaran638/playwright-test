from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import urlparse

from loguru import logger
from playwright.async_api import Request

from zhy.modules.common.browser_cookies import load_cookies_if_present, save_cookies
from zhy.modules.folder_patents_hybrid.models import FolderAuthState, HybridTaskConfig, strip_or_none
from zhy.modules.folder_patents_hybrid.storage import save_json
from zhy.modules.site_init.initialize_site_async import initialize_site


def build_folder_page_url(space_id: str, folder_id: str, page: int) -> str:
    """构建 workspace 专利表页 URL。"""

    return (
        "https://workspace.zhihuiya.com/detail/patent/table"
        f"?spaceId={space_id}&folderId={folder_id}&page={page}"
    )


def build_cookie_header_from_cookie_list(cookies: list[dict]) -> str | None:
    """将 Playwright cookies 列表拼成 Cookie 请求头。"""

    items: list[str] = []
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if not name:
            continue
        items.append(f"{name}={value or ''}")
    if not items:
        return None
    return "; ".join(items)


async def ensure_logged_in(managed, config: HybridTaskConfig) -> None:
    """
    简介：确保浏览器上下文已登录，并把 cookie 持久化到本地文件。
    参数：managed 为浏览器上下文包装对象；config 为流程配置。
    返回值：无。
    逻辑：加载 cookie -> 打开站点完成登录检测 -> 再次保存 cookie。
    """

    logger.info(
        "[folder_patents_hybrid_auth] ensure_logged_in: cookie_file={} target_home={}",
        config.cookie_file,
        config.target_home_url,
    )
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
    await save_cookies(managed.context, config.cookie_file)
    logger.info("[folder_patents_hybrid_auth] ensure_logged_in complete: final_url={}", page.url)
    await page.close()


def is_matching_patents_request(request: Request, space_id: str, folder_id: str) -> bool:
    """判断请求是否为目标 folder 的 patents API。"""

    if request.method.upper() != "POST":
        return False
    parsed = urlparse(request.url)
    if parsed.netloc != "workspace-service.zhihuiya.com":
        return False
    expected_path = f"/workspace/web/{space_id}/folder/{folder_id}/patents"
    return parsed.path == expected_path


async def capture_patents_auth_state(managed, config: HybridTaskConfig, space_id: str, folder_id: str) -> FolderAuthState:
    """
    简介：通过监听真实页面请求抓取鉴权参数与 body 模板。
    参数：managed 为浏览器上下文包装对象；config 为流程配置；space_id/folder_id 为当前目标。
    返回值：FolderAuthState。
    逻辑：打开目标页并等待 API 请求 -> 提取 headers/body/cookie -> 持久化 auth_state。
    """

    logger.info(
        "[folder_patents_hybrid_auth] capture_auth start: space_id={} folder_id={} start_page={}",
        space_id,
        folder_id,
        config.start_page,
    )
    page = await managed.context.new_page()
    try:
        target_url = build_folder_page_url(space_id, folder_id, config.start_page)

        async def trigger_navigation() -> None:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=config.capture_timeout_ms)

        try:
            async with page.expect_request(
                lambda request: is_matching_patents_request(request, space_id, folder_id),
                timeout=config.capture_timeout_ms,
            ) as request_info:
                await trigger_navigation()
            request = await request_info.value
        except Exception:
            async with page.expect_request(
                lambda request: is_matching_patents_request(request, space_id, folder_id),
                timeout=config.capture_timeout_ms,
            ) as request_info:
                await page.reload(wait_until="domcontentloaded", timeout=config.capture_timeout_ms)
            request = await request_info.value

        headers = await request.all_headers()
        raw_body = request.post_data or "{}"
        try:
            body_template = json.loads(raw_body)
        except json.JSONDecodeError:
            body_template = {}

        cookies = await managed.context.cookies()
        cookie_header = build_cookie_header_from_cookie_list(cookies)

        auth_state = FolderAuthState(
            space_id=space_id,
            folder_id=folder_id,
            request_url=request.url,
            authorization=strip_or_none(headers.get("authorization")),
            x_client_id=strip_or_none(headers.get("x-client-id")),
            x_device_id=strip_or_none(headers.get("x-device-id")),
            b3=strip_or_none(headers.get("b3")),
            cookie_header=cookie_header,
            body_template=body_template if isinstance(body_template, dict) else {},
            captured_at=datetime.now(timezone.utc).isoformat(),
        )

        save_json(config.auth_state_file, auth_state.to_json())
        await save_cookies(managed.context, config.cookie_file)

        logger.info(
            "[folder_patents_hybrid_auth] capture_auth success: folder_id={} request_url={} has_authorization={} has_x_client_id={} has_x_device_id={} has_b3={} has_cookie={}",
            folder_id,
            auth_state.request_url,
            bool(auth_state.authorization),
            bool(auth_state.x_client_id),
            bool(auth_state.x_device_id),
            bool(auth_state.b3),
            bool(auth_state.cookie_header),
        )
        return auth_state
    finally:
        await page.close()


async def refresh_auth_state(managed, config: HybridTaskConfig, space_id: str, folder_id: str) -> FolderAuthState:
    """刷新登录态并重新抓取鉴权参数。"""

    logger.warning(
        "[folder_patents_hybrid_auth] refreshing auth state: space_id={} folder_id={}",
        space_id,
        folder_id,
    )
    await ensure_logged_in(managed, config)
    return await capture_patents_auth_state(managed, config, space_id, folder_id)
