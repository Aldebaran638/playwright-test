import json
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger


# ═══════════════════════════════════════════════════════════════
# 筛选规则配置区域
# ═══════════════════════════════════════════════════════════════

FILTER_RULES = [
    {
        "risk_type": "立案信息",
        "fields": ["原告", "法院"]
    },
    {
        "risk_type": "行政处罚",
        "fields": []
    },
]

# ═══════════════════════════════════════════════════════════════


def filter_risk_records(
    input_file: str | Path,
    output_file: str | Path | None = None,
    custom_rules: List[Dict[str, Any]] | None = None
) -> Dict[str, Any]:
    """
    根据筛选规则筛选风险记录
    
    Args:
        input_file: 输入JSON文件路径
        output_file: 输出JSON文件路径，如果为None则自动生成
        custom_rules: 自定义筛选规则，如果为None则使用默认规则
    
    Returns:
        筛选后的数据
    """
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"[risk_filter] 输入文件不存在: {input_path}")
        return {}
    
    if output_file is None:
        output_path = input_path.parent / f"{input_path.stem}_filtered.json"
    else:
        output_path = Path(output_file)
    
    rules = custom_rules if custom_rules is not None else FILTER_RULES
    
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"[risk_filter] 成功读取输入文件: {input_path}")
        
        filtered_data = _apply_filter_rules(data, rules)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[risk_filter] 筛选结果已保存到: {output_path}")
        
        return filtered_data
        
    except Exception as e:
        logger.error(f"[risk_filter] 处理过程中发生错误: {e}")
        return {}


def _apply_filter_rules(data: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    应用筛选规则到数据
    
    Args:
        data: 原始数据
        rules: 筛选规则列表
    
    Returns:
        筛选后的数据
    """
    filtered_data = {
        "analysis_params": data.get("analysis_params", {}),
        "successful_results": [],
        "failed_companies": data.get("failed_companies", [])
    }
    
    total_records = 0
    filtered_records = 0
    
    for company_result in data.get("successful_results", []):
        company_name = company_result.get("company_name", "")
        original_records = company_result.get("risk_records", [])
        
        filtered_company_records = []
        
        for record in original_records:
            total_records += 1
            risk_type = record.get("risk_type", "")
            
            matching_rule = None
            for rule in rules:
                if rule.get("risk_type") == risk_type:
                    matching_rule = rule
                    break
            
            if matching_rule:
                filtered_records += 1
                filtered_record = _filter_single_record(record, matching_rule)
                filtered_company_records.append(filtered_record)
        
        if filtered_company_records:
            filtered_company_result = {
                "company_name": company_name,
                "success": True,
                "risk_records": filtered_company_records
            }
            filtered_data["successful_results"].append(filtered_company_result)
    
    logger.info(f"[risk_filter] 总记录数: {total_records}, 筛选后记录数: {filtered_records}")
    
    return filtered_data


def _filter_single_record(record: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据规则筛选单条记录
    
    Args:
        record: 原始记录
        rule: 筛选规则
    
    Returns:
        筛选后的记录
    """
    filtered_record = {
        "title": record.get("title", ""),
        "risk_type": record.get("risk_type", ""),
        "fields": {}
    }
    
    fields_to_keep = rule.get("fields", [])
    original_fields = record.get("fields", {})
    
    if not fields_to_keep:
        return filtered_record
    
    for field_name in fields_to_keep:
        if field_name in original_fields:
            filtered_record["fields"][field_name] = original_fields[field_name]
    
    return filtered_record


def get_available_risk_types(input_file: str | Path) -> List[str]:
    """
    获取输入文件中所有可用的风险类型
    
    Args:
        input_file: 输入JSON文件路径
    
    Returns:
        风险类型列表
    """
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"[risk_filter] 输入文件不存在: {input_path}")
        return []
    
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        risk_types = set()
        for company_result in data.get("successful_results", []):
            for record in company_result.get("risk_records", []):
                risk_type = record.get("risk_type", "")
                if risk_type:
                    risk_types.add(risk_type)
        
        result = sorted(list(risk_types))
        logger.info(f"[risk_filter] 发现 {len(result)} 种风险类型: {result}")
        return result
        
    except Exception as e:
        logger.error(f"[risk_filter] 读取文件时发生错误: {e}")
        return []


def get_available_fields(input_file: str | Path, risk_type: str) -> List[str]:
    """
    获取指定风险类型的所有可用字段
    
    Args:
        input_file: 输入JSON文件路径
        risk_type: 风险类型
    
    Returns:
        字段列表
    """
    input_path = Path(input_file)
    if not input_path.exists():
        logger.error(f"[risk_filter] 输入文件不存在: {input_path}")
        return []
    
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        fields = set()
        for company_result in data.get("successful_results", []):
            for record in company_result.get("risk_records", []):
                if record.get("risk_type") == risk_type:
                    for field_name in record.get("fields", {}).keys():
                        fields.add(field_name)
        
        result = sorted(list(fields))
        logger.info(f"[risk_filter] 风险类型 '{risk_type}' 发现 {len(result)} 个字段: {result}")
        return result
        
    except Exception as e:
        logger.error(f"[risk_filter] 读取文件时发生错误: {e}")
        return []
