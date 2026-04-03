from typing import Callable

from loguru import logger
from playwright.sync_api import Page

from tyc.modules.browser.page_guard import PageGuardResult, check_page


WAIT_INTERVAL_MS = 3000


def wait_until_page_recovered(
    page_getter: Callable[[], Page],
    *,
    check_page_func: Callable[[Page], PageGuardResult] = check_page,
    wait_interval_ms: int = WAIT_INTERVAL_MS,
) -> None:
    logger.warning("[wait_for_recovery] 当前页面需要人工处理，系统将每 3 秒检查一次是否已恢复")

    while True:
        page = page_getter()
        guard_result = check_page_func(page)

        # 页面恢复正常后结束阻塞，把控制权交还给当前流程函数。
        if not guard_result.is_illegal:
            logger.info("[wait_for_recovery] 页面已恢复正常，继续执行当前流程")
            return

        logger.warning(
            f"[wait_for_recovery] 页面仍未恢复，当前状态: {guard_result.page_type}，请继续手动处理"
        )
        page.wait_for_timeout(wait_interval_ms)
