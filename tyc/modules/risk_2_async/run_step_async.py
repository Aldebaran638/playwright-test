from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, TypeVar

from loguru import logger
from playwright.async_api import Page, TimeoutError


T = TypeVar("T")


@dataclass(slots=True)
class StepResult(Generic[T]):
    ok: bool
    value: T | None = None
    error: Exception | None = None


async def run_step_async(
    fn: Callable[..., Awaitable[T]],
    *args: Any,
    step_name: str = "",
    critical: bool = False,
    retries: int = 0,
    **kwargs: Any,
) -> StepResult[T]:
    name = step_name or getattr(fn, "__name__", "未命名步骤")
    last_error: Exception | None = None

    page: Page | None = None
    for arg in args:
        if isinstance(arg, Page):
            page = arg
            break
    for value in kwargs.values():
        if isinstance(value, Page):
            page = value
            break

    for attempt in range(retries + 1):
        if attempt > 0:
            logger.info(f'[run_step_async] 步骤"{name}" 第{attempt}次重试...')

        await asyncio.sleep(random.uniform(0.3, 0.6))

        try:
            value = await fn(*args, **kwargs)
            logger.info(f'[run_step_async] 步骤"{name}" 执行成功')
            return StepResult(ok=True, value=value, error=None)
        except TimeoutError as exc:
            last_error = exc
            if page is not None:
                logger.warning(f'[run_step_async] 步骤"{name}" 超时: {exc}')
        except Exception as exc:
            last_error = exc

    if last_error is None:
        last_error = RuntimeError(f'步骤"{name}" 执行失败，但没有捕获到具体异常')

    if critical:
        logger.error(f'[run_step_async] 步骤"{name}" 失败，流程中止。错误: {last_error}')
        raise last_error

    logger.warning(f'[run_step_async] 步骤"{name}" 失败，已跳过。错误: {last_error}')
    return StepResult(ok=False, value=None, error=last_error)