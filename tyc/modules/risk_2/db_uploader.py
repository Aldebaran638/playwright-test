import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

import pymysql
from pymysql import Connection, cursors
from loguru import logger
from dotenv import load_dotenv
import os


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


load_dotenv(PROJECT_ROOT / ".env")


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "risk_db")
DB_TABLE = os.getenv("DB_TABLE", "risk_info")
DB_TABLE_BACKUP = f"{DB_TABLE}_backup"


def upload_risk_data_to_db(input_file: str | Path) -> bool:
    input_path = Path(input_file)

    if not input_path.exists():
        logger.error(f"[db_uploader] 输入文件不存在: {input_path}")
        return False

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"[db_uploader] 成功读取输入文件: {input_path}")

        records = _extract_records_from_data(data)

        if not records:
            logger.warning("[db_uploader] 没有找到有效的风险记录")
            return False

        logger.info(f"[db_uploader] 提取到 {len(records)} 条风险记录")

        success = _upload_records_to_db(records)

        if success:
            logger.info(f"[db_uploader] 成功上传 {len(records)} 条记录到数据库")
        else:
            logger.error("[db_uploader] 上传失败")

        return success

    except Exception as e:
        logger.error(f"[db_uploader] 处理过程中发生错误: {e}")
        return False


def _extract_records_from_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    records = []

    for company_result in data.get("successful_results", []):
        company_name = company_result.get("company_name", "")

        for risk_record in company_result.get("risk_records", []):
            record = {
                "company_name": company_name,
                "risk_title": risk_record.get("title", ""),
                "risk_type": risk_record.get("risk_type", ""),
                "key_risk_info": _format_fields(risk_record.get("fields", {}))
            }
            records.append(record)

    return records


def _format_fields(fields: Dict[str, str]) -> str:
    if not fields:
        return ""

    lines = []
    for key, value in fields.items():
        lines.append(f"{key}：{value}")

    return "\n".join(lines)


def _upload_records_to_db(records: List[Dict[str, Any]]) -> bool:
    connection = None

    try:
        logger.info(f"[db_uploader] 连接数据库: {DB_HOST}:{DB_PORT}/{DB_NAME}")

        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
            cursorclass=cursors.DictCursor
        )

        logger.info("[db_uploader] 数据库连接成功")

        with connection.cursor() as cursor:

            # 1. 删除旧备份表（如果存在）
            logger.info(f"[db_uploader] 删除旧备份表: {DB_TABLE_BACKUP}")
            cursor.execute(f"DROP TABLE IF EXISTS `{DB_TABLE_BACKUP}`")

            # 2. 将当前主表备份
            logger.info(f"[db_uploader] 备份主表: {DB_TABLE} → {DB_TABLE_BACKUP}")
            cursor.execute(f"RENAME TABLE `{DB_TABLE}` TO `{DB_TABLE_BACKUP}`")

            # 3. 创建新的空主表
            logger.info(f"[db_uploader] 创建新主表: {DB_TABLE}")
            cursor.execute(f"CREATE TABLE `{DB_TABLE}` LIKE `{DB_TABLE_BACKUP}`")

            try:
                # 4. 全量插入新数据
                cursor.execute("BEGIN")
                inserted_count = 0

                for record in records:
                    sql = f"""
                        INSERT INTO `{DB_TABLE}`
                        (company_name, risk_title, risk_type, key_risk_info, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (
                        record["company_name"],
                        record["risk_title"],
                        record["risk_type"],
                        record["key_risk_info"],
                        datetime.now()
                    ))

                    inserted_count += 1

                    if inserted_count % 100 == 0:
                        logger.info(f"[db_uploader] 已处理 {inserted_count}/{len(records)} 条记录")

                connection.commit()
                logger.info(f"[db_uploader] 事务提交成功，共插入 {inserted_count} 条记录")
                return True

            except Exception as e:
                logger.error(f"[db_uploader] 插入数据时发生错误: {e}，开始还原")
                connection.rollback()

                # 5. 还原：删除新建的空表，把备份表 rename 回来
                cursor.execute(f"DROP TABLE IF EXISTS `{DB_TABLE}`")
                cursor.execute(f"RENAME TABLE `{DB_TABLE_BACKUP}` TO `{DB_TABLE}`")
                logger.info("[db_uploader] 已还原主表")
                return False

    except Exception as e:
        logger.error(f"[db_uploader] 数据库连接失败: {e}")
        return False

    finally:
        if connection:
            connection.close()
            logger.info("[db_uploader] 数据库连接已关闭")


def test_db_connection() -> bool:
    try:
        logger.info(f"[db_uploader] 测试数据库连接: {DB_HOST}:{DB_PORT}/{DB_NAME}")

        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
            cursorclass=cursors.DictCursor
        )

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

        connection.close()

        if result:
            logger.info("[db_uploader] 数据库连接测试成功")
            return True
        else:
            logger.error("[db_uploader] 数据库连接测试失败")
            return False

    except Exception as e:
        logger.error(f"[db_uploader] 数据库连接测试失败: {e}")
        return False


def get_db_config() -> Dict[str, Any]:
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": "******",
        "database": DB_NAME,
        "table": DB_TABLE,
        "backup_table": DB_TABLE_BACKUP
    }