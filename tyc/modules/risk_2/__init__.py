"""
风险2分析模块
用于从天眼查查风险功能中提取公司风险信息
"""

from tyc.modules.risk_2.risk_2_main import process_risk_2, main
from tyc.modules.risk_2.navigate import navigate_to_risk_page
from tyc.modules.risk_2.extract import extract_risk_data

__all__ = [
    "process_risk_2",
    "main",
    "navigate_to_risk_page",
    "extract_risk_data",
]