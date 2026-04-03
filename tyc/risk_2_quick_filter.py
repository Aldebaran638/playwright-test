import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2.risk_filter import filter_risk_records
from loguru import logger


# ═══════════════════════════════════════════════════════════════
# 配置区域 - 在这里修改输入文件和筛选规则
# ═══════════════════════════════════════════════════════════════

# 输入文件路径（相对于当前文件所在目录）
INPUT_FILE = "risk_2_results.json"

# 输出文件路径（如果为 None，则自动生成）
OUTPUT_FILE = None

# 自定义筛选规则（如果为 None，则使用模块中的默认规则）
CUSTOM_RULES = [
    {
        "risk_type": "开庭公告",
        "fields": ["开庭时间"]
    },
    {
        "risk_type": "立案信息",
        "fields": ["立案日期"]
    },
    {
        "risk_type": "裁判文书",
        "fields": ["发布日期", "案号"]
    },
    {
        "risk_type": "法院公告",
        "fields": ["案由", "刊登日期"]
    },
    {
        "risk_type": "经营异常",
        "fields": ["列入日期", "列入原因"]
    },
    {
        "risk_type": "限制消费令",
        "fields": ["发布日期"]
    },
    {
        "risk_type": "行政处罚",
        "fields": ["处罚日期", "处罚事由"]
    },
    {
        "risk_type": "严重违法",
        "fields": ["列入日期", "列入原因"]
    },
]

# ═══════════════════════════════════════════════════════════════

def main():
    """执行筛选"""
    logger.info("=" * 60)
    logger.info("开始执行风险记录筛选")
    logger.info("=" * 60)

    input_path = Path(__file__).parent / INPUT_FILE

    if OUTPUT_FILE:
        output_path = Path(__file__).parent / OUTPUT_FILE
    else:
        output_path = None

    logger.info(f"输入文件: {input_path}")
    logger.info(f"输出文件: {output_path if output_path else '(自动生成)'}")

    if CUSTOM_RULES:
        logger.info(f"使用自定义筛选规则，共 {len(CUSTOM_RULES)} 条:")
        for i, rule in enumerate(CUSTOM_RULES, 1):
            logger.info(f"  规则 {i}:")
            logger.info(f"    风险类型: {rule['risk_type']}")
            logger.info(f"    保留字段: {rule['fields'] if rule['fields'] else '(清空所有字段)'}")
    else:
        logger.info("使用模块默认筛选规则")

    logger.info("-" * 60)

    result = filter_risk_records(
        input_file=input_path,
        output_file=output_path,
        custom_rules=CUSTOM_RULES
    )

    if result:
        logger.info("-" * 60)
        logger.info("筛选完成!")
        logger.info(f"成功处理公司数: {len(result.get('successful_results', []))}")
        logger.info(f"失败公司数: {len(result.get('failed_companies', []))}")

        total_records = 0
        for company in result.get("successful_results", []):
            total_records += len(company.get("risk_records", []))
        logger.info(f"筛选后总记录数: {total_records}")
    else:
        logger.error("筛选失败!")

    logger.info("=" * 60)


if __name__ == "__main__":
    main()
