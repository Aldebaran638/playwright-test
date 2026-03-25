"""Lightweight timeout retry helper for Playwright UI actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar

from loguru import logger
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


P = ParamSpec("P")
R = TypeVar("R")


def run_with_timeout_retry(
    action_name: str,
    page: Page,
    wait_before_action: Callable[[Page, float | None], None],
    action: Callable[[], R],
    max_attempts: int = 3,
) -> R:
    """Retry a UI action when Playwright times out because the page is slow to render."""
    last_error: PlaywrightTimeoutError | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return action()
        except PlaywrightTimeoutError as error:
            last_error = error
            if attempt >= max_attempts:
                logger.error(
                    "动作 {action} 在 {attempts} 次尝试后仍然超时",
                    action=action_name,
                    attempts=max_attempts,
                )
                raise

            logger.warning(
                "动作 {action} 第 {attempt} 次执行超时，等待后重试",
                action=action_name,
                attempt=attempt,
            )
            wait_before_action(page)

    assert last_error is not None
    raise last_error
