import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2.db_uploader import (
    upload_risk_data_to_db,
    test_db_connection,
    get_db_config
)
from loguru import logger


# ═══════════════════════════════════════════════════════════════
# 配置区域
# ═══════════════════════════════════════════════════════════════

# 输入文件路径（相对于当前文件所在目录）
INPUT_FILE = "risk_2_results.json"

# ═══════════════════════════════════════════════════════════════


def test_connection():
    """测试数据库连接"""
    logger.info("=" * 60)
    logger.info("测试 1: 数据库连接测试")
    logger.info("=" * 60)
    
    config = get_db_config()
    logger.info("当前数据库配置:")
    logger.info(f"  主机: {config['host']}")
    logger.info(f"  端口: {config['port']}")
    logger.info(f"  用户: {config['user']}")
    logger.info(f"  数据库: {config['database']}")
    logger.info(f"  表名: {config['table']}")
    
    success = test_db_connection()
    
    if success:
        logger.info("✓ 数据库连接成功")
    else:
        logger.error("✗ 数据库连接失败")


def test_upload():
    """测试上传数据"""
    logger.info("=" * 60)
    logger.info("测试 2: 上传风险数据")
    logger.info("=" * 60)
    
    input_path = Path(__file__).parent / INPUT_FILE
    
    if not input_path.exists():
        logger.warning(f"测试文件不存在: {input_path}")
        return
    
    logger.info(f"输入文件: {input_path}")
    
    success = upload_risk_data_to_db(input_path)
    
    if success:
        logger.info("✓ 数据上传成功")
    else:
        logger.error("✗ 数据上传失败")


def main():
    """运行所有测试"""
    logger.info("开始运行数据库上传测试")
    logger.info("=" * 60)
    
    test_connection()
    logger.info("\n")
    
    test_upload()
    logger.info("\n")
    
    logger.info("=" * 60)
    logger.info("所有测试完成")


if __name__ == "__main__":
    main()
