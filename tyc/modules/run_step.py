import random
import time
from typing import Callable, TypeVar

from loguru import logger
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from tyc.modules.page_guard import check_page
from tyc.modules.wait_for_recovery import wait_until_page_recovered


T = TypeVar("T")

DEFAULT_MAX_RETRIES = 3
DEFAULT_MIN_DELAY_SECONDS = 0.5
DEFAULT_MAX_DELAY_SECONDS = 2.0


def run_step(
    action: Callable[[], T],
    step_name: str,
    *,
    page_getter: Callable[[], Page] | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    min_delay_seconds: float = DEFAULT_MIN_DELAY_SECONDS,
    max_delay_seconds: float = DEFAULT_MAX_DELAY_SECONDS,
    sleep_func: Callable[[float], None] = time.sleep,
    random_func: Callable[[float, float], float] = random.uniform,
    check_page_func=check_page,
    recovery_func=wait_until_page_recovered,
) -> T:
    # 统一封装 Playwright 步骤的超时重试、非法页检查和随机停顿。
    retry_count = 0

    while True:
        try:
            result = action()
            delay_seconds = random_func(min_delay_seconds, max_delay_seconds)
            logger.info(f"[模块] 步骤完成: {step_name}，随机等待 {delay_seconds:.2f} 秒")
            sleep_func(delay_seconds)
            return result
        except (PlaywrightTimeoutError, TimeoutError) as exc:
            # 如果当前已经落入非法页面，先等待用户处理，再重试当前元步骤。
            if page_getter is not None:
                page = page_getter()
                guard_result = check_page_func(page)
                if guard_result.is_illegal:
                    logger.warning(
                        f"[模块] 步骤失败后检测到非法页面: {guard_result.page_type}，"
                        "转入人工处理等待"
                    )
                    recovery_func(page_getter, check_page_func=check_page_func)
                    continue

            # 普通超时按固定次数重试，超过上限后再抛出异常。
            if retry_count >= max_retries:
                logger.error(f"[模块] 步骤失败且已达到重试上限: {step_name}")
                raise exc

            retry_count += 1
            logger.warning(
                f"[模块] 步骤超时，准备重试: {step_name}，"
                f"第 {retry_count} 次重试 / 共 {max_retries} 次"
            )
