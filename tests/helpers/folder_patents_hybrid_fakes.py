from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from zhy.modules.folder_patents_hybrid.models import (
    AuthRefreshRequiredError,
    FolderAuthState,
    HybridTaskConfig,
    TransientRequestError,
)


class FakeContext:
    """最小可用 fake context，满足 workflow 关闭流程。"""

    def __init__(self, cookies_data: list[dict] | None = None) -> None:
        self.cookies_data = cookies_data or []

    async def cookies(self) -> list[dict]:
        return self.cookies_data


class FakeManagedBrowserContext:
    """最小 fake managed context，记录是否调用 close。"""

    def __init__(self, context: FakeContext | None = None) -> None:
        self.context = context or FakeContext()
        self.close_called = False

    async def close(self) -> None:
        self.close_called = True


class FakeAsyncPlaywright:
    """替代 async_playwright() 的 async context manager。"""

    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        return False


@dataclass(slots=True)
class ScriptedApi:
    """按页码剧本驱动 fake API，请求一次消费一个动作。"""

    script: dict[int, list[dict[str, Any]]]
    calls: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        pass

    def post_page_sync(
        self,
        url: str,
        headers: dict[str, str],
        body: dict,
        timeout_seconds: float,
        proxies: dict[str, str] | None,
    ) -> dict:
        raw_page = body.get("page", 1)
        page = int(raw_page)
        self.calls.append(page)

        queue = self.script.get(page)
        if not queue:
            raise AssertionError(f"no scripted action for page={page}")

        action = queue.pop(0)
        action_type = action["type"]

        if action_type == "success":
            return action["payload"]
        if action_type == "empty_page":
            return action.get("payload") or make_response(patent_count=0, total=40, limit=20)
        if action_type == "invalid_data":
            return action.get("payload") or {"unexpected": {}}
        if action_type == "401":
            raise AuthRefreshRequiredError("received 401 from patents API")
        if action_type == "transient_500":
            raise TransientRequestError("transient status code: 500")
        if action_type == "timeout":
            raise requests.Timeout("timeout")
        if action_type == "connection_error":
            raise requests.ConnectionError("connection error")

        raise AssertionError(f"unsupported action type: {action_type}")


def make_auth_state(space_id: str, folder_id: str) -> FolderAuthState:
    """创建完整 fake auth_state，字段和业务消费结构一致。"""

    return FolderAuthState(
        space_id=space_id,
        folder_id=folder_id,
        request_url=f"https://workspace-service.zhihuiya.com/workspace/web/{space_id}/folder/{folder_id}/patents",
        authorization="Bearer fake-token",
        x_client_id="fake-client-id",
        x_device_id="fake-device-id",
        b3="fake-b3",
        cookie_header="sid=fake",
        body_template={"page": 1, "size": 20, "query": {}},
        captured_at=datetime.now(timezone.utc).isoformat(),
    )


def make_patents(patent_count: int) -> list[dict[str, str]]:
    return [
        {"PN": f"CN{idx:06d}A", "PBDT": "2025-01-01"}
        for idx in range(1, patent_count + 1)
    ]


def make_response(patent_count: int, total: int, limit: int) -> dict:
    return {
        "data": {
            "patents_data": make_patents(patent_count),
            "total": total,
            "limit": limit,
        }
    }


def make_hybrid_config(tmp_path: Path) -> HybridTaskConfig:
    """创建用于 workflow 层测试的默认配置，所有输出写入 tmp_path。"""

    return HybridTaskConfig(
        browser_executable_path=None,
        user_data_dir=None,
        cookie_file=str(tmp_path / "cookies.json"),
        auth_state_file=str(tmp_path / "auth_state.json"),
        output_root=str(tmp_path / "output"),
        target_home_url="https://example.com",
        success_url="https://example.com",
        success_header_selector="#header",
        success_logged_in_selector="#avatar",
        success_content_selector="#content",
        loading_overlay_selector="#loading",
        goto_timeout_ms=1000,
        login_timeout_seconds=5.0,
        login_poll_interval_seconds=0.2,
        origin="https://workspace.zhihuiya.com",
        referer="https://workspace.zhihuiya.com/",
        x_site_lang="CN",
        x_api_version="2.0",
        x_patsnap_from="w-analytics-workspace",
        user_agent="fake-ua",
        start_page=1,
        max_pages=None,
        page_concurrency=1,
        size=20,
        timeout_seconds=1.0,
        capture_timeout_ms=1000,
        max_auth_refreshes=2,
        retry_count=2,
        retry_backoff_base_seconds=0.0,
        min_request_interval_seconds=0.0,
        request_jitter_seconds=0.0,
        resume=True,
        proxy=None,
        headless=True,
        fail_fast=False,
    )
