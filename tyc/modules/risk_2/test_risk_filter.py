import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2.risk_filter import (
    filter_risk_records,
    get_available_risk_types,
    get_available_fields,
    FILTER_RULES
)
from loguru import logger


def test_get_available_risk_types():
    """测试获取可用风险类型"""
    logger.info("=" * 60)
    logger.info("测试 1: 获取可用风险类型")
    logger.info("=" * 60)
    
    input_file = Path(__file__).parent / "risk_2_results.json"
    
    if not input_file.exists():
        logger.warning(f"测试文件不存在: {input_file}")
        return
    
    risk_types = get_available_risk_types(input_file)
    
    logger.info(f"发现的风险类型数量: {len(risk_types)}")
    for i, risk_type in enumerate(risk_types, 1):
        logger.info(f"  {i}. {risk_type}")


def test_get_available_fields():
    """测试获取可用字段"""
    logger.info("=" * 60)
    logger.info("测试 2: 获取可用字段")
    logger.info("=" * 60)
    
    input_file = Path(__file__).parent / "risk_2_results.json"
    
    if not input_file.exists():
        logger.warning(f"测试文件不存在: {input_file}")
        return
    
    risk_types = get_available_risk_types(input_file)
    
    for risk_type in risk_types[:5]:
        logger.info(f"\n风险类型: {risk_type}")
        fields = get_available_fields(input_file, risk_type)
        for i, field in enumerate(fields, 1):
            logger.info(f"  {i}. {field}")


def test_filter_with_default_rules():
    """测试使用默认规则筛选"""
    logger.info("=" * 60)
    logger.info("测试 3: 使用默认规则筛选")
    logger.info("=" * 60)
    
    input_file = Path(__file__).parent / "risk_2_results.json"
    output_file = Path(__file__).parent / "risk_2_results_filtered_default.json"
    
    if not input_file.exists():
        logger.warning(f"测试文件不存在: {input_file}")
        return
    
    logger.info("默认筛选规则:")
    for i, rule in enumerate(FILTER_RULES, 1):
        logger.info(f"  规则 {i}:")
        logger.info(f"    风险类型: {rule['risk_type']}")
        logger.info(f"    保留字段: {rule['fields'] if rule['fields'] else '(全部清空)'}")
    
    filtered_data = filter_risk_records(input_file, output_file)
    
    if filtered_data:
        logger.info(f"\n筛选完成，结果已保存到: {output_file}")
        logger.info(f"成功处理公司数: {len(filtered_data.get('successful_results', []))}")
    else:
        logger.error("筛选失败")


def test_filter_with_custom_rules():
    """测试使用自定义规则筛选"""
    logger.info("=" * 60)
    logger.info("测试 4: 使用自定义规则筛选")
    logger.info("=" * 60)
    
    input_file = Path(__file__).parent / "risk_2_results.json"
    output_file = Path(__file__).parent / "risk_2_results_filtered_custom.json"
    
    if not input_file.exists():
        logger.warning(f"测试文件不存在: {input_file}")
        return
    
    custom_rules = [
        {
            "risk_type": "开庭公告",
            "fields": ["原告", "被告", "案由", "开庭时间", "法院"]
        },
        {
            "risk_type": "法院公告",
            "fields": ["被告", "原告", "案由", "法院", "刊登日期"]
        },
        {
            "risk_type": "限制消费令",
            "fields": ["限消令对象", "申请人", "执行法院", "发布日期"]
        },
    ]
    
    logger.info("自定义筛选规则:")
    for i, rule in enumerate(custom_rules, 1):
        logger.info(f"  规则 {i}:")
        logger.info(f"    风险类型: {rule['risk_type']}")
        logger.info(f"    保留字段: {rule['fields']}")
    
    filtered_data = filter_risk_records(input_file, output_file, custom_rules)
    
    if filtered_data:
        logger.info(f"\n筛选完成，结果已保存到: {output_file}")
        logger.info(f"成功处理公司数: {len(filtered_data.get('successful_results', []))}")
    else:
        logger.error("筛选失败")


def test_filter_empty_fields():
    """测试清空字段的筛选"""
    logger.info("=" * 60)
    logger.info("测试 5: 清空字段的筛选")
    logger.info("=" * 60)
    
    input_file = Path(__file__).parent / "risk_2_results.json"
    output_file = Path(__file__).parent / "risk_2_results_filtered_empty.json"
    
    if not input_file.exists():
        logger.warning(f"测试文件不存在: {input_file}")
        return
    
    risk_types = get_available_risk_types(input_file)
    
    if not risk_types:
        logger.warning("没有找到风险类型")
        return
    
    custom_rules = [
        {
            "risk_type": risk_types[0],
            "fields": []
        }
    ]
    
    logger.info(f"清空字段规则:")
    logger.info(f"  风险类型: {risk_types[0]}")
    logger.info(f"  保留字段: (清空所有字段)")
    
    filtered_data = filter_risk_records(input_file, output_file, custom_rules)
    
    if filtered_data:
        logger.info(f"\n筛选完成，结果已保存到: {output_file}")
        logger.info(f"成功处理公司数: {len(filtered_data.get('successful_results', []))}")
    else:
        logger.error("筛选失败")


def main():
    """运行所有测试"""
    logger.info("开始运行筛选器测试")
    logger.info("=" * 60)
    
    test_get_available_risk_types()
    logger.info("\n")
    
    test_get_available_fields()
    logger.info("\n")
    
    test_filter_with_default_rules()
    logger.info("\n")
    
    test_filter_with_custom_rules()
    logger.info("\n")
    
    test_filter_empty_fields()
    logger.info("\n")
    
    logger.info("=" * 60)
    logger.info("所有测试完成")


if __name__ == "__main__":
    main()
