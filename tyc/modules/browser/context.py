import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from loguru import logger
from playwright.sync_api import BrowserContext, Playwright

from tyc.modules.common.run_step import run_step


STEALTH_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "assets" / "stealth.min.js"
COOKIES_FILE_PATH = Path(__file__).resolve().parents[2] / "cookies.json"


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
    factory: Callable[[], BrowserContext]

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
                ),
            )
        )
        strategies.append(
            BrowserContextStrategy(
                name="default_browser_persistent",
                description="默认浏览器 + 持久化用户目录",
                factory=lambda: _launch_default_browser_persistent(
                    playwright,
                    user_data_dir,
                ),
            )
        )
        strategies.append(
            BrowserContextStrategy(
                name="default_browser_ephemeral",
                description="默认浏览器 + 临时上下文",
                factory=lambda: _launch_default_browser_ephemeral(playwright),
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
                ),
            )
        )
        strategies.append(
            BrowserContextStrategy(
                name="default_browser_ephemeral",
                description="默认浏览器 + 临时上下文",
                factory=lambda: _launch_default_browser_ephemeral(playwright),
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
                ),
            )
        )
        strategies.append(
            BrowserContextStrategy(
                name="default_browser_ephemeral",
                description="默认浏览器 + 临时上下文",
                factory=lambda: _launch_default_browser_ephemeral(playwright),
            )
        )
        return "default_browser_persistent", strategies

    strategies.append(
        BrowserContextStrategy(
            name="default_browser_ephemeral",
            description="默认浏览器 + 临时上下文",
            factory=lambda: _launch_default_browser_ephemeral(playwright),
        )
    )
    return "default_browser_ephemeral", strategies


def launch_tyc_browser_context(
    playwright: Playwright,
    browser_executable_path: Path | None = None,
    user_data_dir: Path | None = None,
) -> tuple[BrowserContext, dict[str, Any]]:
    _ensure_stealth_script_exists()
    requested_mode, strategies = _build_strategies(
        playwright,
        browser_executable_path,
        user_data_dir,
    )
    decision = BrowserContextDecision(
        requested_mode=requested_mode,
        fallback_chain=[strategy.name for strategy in strategies],
    )

    for index, strategy in enumerate(strategies):
        logger.info(
            f"[browser_context] 尝试浏览器上下文模式: {strategy.name} ({strategy.description})"
        )
        launch_result = run_step(
            strategy.factory,
            step_name=f"启动浏览器上下文模式: {strategy.name}",
            critical=False,
            retries=0,
        )
        if not launch_result.ok or launch_result.value is None:
            error_message = str(launch_result.error) if launch_result.error is not None else "unknown error"
            message = f"[browser_context] 模式 {strategy.name} 启动失败: {error_message}"
            decision.messages.append(message)
            decision.reason = error_message
            logger.warning(message)
            continue

        context = launch_result.value
        context.add_init_script(path=str(STEALTH_SCRIPT_PATH))
        load_cookies(context)

        decision.resolved_mode = strategy.name
        decision.success = True
        decision.used_fallback = index > 0
        decision.reason = ""
        logger.info(f"[browser_context] 浏览器上下文创建成功，最终模式: {strategy.name}")
        return context, {
            "requested_mode": decision.requested_mode,
            "resolved_mode": decision.resolved_mode,
            "success": decision.success,
            "used_fallback": decision.used_fallback,
            "fallback_chain": decision.fallback_chain,
            "reason": decision.reason,
            "messages": decision.messages,
        }

    raise RuntimeError(f"Failed to create browser context: {decision.reason or 'all strategies failed'}")


def _launch_full_persistent(
    playwright: Playwright,
    browser_executable_path: Path,
    user_data_dir: Path,
) -> BrowserContext:
    _ensure_browser_executable(browser_executable_path)
    _ensure_user_data_dir(user_data_dir)
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        executable_path=str(browser_executable_path),
        headless=False,
        slow_mo=100,
        args=["--profile-directory=Default"],
    )


def _launch_custom_browser_ephemeral(
    playwright: Playwright,
    browser_executable_path: Path,
) -> BrowserContext:
    _ensure_browser_executable(browser_executable_path)
    browser = playwright.chromium.launch(
        executable_path=str(browser_executable_path),
        headless=False,
        slow_mo=100,
    )
    return browser.new_context()


def _launch_default_browser_persistent(
    playwright: Playwright,
    user_data_dir: Path,
) -> BrowserContext:
    _ensure_user_data_dir(user_data_dir)
    return playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=False,
        slow_mo=100,
        args=["--profile-directory=Default"],
    )


def _launch_default_browser_ephemeral(playwright: Playwright) -> BrowserContext:
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=100,
    )
    return browser.new_context()


def save_cookies(context: BrowserContext) -> None:
    try:
        cookies = context.cookies()
        COOKIES_FILE_PATH.write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"[browser_context] 成功保存 cookies: {COOKIES_FILE_PATH}")
    except Exception as exc:
        logger.error(f"[browser_context] 保存 cookies 失败: {exc}")


def load_cookies(context: BrowserContext) -> None:
    try:
        if not COOKIES_FILE_PATH.exists():
            logger.info(f"[browser_context] 未找到 cookies 文件，跳过加载: {COOKIES_FILE_PATH}")
            return

        cookies = json.loads(COOKIES_FILE_PATH.read_text(encoding="utf-8"))
        context.add_cookies(cookies)
        logger.info(f"[browser_context] 成功加载 cookies: {COOKIES_FILE_PATH}")
    except Exception as exc:
        logger.error(f"[browser_context] 加载 cookies 失败: {exc}")
