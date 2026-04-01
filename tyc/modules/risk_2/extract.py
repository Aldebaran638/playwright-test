from typing import Any, List, Dict
from datetime import datetime
from playwright.sync_api import Page
from tyc.modules.run_step import run_step


def extract_risk_data(page: Page, company_name: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    前置状态：page 停在该公司风险详情页
    后置状态：page 仍停在该公司风险详情页（不做任何跳转）
    返回：list[dict]，每个 dict 代表一条风险记录
    失败：异常向上抛，由外层 run_step 捕获，整个公司跳过
    """
    # 等待记录列表容器出现
    records_container = page.locator("#search-bar + div > div:nth-child(3)")
    run_step(
        records_container.locator("xpath=./div[1]").wait_for,
        step_name="等待记录列表",
        critical=True,
        retries=2,
    )
    
    # 获取所有记录
    records = run_step(
        lambda: records_container.locator("xpath=./div").all(),
        step_name="获取记录列表",
        critical=True,
        retries=1
    )
    
    result = []
    for record in records.value:
        # 提取标题文本
        title = record.locator("xpath=./div[1]/div[1]").inner_text()
        
        # 提取风险类型
        risk_type = record.locator("xpath=./div[1]/div[2]").inner_text()
        
        # 提取字段
        fields = {}
        label_elements = record.locator("xpath=./div[2]//span[contains(text(),'：')]").all()
        for label_el in label_elements:
            key = label_el.inner_text().rstrip("：:")
            val_els = label_el.locator("xpath=following-sibling::span").all()
            val = "".join(el.inner_text() for el in val_els).strip()
            if key and val:
                fields[key] = val
        
        # 添加到结果
        result.append({
            "title": title,
            "risk_type": risk_type,
            "fields": fields
        })
    
    # 根据日期范围筛选结果
    filtered_result = _filter_by_date(result, start_date, end_date)
    
    return filtered_result


def _filter_by_date(records: List[Dict[str, Any]], start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    根据日期范围筛选记录
    
    Args:
        records: 风险记录列表
        start_date: 起始日期，格式为 "YYYY-MM-DD"
        end_date: 结束日期，格式为 "YYYY-MM-DD"
    
    Returns:
        筛选后的记录列表
    """
    # 解析日期范围
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    filtered = []
    for record in records:
        # 查找日期字段
        date_value = None
        for key, value in record.get("fields", {}).items():
            # 检查字段名是否包含日期相关关键词
            if any(keyword in key for keyword in ["日期", "时间", "刊登", "发布", "发生"]):
                # 提取日期值
                date_str = _extract_date_from_string(value)
                if date_str:
                    try:
                        record_date = datetime.strptime(date_str, "%Y-%m-%d")
                        # 检查日期是否在范围内
                        if start <= record_date <= end:
                            filtered.append(record)
                            break
                    except ValueError:
                        # 日期格式不正确，跳过
                        pass
        
        # 如果没有找到日期字段，默认包含该记录
        else:
            filtered.append(record)
    
    return filtered


def _extract_date_from_string(text: str) -> str:
    """
    从字符串中提取日期
    
    Args:
        text: 包含日期的字符串
    
    Returns:
        提取的日期字符串，格式为 "YYYY-MM-DD"
    """
    # 匹配 YYYY-MM-DD 格式的日期
    import re
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    
    # 匹配 YYYY年MM月DD日 格式的日期
    match = re.search(r"\d{4}年\d{2}月\d{2}日", text)
    if match:
        date_str = match.group(0)
        # 转换为 YYYY-MM-DD 格式
        date_str = date_str.replace("年", "-").replace("月", "-").replace("日", "")
        return date_str
    
    return None
