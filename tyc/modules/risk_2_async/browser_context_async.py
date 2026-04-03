from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from loguru import logger
from playwright.async_api import BrowserContext, Playwright


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


STEALTH_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "common" / "assets" / "stealth.min.js"
COOKIES_FILE_PATH = PROJECT_ROOT / "cookies.json"


@dataclass(slots=True)
class BrowserContextDecision:
    requested_mode: str
    resolved_mode: str = ""
    success: bool = False
    used_fallback: bool = False
    fallback_chain: list[str] = field(default_factory=list)
    reason: str = ""
    messages: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BrowserContextStrategy:
    name: str
    description: str
    factory: Callable[[], Awaitable[BrowserContext]]


def _ensure_stealth_script_exists() -> None:
    if not STEALTH_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"missing stealth script: {STEALTH_SCRIPT_PATH}")


def _ensure_browser_executable(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"browser executable not found: {path}")


def _ensure_user_data_dir(path: Path) -> None:
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"user data directory not found: {path}")


def _build_strategies(
    playwright: Playwright,
    browser_executable_path: Path | None,
    user_data_dir: Path | None,
    headless: bool,
) -> tuple[str, list[BrowserContextStrategy]]:
    strategies: list[BrowserContextStrategy] = []

    if browser_executable_path is not None and user_data_dir is not None:
        strategies.append(
            BrowserContextStrategy(
                name="full_persistent",
                description="自定义浏览器 + 持久化用户目录",
                factory=lambda: _launch_full_persistent(
                    playwright,
                    browser_executable_path,
                    user_data_dir,
                    headless,
                ),
            )
        )
        strategies.append(
            BrowserContextStrategy(
                name="custom_browser_ephemeral",
                description="自定义浏览器 + 临时上下文",
                factory=lambda: _launch_custom_browser_ephemeral(
                    playwright,
                    browser_executable_path,
                    headless,
                ),
            )
        )
        return "full_persistent", strategies

    if browser_executable_path is not None:
        strategies.append(
            BrowserContextStrategy(
                name="custom_browser_ephemeral",
                description="自定义浏览器 + 临时上下文",
                factory=lambda: _launch_custom_browser_ephemeral(
                    playwright,
                    browser_executable_path,
                    headless,
                ),
            )
        )
        return "custom_browser_ephemeral", strategies

    if user_data_dir is not None:
        strategies.append(
            BrowserContextStrategy(
                name="default_browser_persistent",
                description="默认浏览器 + 持久化用户目录",
                factory=lambda: _launch_default_browser_persistent(
                    playwright,
                    user_data_dir,
                    headless,
                ),
            )
        )
        return "default_browser_persistent", strategies

    strategies.append(
        BrowserContextStrategy(
            name="default_browser_ephemeral",
            description="默认浏览器 + 临时上下文",
            factory=lambda: _launch_default_browser_ephemeral(playwright, headless),
        )
    )
    return "default_browser_ephemeral", strategies


async def launch_tyc_browser_context_async(
    playwright: Playwright,
    browser_executable_path: Path | None = None,
    user_data_dir: Path | None = None,
    headless: bool = False,
) -> tuple[BrowserContext, dict[str, Any]]:
    _ensure_stealth_script_exists()
    requested_mode, strategies = _build_strategies(
        playwright,
        browser_executable_path,
        user_data_dir,
        headless,
    )
    decision = BrowserContextDecision(
        requested_mode=requested_mode,
        fallback_chain=[strategy.name for strategy in strategies],
    )

    for index, strategy in enumerate(strategies):
        logger.info(f"[browser_context_async] 尝试浏览器上下文模式: {strategy.name} ({strategy.description})")
        try:
            context = await strategy.factory()
            await context.add_init_script(path=str(STEALTH_SCRIPT_PATH))
            await load_cookies_async(context)

            decision.resolved_mode = strategy.name
            decision.success = True
            decision.used_fallback = index > 0
            logger.info(f"[browser_context_async] 浏览器上下文创建成功，最终模式: {strategy.name}")
            return context, {
                "requested_mode": decision.requested_mode,
                "resolved_mode": decision.resolved_mode,
                "success": decision.success,
                "used_fallback": decision.used_fallback,
                "fallback_chain": decision.fallback_chain,
                "reason": decision.reason,
                "messages": decision.messages,
            }
        except Exception as exc:
            error_message = str(exc)
            decision.messages.append(f"[browser_context_async] 模式 {strategy.name} 启动失败: {error_message}")
            decision.reason = error_message
            logger.warning(f"[browser_context_async] 模式 {strategy.name} 启动失败: {error_message}")

    raise RuntimeError(f"Failed to create browser context: {decision.reason or 'all strategies failed'}")


async def _launch_full_persistent(
    playwright: Playwright,
    browser_executable_path: Path,
    user_data_dir: Path,
    headless: bool,
) -> BrowserContext:
    _ensure_browser_executable(browser_executable_path)
    _ensure_user_data_dir(user_data_dir)
    return await playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        executable_path=str(browser_executable_path),
        headless=headless,
        slow_mo=100,
        args=["--profile-directory=Default"],
    )


async def _launch_custom_browser_ephemeral(
    playwright: Playwright,
    browser_executable_path: Path,
    headless: bool,
) -> BrowserContext:
    _ensure_browser_executable(browser_executable_path)
    browser = await playwright.chromium.launch(
        executable_path=str(browser_executable_path),
        headless=headless,
        slow_mo=100,
    )
    return await browser.new_context()


async def _launch_default_browser_persistent(
    playwright: Playwright,
    user_data_dir: Path,
    headless: bool,
) -> BrowserContext:
    _ensure_user_data_dir(user_data_dir)
    return await playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=headless,
        slow_mo=100,
        args=["--profile-directory=Default"],
    )


async def _launch_default_browser_ephemeral(playwright: Playwright, headless: bool) -> BrowserContext:
    browser = await playwright.chromium.launch(
        headless=headless,
        slow_mo=100,
    )
    return await browser.new_context()


async def save_cookies_async(context: BrowserContext) -> None:
    try:
        cookies = await context.cookies()
        COOKIES_FILE_PATH.write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"[browser_context_async] 成功保存 cookies: {COOKIES_FILE_PATH}")
    except Exception as exc:
        logger.error(f"[browser_context_async] 保存 cookies 失败: {exc}")


async def load_cookies_async(context: BrowserContext) -> None:
    try:
        if not COOKIES_FILE_PATH.exists():
            logger.info(f"[browser_context_async] 未找到 cookies 文件，跳过加载: {COOKIES_FILE_PATH}")
            return

        cookies = json.loads(COOKIES_FILE_PATH.read_text(encoding="utf-8"))
        await context.add_cookies(cookies)
        logger.info(f"[browser_context_async] 成功加载 cookies: {COOKIES_FILE_PATH}")
    except Exception as exc:
        logger.error(f"[browser_context_async] 加载 cookies 失败: {exc}")