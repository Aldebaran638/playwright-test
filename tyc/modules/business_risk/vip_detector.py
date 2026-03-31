from loguru import logger
from playwright.sync_api import Page

from tyc.modules.run_step import run_step


VIP_KEYWORDS = ["VIP", "开通", "会员", "¥", "支付"]


def _get_section_title(page: Page, dim: str) -> str:
    """获取板块的中文名称"""
    container = page.locator(f"[data-dim='{dim}']")
    try:
        # 尝试获取板块标题
        title_element = container.locator("h3, h4, .title, .name").first
        if title_element.count() > 0:
            title = title_element.inner_text().strip()
            if title:
                return title
        
        # 如果没有找到标题元素，尝试获取第一个非空文本
        container_text = container.inner_text().strip()
        if container_text:
            # 取前50个字符作为标题
            return container_text[:50]
    except Exception:
        pass
    return f"板块({dim})"


def is_vip_section(page: Page, dim: str) -> bool:
    section_title = _get_section_title(page, dim)
    logger.info(f"[business_risk.vip_detector] 开始检测板块是否为 VIP: {dim} ({section_title})")

    container = page.locator(f"[data-dim='{dim}']")
    count_result = run_step(
        container.count,
        step_name=f"检查板块容器是否存在: {dim} ({section_title})",
        critical=False,
        retries=0,
    )
    if not count_result.ok or not count_result.value:
        logger.info(f"[business_risk.vip_detector] 未找到板块容器，按非 VIP 处理: {dim} ({section_title})")
        return False

    text_result = run_step(
        container.first.inner_text,
        step_name=f"读取板块文本以检测 VIP: {dim} ({section_title})",
        critical=False,
        retries=0,
    )
    if not text_result.ok or text_result.value is None:
        logger.warning(f"[business_risk.vip_detector] 读取板块文本失败，按非 VIP 处理: {dim} ({section_title})")
        return False

    container_text = str(text_result.value).lower()
    keyword_count = sum(1 for keyword in VIP_KEYWORDS if keyword.lower() in container_text)
    if keyword_count >= 2:
        logger.warning(f"[business_risk.vip_detector] 板块需要会员权限，已跳过: {dim} ({section_title})")
        return True

    logger.info(f"[business_risk.vip_detector] 板块可正常访问: {dim} ({section_title})")
    return False
