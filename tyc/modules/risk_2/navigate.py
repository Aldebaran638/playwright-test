from playwright.sync_api import Page
from tyc.modules.common.run_step import run_step
import re
import logging

# 配置日志
logger = logging.getLogger(__name__)


def navigate_to_risk_page(page: Page, company_name: str) -> bool:
    """
    前置状态：page 停在「查风险」搜索页（有搜索框）
    后置状态：page 停在该公司风险详情页
    失败：异常向上抛，由外层 run_step 捕获
    
    Returns:
        bool: True 表示找到风险信息，False 表示未找到风险信息
    """
    # 清空并填入搜索框（找本页面出现的第一个搜索框）
    search_box = page.get_by_role("textbox").first
    run_step(
        search_box.fill,
        company_name,
        step_name="填入公司名称到搜索框",
        critical=True,
        retries=1,
    )
    
    # 点击搜索按钮（找文本中带有"搜索"或者"天眼一下"字样的按钮）
    # 尝试不同的定位方式
    search_buttons = page.get_by_role("button").all()
    found = False
    for button in search_buttons:
        try:
            text = button.inner_text()
            if "搜索" in text or "天眼一下" in text:
                run_step(
                    button.click,
                    step_name="点击搜索按钮",
                    critical=True,
                    retries=1,
                )
                found = True
                break
        except Exception:
            continue
    
    if not found:
        # 如果没有找到带有指定文本的按钮，尝试点击第一个按钮
        first_button = page.get_by_role("button").first
        run_step(
            first_button.click,
            step_name="点击第一个按钮作为搜索按钮",
            critical=True,
            retries=1,
        )
    
    # 检查第一个子元素中是否有独立包装的数字
    # 如果找到的结果是0，说明没有找到符合条件的内容，直接跳过等待
    search_bar = page.locator("#search-bar")
    if search_bar.count() > 0:
        # 找到 #search-bar 的兄弟元素
        sibling_div = search_bar.locator("+ div")
        if sibling_div.count() > 0:
            # 直接查找第一个子元素，不使用 class 定位
            first_child = sibling_div.locator("div:nth-child(1)")
            
            if first_child.count() > 0:
                # 查找独立包装的数字
                number_elements = first_child.locator("div, span").all()
                for element in number_elements:
                    try:
                        text = element.inner_text().strip()
                        # 检查是否是独立的数字
                        if re.fullmatch(r"\d+", text):
                            # 如果数字是0，说明没有找到符合条件的内容
                            if text == "0":
                                logger.info(f"[risk_2.navigate] 未找到 {company_name} 的风险信息，跳过等待")
                                return False
                            else:
                                # 输出日志提示开发者当前找到了几条风险信息
                                logger.info(f"[risk_2.navigate] 找到了 {company_name} 的 {text} 条风险信息")
                            break
                    except Exception:
                        continue
    
    # 等待风险详情页加载完成
    records_container = page.locator("#search-bar + div > div:nth-child(3)")
    run_step(
        records_container.locator("xpath=./div[1]").wait_for,
        step_name="等待风险详情页加载完成",
        critical=True,
        retries=2,
    )
    
    return True
