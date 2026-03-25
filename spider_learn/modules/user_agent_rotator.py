"""Utilities for generating realistic rotating user agents."""

from __future__ import annotations

import random
from functools import lru_cache
from typing import Final

from fake_useragent import UserAgent
from loguru import logger

_ALLOWED_BROWSERS: Final[tuple[str, ...]] = ("Chrome", "Edge", "Firefox", "Safari")
_ALLOWED_OS: Final[tuple[str, ...]] = ("Windows", "Mac OS X", "Linux", "Ubuntu")
_MIN_BROWSER_VERSIONS: Final[dict[str, float]] = {
    "Chrome": 120.0,
    "Edge": 120.0,
    "Firefox": 120.0,
    "Safari": 17.0,
}
_FALLBACK_USER_AGENTS: Final[tuple[str, ...]] = (
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) "
        "Gecko/20100101 Firefox/137.0"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.3 Safari/605.1.15"
    ),
)

_user_agent_provider = UserAgent(
    browsers=_ALLOWED_BROWSERS,
    os=_ALLOWED_OS,
    platforms="desktop",
)


def _is_plausible_desktop_user_agent(entry: dict[str, object]) -> bool:
    browser = str(entry.get("browser", ""))
    if browser not in _ALLOWED_BROWSERS:
        return False

    operating_system = str(entry.get("os", ""))
    if operating_system not in _ALLOWED_OS:
        return False

    if entry.get("type") != "desktop":
        return False

    version = float(entry.get("browser_version_major_minor", 0.0))
    if version < _MIN_BROWSER_VERSIONS[browser]:
        return False

    user_agent = str(entry.get("useragent", ""))
    if not user_agent.startswith("Mozilla/5.0"):
        return False

    forbidden_tokens = ("HeadlessChrome", "PhantomJS", "Electron/", "bot", "crawler")
    if any(token in user_agent for token in forbidden_tokens):
        return False

    if browser == "Safari":
        return "Macintosh" in user_agent and "Safari/" in user_agent and "Chrome/" not in user_agent

    if browser in {"Chrome", "Edge"}:
        return "AppleWebKit/537.36" in user_agent and "Safari/537.36" in user_agent

    if browser == "Firefox":
        return "Gecko/20100101" in user_agent and "Firefox/" in user_agent

    return True


@lru_cache(maxsize=1)
def _load_candidate_pool() -> tuple[dict[str, object], ...]:
    candidates = tuple(
        entry
        for entry in _user_agent_provider.data_browsers
        if _is_plausible_desktop_user_agent(entry)
    )

    logger.debug("[模块] 已加载可信桌面 UA 数量: {count}", count=len(candidates))

    if not candidates:
        logger.warning("[模块] fake-useragent 数据中没有可用 UA，改用内置后备 UA 池。")

    return candidates


def get_rotating_user_agent() -> str:
    """Return a realistic desktop browser UA string.

    The selection is limited to current mainstream desktop browsers and weighted
    by the usage percentage bundled with ``fake-useragent``.
    """

    candidates = _load_candidate_pool()
    if not candidates:
        selected_fallback = random.choice(_FALLBACK_USER_AGENTS)
        logger.debug("[模块] 本次使用后备 UA: {ua}", ua=selected_fallback)
        return selected_fallback

    weights = [max(float(entry.get("percent", 0.0)), 0.01) for entry in candidates]
    selected = random.choices(candidates, weights=weights, k=1)[0]

    logger.debug(
        "[模块] 本次选中 UA -> 浏览器: {browser}, 版本: {version}, 系统: {os}, 权重: {percent}",
        browser=selected.get("browser"),
        version=selected.get("browser_version"),
        os=selected.get("os"),
        percent=selected.get("percent"),
    )

    return str(selected["useragent"])
