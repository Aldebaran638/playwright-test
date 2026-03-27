from typing import Callable

from loguru import logger
from playwright.sync_api import Page

from tyc.modules.page_guard import check_page


WAIT_INTERVAL_MS = 3000


def wait_until_page_recovered(
    page_getter: Callable[[], Page],
    *,
    check_page_func: Callable[[Page], object] = check_page,
    wait_interval_ms: int = WAIT_INTERVAL_MS,
) -> None:
    # 阻塞等待用户处理非法页面，直到页面恢复正常。
    logger.warning("[模块] 当前页面需要人工处理，系统将每 3 秒检查一次是否已恢复")

    while True:
        page = page_getter()
        guard_result = check_page_func(page)

        # 页面恢复正常后结束阻塞，交还给当前失败步骤继续重试。
        if not guard_result.is_illegal:
            logger.info("[模块] 页面已恢复正常，继续执行当前步骤")
            return

        logger.warning(f"[模块] 仍处于非法页面: {guard_result.page_type}，请继续手动处理")
        page.wait_for_timeout(wait_interval_ms)
