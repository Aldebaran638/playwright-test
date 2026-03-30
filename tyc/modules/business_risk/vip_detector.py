from loguru import logger
from playwright.sync_api import Page

from tyc.modules.run_step import run_step

# VIP检测关键字
VIP_KEYWORDS = ["VIP", "开通", "会员", "¥", "支付"]


def is_vip_section(page: Page, dim: str) -> bool:
    """
    检测指定data-dim的板块是否为VIP付费板块
    
    Args:
        page: Playwright Page 对象
        dim: 业务标识符，如 "corpIllegals"
        
    Returns:
        bool: 如果是VIP板块返回True，否则返回False
    """
    try:
        # 查找板块容器
        section_container = run_step(
            lambda: page.locator(f"[data-dim='{dim}']"),
            "查找板块容器",
            page_getter=lambda: page
        )
        if run_step(
            lambda: section_container.count(),
            "获取板块容器数量",
            page_getter=lambda: page
        ) == 0:
            return False
        
        # 提取板块标题（用于日志）
        section_title = "未知板块"
        elements = run_step(
            lambda: section_container.locator("*").all(),
            "获取容器内所有元素",
            page_getter=lambda: page
        )
        for element in elements:
            text = element.inner_text().strip()
            if text:
                section_title = text
                break
        
        # VIP检测
        container_text = run_step(
            lambda: section_container.inner_text().lower(),
            "获取容器文本",
            page_getter=lambda: page
        )
        keyword_count = 0
        for keyword in VIP_KEYWORDS:
            if keyword.lower() in container_text:
                keyword_count += 1
        
        if keyword_count >= 2:
            # 判定为VIP板块
            section_title_for_log = section_title if section_title != "未知板块" else dim
            logger.warning(f"[模块] 板块 '{section_title_for_log}' 需要会员权限，已跳过")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"[模块] 检测VIP板块时出错: {e}")
        return False
