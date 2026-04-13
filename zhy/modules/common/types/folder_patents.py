from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class AuthRefreshRequiredError(Exception):
    """鉴权失效时抛出，提示外层刷新认证信息。"""


class TransientRequestError(Exception):
    """临时性请求失败（如 429/5xx）时抛出，用于触发重试。"""


@dataclass(frozen=True, slots=True)
class FolderApiTarget:
    """单个文件夹 API 抓取目标。"""

    space_id: str
    folder_id: str


@dataclass(slots=True)
class FolderAuthState:
    """文件夹 API 抓取所需鉴权上下文。"""

    space_id: str
    folder_id: str
    request_url: str
    authorization: str | None
    x_client_id: str | None
    x_device_id: str | None
    b3: str | None
    cookie_header: str | None
    body_template: dict
    captured_at: str

    def to_headers(self, *, origin: str, referer: str, user_agent: str, x_api_version: str, x_patsnap_from: str, x_site_lang: str) -> dict[str, str]:
        headers: dict[str, str] = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": origin,
            "referer": referer,
            "user-agent": user_agent,
            "x-api-version": x_api_version,
            "x-patsnap-from": x_patsnap_from,
            "x-requested-with": "XMLHttpRequest",
            "x-site-lang": x_site_lang,
        }
        if self.authorization:
            headers["authorization"] = self.authorization
        if self.x_client_id:
            headers["x-client-id"] = self.x_client_id
        if self.x_device_id:
            headers["x-device-id"] = self.x_device_id
        if self.b3:
            headers["b3"] = self.b3
        if self.cookie_header:
            headers["cookie"] = self.cookie_header
        return headers

    def to_json(self) -> dict:
        return {
            "space_id": self.space_id,
            "folder_id": self.folder_id,
            "request_url": self.request_url,
            "authorization": self.authorization,
            "x_client_id": self.x_client_id,
            "x_device_id": self.x_device_id,
            "b3": self.b3,
            "cookie_header": self.cookie_header,
            "body_template": self.body_template,
            "captured_at": self.captured_at,
        }

    @classmethod
    def from_json(cls, data: dict) -> "FolderAuthState":
        return cls(
            space_id=str(data.get("space_id") or "").strip(),
            folder_id=str(data.get("folder_id") or "").strip(),
            request_url=str(data.get("request_url") or "").strip(),
            authorization=strip_or_none(data.get("authorization")),
            x_client_id=strip_or_none(data.get("x_client_id")),
            x_device_id=strip_or_none(data.get("x_device_id")),
            b3=strip_or_none(data.get("b3")),
            cookie_header=strip_or_none(data.get("cookie_header")),
            body_template=data.get("body_template") if isinstance(data.get("body_template"), dict) else {},
            captured_at=str(data.get("captured_at") or "").strip(),
        )


@dataclass(slots=True)
class HybridTaskConfig:
    """文件夹 API 抓取流程运行配置，所有模块参数均由流程文件注入。"""

    browser_executable_path: str | None
    user_data_dir: str | None
    cookie_file: Path
    auth_state_file: Path
    output_root: Path
    target_home_url: str
    success_url: str
    success_header_selector: str
    success_logged_in_selector: str
    success_content_selector: str
    loading_overlay_selector: str
    goto_timeout_ms: int
    login_timeout_seconds: float
    login_poll_interval_seconds: float
    origin: str
    referer: str
    x_site_lang: str
    x_api_version: str
    x_patsnap_from: str
    user_agent: str
    abstract_request_url: str
    abstract_origin: str
    abstract_referer: str
    abstract_x_patsnap_from: str
    abstract_request_template: dict
    abstract_text_field_name: str
    start_page: int
    max_pages: int | None
    page_concurrency: int
    size: int
    timeout_seconds: float
    capture_timeout_ms: int
    max_auth_refreshes: int
    retry_count: int
    retry_backoff_base_seconds: float
    min_request_interval_seconds: float
    request_jitter_seconds: float
    resume: bool
    proxy: str | None
    headless: bool
    fail_fast: bool


def strip_or_none(value: object) -> str | None:
    """把任意值转成去空白字符串，空值返回 None。"""

    if value is None:
        return None
    text = str(value).strip()
    return text or None
