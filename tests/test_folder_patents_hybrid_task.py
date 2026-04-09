from __future__ import annotations

import json
from pathlib import Path

import pytest

import zhy.tasks.folder_patents_hybrid_task as task_module
from tests.helpers.folder_patents_hybrid_fakes import (
    FakeAsyncPlaywright,
    FakeManagedBrowserContext,
    ScriptedApi,
    make_auth_state,
    make_hybrid_config,
    make_response,
)
from zhy.modules.folder_patents_hybrid.api_fetch import RequestScheduler, fetch_folder_pages
from zhy.modules.folder_patents_hybrid.models import AuthRefreshRequiredError, FolderApiTarget, TransientRequestError
from zhy.modules.folder_patents_hybrid.workflow import run_folder_patents_hybrid


@pytest.mark.asyncio
async def test_run_hybrid_task_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """验证正常分页抓取并在空页停止，同时落盘 summary 与 page 文件。"""

    auth_state = make_auth_state("space-a", "folder-a")
    scripted = ScriptedApi(
        {
            1: [{"type": "success", "payload": make_response(2, total=999, limit=20)}],
            2: [{"type": "success", "payload": make_response(1, total=999, limit=20)}],
            3: [{"type": "empty_page", "payload": make_response(0, total=999, limit=20)}],
        }
    )

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.api_fetch.post_page_sync", scripted.post_page_sync)

    summary = await fetch_folder_pages(
        space_id="space-a",
        folder_id="folder-a",
        auth_state=auth_state,
        output_root=tmp_path,
        start_page=1,
        max_pages=None,
        page_concurrency=1,
        size=20,
        timeout_seconds=1.0,
        retry_count=2,
        retry_backoff_base_seconds=0.0,
        resume=True,
        scheduler=RequestScheduler(1, 0.0, 0.0),
        proxies=None,
        headers=auth_state.to_headers(
            origin="https://workspace.zhihuiya.com",
            referer="https://workspace.zhihuiya.com/",
            user_agent="fake",
            x_api_version="2.0",
            x_patsnap_from="w-analytics-workspace",
            x_site_lang="CN",
        ),
    )

    folder_dir = tmp_path / "space-a_folder-a"
    assert (folder_dir / "page_0001.json").exists()
    assert (folder_dir / "page_0002.json").exists()
    assert (folder_dir / "page_0003.json").exists()
    assert summary["reason"] == "empty_page_detected"
    assert summary["pages_saved"] == 3


@pytest.mark.asyncio
async def test_auth_refresh_on_401(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """验证 401 触发 refresh_auth_state，刷新后继续执行。"""

    config = make_hybrid_config(tmp_path)
    target = FolderApiTarget(space_id="space-a", folder_id="folder-a")
    managed = FakeManagedBrowserContext()
    refresh_calls: list[int] = []

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.async_playwright", lambda: FakeAsyncPlaywright())

    async def fake_build_browser_context(playwright, user_input, headless):
        return managed

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.build_browser_context", fake_build_browser_context)
    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.load_auth_state_if_valid", lambda *args, **kwargs: None)

    async def fake_refresh_auth_state(managed_ctx, cfg, space_id, folder_id):
        refresh_calls.append(1)
        return make_auth_state(space_id, folder_id)

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.refresh_auth_state", fake_refresh_auth_state)

    state = {"first": True}

    async def fake_fetch_folder_pages(**kwargs):
        if state["first"]:
            state["first"] = False
            raise AuthRefreshRequiredError("received 401 from patents API")
        return {
            "space_id": "space-a",
            "folder_id": "folder-a",
            "status": "ok",
            "reason": "empty_page_detected",
            "total": 40,
            "limit": 20,
            "pages_saved": 3,
            "last_page_requested": 3,
            "last_page_patent_count": 0,
            "saved_files": ["a", "b", "c"],
            "error": None,
            "auth_refresh_count": 0,
        }

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.fetch_folder_pages", fake_fetch_folder_pages)

    summary_path = await run_folder_patents_hybrid(config, [target], default_space_id="space-a")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert len(refresh_calls) >= 2
    assert summary["folders"][0]["auth_refresh_count"] == 1
    assert summary["folders"][0]["pages_saved"] == 3


@pytest.mark.asyncio
async def test_retry_on_transient_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """验证 transient 错误触发 retry，并能在重试后成功。"""

    auth_state = make_auth_state("space-a", "folder-a")
    scripted = ScriptedApi(
        {
            1: [
                {"type": "transient_500"},
                {"type": "success", "payload": make_response(1, total=40, limit=20)},
            ],
            2: [{"type": "empty_page", "payload": make_response(0, total=40, limit=20)}],
        }
    )

    warning_messages: list[str] = []

    def fake_warning(message: str, *args, **kwargs):
        warning_messages.append(message)

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.api_fetch.post_page_sync", scripted.post_page_sync)
    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.api_fetch.logger.warning", fake_warning)

    summary = await fetch_folder_pages(
        space_id="space-a",
        folder_id="folder-a",
        auth_state=auth_state,
        output_root=tmp_path,
        start_page=1,
        max_pages=None,
        page_concurrency=1,
        size=20,
        timeout_seconds=1.0,
        retry_count=2,
        retry_backoff_base_seconds=0.0,
        resume=True,
        scheduler=RequestScheduler(1, 0.0, 0.0),
        proxies=None,
        headers=auth_state.to_headers(
            origin="https://workspace.zhihuiya.com",
            referer="https://workspace.zhihuiya.com/",
            user_agent="fake",
            x_api_version="2.0",
            x_patsnap_from="w-analytics-workspace",
            x_site_lang="CN",
        ),
    )

    assert summary["reason"] == "empty_page_detected"
    assert scripted.calls.count(1) == 2
    assert any("retry request" in msg for msg in warning_messages)


@pytest.mark.asyncio
async def test_retry_exhausted_raises_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """验证 transient 错误重试用尽后会抛错。"""

    auth_state = make_auth_state("space-a", "folder-a")
    scripted = ScriptedApi({1: [{"type": "transient_500"}, {"type": "transient_500"}]})

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.api_fetch.post_page_sync", scripted.post_page_sync)

    with pytest.raises(TransientRequestError):
        await fetch_folder_pages(
            space_id="space-a",
            folder_id="folder-a",
            auth_state=auth_state,
            output_root=tmp_path,
            start_page=1,
            max_pages=1,
            page_concurrency=1,
            size=20,
            timeout_seconds=1.0,
            retry_count=2,
            retry_backoff_base_seconds=0.0,
            resume=True,
            scheduler=RequestScheduler(1, 0.0, 0.0),
            proxies=None,
            headers=auth_state.to_headers(
                origin="https://workspace.zhihuiya.com",
                referer="https://workspace.zhihuiya.com/",
                user_agent="fake",
                x_api_version="2.0",
                x_patsnap_from="w-analytics-workspace",
                x_site_lang="CN",
            ),
        )


@pytest.mark.asyncio
async def test_resume_skips_existing_page_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """验证 resume 命中本地 page 文件时会跳过远端请求。"""

    auth_state = make_auth_state("space-a", "folder-a")
    folder_dir = tmp_path / "space-a_folder-a"
    folder_dir.mkdir(parents=True, exist_ok=True)
    (folder_dir / "page_0001.json").write_text(json.dumps(make_response(1, 999, 20)), encoding="utf-8")

    scripted = ScriptedApi(
        {
            1: [{"type": "success", "payload": make_response(1, 999, 20)}],
            2: [{"type": "success", "payload": make_response(1, 999, 20)}],
            3: [{"type": "empty_page", "payload": make_response(0, 999, 20)}],
        }
    )

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.api_fetch.post_page_sync", scripted.post_page_sync)

    summary = await fetch_folder_pages(
        space_id="space-a",
        folder_id="folder-a",
        auth_state=auth_state,
        output_root=tmp_path,
        start_page=1,
        max_pages=None,
        page_concurrency=1,
        size=20,
        timeout_seconds=1.0,
        retry_count=2,
        retry_backoff_base_seconds=0.0,
        resume=True,
        scheduler=RequestScheduler(1, 0.0, 0.0),
        proxies=None,
        headers=auth_state.to_headers(
            origin="https://workspace.zhihuiya.com",
            referer="https://workspace.zhihuiya.com/",
            user_agent="fake",
            x_api_version="2.0",
            x_patsnap_from="w-analytics-workspace",
            x_site_lang="CN",
        ),
    )

    assert scripted.calls.count(1) == 0
    assert summary["pages_saved"] == 3


@pytest.mark.asyncio
async def test_fail_when_auth_refresh_limit_reached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """验证持续 401 时会在达到 refresh 限制后失败并写入 summary。"""

    config = make_hybrid_config(tmp_path)
    config.max_auth_refreshes = 1
    target = FolderApiTarget(space_id="space-a", folder_id="folder-a")

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.async_playwright", lambda: FakeAsyncPlaywright())

    async def fake_build_browser_context(playwright, user_input, headless):
        return FakeManagedBrowserContext()

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.build_browser_context", fake_build_browser_context)
    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.load_auth_state_if_valid", lambda *args, **kwargs: None)

    async def fake_refresh_auth_state(managed_ctx, cfg, space_id, folder_id):
        return make_auth_state(space_id, folder_id)

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.refresh_auth_state", fake_refresh_auth_state)

    async def always_401(**kwargs):
        raise AuthRefreshRequiredError("received 401 from patents API")

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.fetch_folder_pages", always_401)

    summary_path = await run_folder_patents_hybrid(config, [target], default_space_id="space-a")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert summary["folders"][0]["status"] == "error"
    assert "auth refresh retry limit reached" in summary["folders"][0]["error"]


@pytest.mark.asyncio
async def test_fail_on_invalid_data_object(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """验证返回结构缺少 data 时，reason 为 missing_data_object。"""

    auth_state = make_auth_state("space-a", "folder-a")
    scripted = ScriptedApi({1: [{"type": "invalid_data"}]})

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.api_fetch.post_page_sync", scripted.post_page_sync)

    summary = await fetch_folder_pages(
        space_id="space-a",
        folder_id="folder-a",
        auth_state=auth_state,
        output_root=tmp_path,
        start_page=1,
        max_pages=1,
        page_concurrency=1,
        size=20,
        timeout_seconds=1.0,
        retry_count=2,
        retry_backoff_base_seconds=0.0,
        resume=True,
        scheduler=RequestScheduler(1, 0.0, 0.0),
        proxies=None,
        headers=auth_state.to_headers(
            origin="https://workspace.zhihuiya.com",
            referer="https://workspace.zhihuiya.com/",
            user_agent="fake",
            x_api_version="2.0",
            x_patsnap_from="w-analytics-workspace",
            x_site_lang="CN",
        ),
    )

    assert summary["reason"] == "missing_data_object"


@pytest.mark.asyncio
async def test_stop_on_total_limit_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """验证 total/limit 到达边界时会停止，不再请求下一页。"""

    auth_state = make_auth_state("space-a", "folder-a")
    scripted = ScriptedApi(
        {
            1: [{"type": "success", "payload": make_response(1, total=40, limit=20)}],
            2: [{"type": "success", "payload": make_response(1, total=40, limit=20)}],
            3: [{"type": "success", "payload": make_response(1, total=40, limit=20)}],
        }
    )

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.api_fetch.post_page_sync", scripted.post_page_sync)

    summary = await fetch_folder_pages(
        space_id="space-a",
        folder_id="folder-a",
        auth_state=auth_state,
        output_root=tmp_path,
        start_page=1,
        max_pages=None,
        page_concurrency=1,
        size=20,
        timeout_seconds=1.0,
        retry_count=2,
        retry_backoff_base_seconds=0.0,
        resume=True,
        scheduler=RequestScheduler(1, 0.0, 0.0),
        proxies=None,
        headers=auth_state.to_headers(
            origin="https://workspace.zhihuiya.com",
            referer="https://workspace.zhihuiya.com/",
            user_agent="fake",
            x_api_version="2.0",
            x_patsnap_from="w-analytics-workspace",
            x_site_lang="CN",
        ),
    )

    assert summary["reason"] == "reached_total_page"
    assert scripted.calls == [1, 2]


@pytest.mark.asyncio
async def test_auth_state_cache_hit_and_miss_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """验证 auth_state 缓存命中/未命中路径。"""

    config = make_hybrid_config(tmp_path)
    target = FolderApiTarget(space_id="space-a", folder_id="folder-a")

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.async_playwright", lambda: FakeAsyncPlaywright())

    async def fake_build_browser_context(playwright, user_input, headless):
        return FakeManagedBrowserContext()

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.build_browser_context", fake_build_browser_context)

    calls = {"refresh": 0}

    async def fake_refresh_auth_state(managed_ctx, cfg, space_id, folder_id):
        calls["refresh"] += 1
        return make_auth_state(space_id, folder_id)

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.refresh_auth_state", fake_refresh_auth_state)

    async def fake_fetch_folder_pages(**kwargs):
        return {
            "space_id": "space-a",
            "folder_id": "folder-a",
            "status": "ok",
            "reason": "empty_page_detected",
            "total": 1,
            "limit": 20,
            "pages_saved": 1,
            "last_page_requested": 1,
            "last_page_patent_count": 0,
            "saved_files": ["page_0001.json"],
            "error": None,
            "auth_refresh_count": 0,
        }

    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.fetch_folder_pages", fake_fetch_folder_pages)

    # 先走缓存命中路径。
    monkeypatch.setattr(
        "zhy.modules.folder_patents_hybrid.workflow.load_auth_state_if_valid",
        lambda *args, **kwargs: make_auth_state("space-a", "folder-a"),
    )
    await run_folder_patents_hybrid(config, [target], default_space_id="space-a")
    assert calls["refresh"] == 0

    # 再走缓存未命中路径。
    monkeypatch.setattr("zhy.modules.folder_patents_hybrid.workflow.load_auth_state_if_valid", lambda *args, **kwargs: None)
    await run_folder_patents_hybrid(config, [target], default_space_id="space-a")
    assert calls["refresh"] >= 1


@pytest.mark.asyncio
async def test_default_arguments_can_start_without_real_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """验证 task 默认参数模式可启动，并调用下沉 workflow。"""

    parser = task_module.build_argument_parser()
    args = parser.parse_args([])

    assert args.use_defaults == 1

    args = task_module.apply_default_mode(args)
    args.output_root = tmp_path / "output"
    args.cookie_file = tmp_path / "cookies.json"
    args.auth_state_file = tmp_path / "auth.json"

    async def fake_run_folder_patents_hybrid(config, folder_targets, default_space_id):
        path = Path(config.output_root) / f"{default_space_id}_run_summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"default_space_id": default_space_id, "folders": []}), encoding="utf-8")
        return path

    monkeypatch.setattr(task_module, "run_folder_patents_hybrid", fake_run_folder_patents_hybrid)

    summary_path = await task_module.run_task(args)
    assert summary_path.exists()
