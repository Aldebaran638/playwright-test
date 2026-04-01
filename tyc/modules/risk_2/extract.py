from typing import Any, List, Dict
from playwright.sync_api import Page
from tyc.modules.run_step import run_step


def extract_risk_data(page: Page, company_name: str) -> List[Dict[str, Any]]:
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
    
    return result
