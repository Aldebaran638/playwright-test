import re
from loguru import logger
from playwright.sync_api import Page


def extract_tag_nav_texts(page: Page) -> list[tuple[str, str]]:
    """
    根据id="JS_tag_nav"，抓取元素中的非纯数字文本及其后面的数字
    
    Args:
        page: Playwright Page 对象
        
    Returns:
        list[tuple[str, str]]: 二元数组，每个元素为(文本, 数字)
    """
    logger.info("[模块] 开始提取JS_tag_nav中的非纯数字文本及其数字")
    
    try:
        # 找到JS_tag_nav元素，id匹配
        tag_nav = page.locator("#JS_tag_nav")
        
        # 获取所有子元素
        children = tag_nav.locator("> *").all()
        
        # 存储二元数组
        result = []
        
        for child in children:
            # 获取元素的文本内容
            text = child.inner_text()
            
            # 提取非数字部分和数字部分
            # 匹配最后一个数字序列
            match = re.search(r"(.*?)(\d+)$", text.strip())
            if match:
                non_numeric_part = match.group(1).strip()
                numeric_part = match.group(2)
                
                # 检查是否为非纯数字文本
                if non_numeric_part and not non_numeric_part.isdigit():
                    result.append((non_numeric_part, numeric_part))
            else:
                # 没有数字的情况
                non_numeric_part = text.strip()
                if non_numeric_part and not non_numeric_part.isdigit():
                    result.append((non_numeric_part, "0"))
        
        logger.info(f"[模块] 提取到 {len(result)} 个二元组")
        logger.info(f"[模块] 提取的二元组: {result}")
        
        return result
    except Exception as e:
        logger.error(f"[模块] 提取JS_tag_nav文本失败: {e}")
        return []
