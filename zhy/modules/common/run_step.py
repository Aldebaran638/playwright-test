from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, TypeVar

from loguru import logger


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
    retry_delay_seconds: float = 0.0,
    **kwargs: Any,
) -> StepResult[T]:
    name = step_name or getattr(fn, "__name__", "unnamed_step")
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        if attempt > 0:
            logger.info(
                '[run_step] retry step "{}" attempt {}/{}',
                name,
                attempt,
                retries,
            )
            if retry_delay_seconds > 0:
                await asyncio.sleep(retry_delay_seconds)

        try:
            value = await fn(*args, **kwargs)
            logger.info('[run_step] step "{}" succeeded', name)
            return StepResult(ok=True, value=value, error=None)
        except Exception as exc:
            last_error = exc

    if last_error is None:
        last_error = RuntimeError(f'step "{name}" failed without a captured exception')

    if critical:
        logger.error('[run_step] step "{}" failed and stops the pipeline: {}', name, last_error)
        raise last_error

    logger.warning('[run_step] step "{}" failed and will be skipped: {}', name, last_error)
    return StepResult(ok=False, value=None, error=last_error)
