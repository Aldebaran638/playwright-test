import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from loguru import logger


T = TypeVar("T")


@dataclass(slots=True)
class StepResult(Generic[T]):
    ok: bool
    value: T | None = None
    error: Exception | None = None


def run_step(
    fn: Callable[..., T],
    *args: Any,
    step_name: str = "",
    critical: bool = False,
    retries: int = 0,
    **kwargs: Any,
) -> StepResult[T]:
    name = step_name or getattr(fn, "__name__", "未命名步骤")
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        if attempt > 0:
            logger.info(f'[run_step] 步骤"{name}" 第{attempt}次重试...')

        delay = random.uniform(0.5, 0.8)
        time.sleep(delay)

        try:
            value = fn(*args, **kwargs)
            logger.info(f'[run_step] 步骤"{name}" 执行成功')
            return StepResult(ok=True, value=value, error=None)
        except Exception as exc:
            last_error = exc

    if last_error is None:
        last_error = RuntimeError(f'步骤"{name}" 执行失败，但没有捕获到具体异常')

    if critical:
        logger.error(f'[run_step] 步骤"{name}" 失败，流程中止。错误: {last_error}')
        raise last_error

    logger.warning(f'[run_step] 步骤"{name}" 失败，已跳过。错误: {last_error}')
    return StepResult(ok=False, value=None, error=last_error)
