from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pymysql
from dotenv import load_dotenv
from loguru import logger
from pymysql import Connection, cursors


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


load_dotenv(PROJECT_ROOT / ".env")


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "risk_db")
DB_TABLE = os.getenv("DB_DAILY_SUMMARY_TABLE", "risk_daily_summary")
DB_TABLE_BACKUP = f"{DB_TABLE}_backup"


def upload_risk_daily_summary_to_db(input_file: str | Path) -> bool:
    input_path = Path(input_file)

    if not input_path.exists():
        logger.error(f"[risk_daily_db_uploader] 输入文件不存在: {input_path}")
        return False

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"[risk_daily_db_uploader] 成功读取输入文件: {input_path}")

        records = extract_summary_records_from_data(data)
        if not records:
            logger.warning("[risk_daily_db_uploader] 没有找到有效的按日聚合记录")
            return False

        logger.info(f"[risk_daily_db_uploader] 提取到 {len(records)} 条按日聚合记录")
        success = _upload_records_to_db(records)

        if success:
            logger.info(f"[risk_daily_db_uploader] 成功上传 {len(records)} 条记录到数据库")
        else:
            logger.error("[risk_daily_db_uploader] 上传失败")

        return success

    except Exception as e:
        logger.error(f"[risk_daily_db_uploader] 处理过程中发生错误: {e}")
        return False


def extract_summary_records_from_data(data: Any) -> list[dict[str, str]]:
    if not isinstance(data, list):
        logger.error("[risk_daily_db_uploader] 输入数据不是按日聚合数组")
        return []

    records: list[dict[str, str]] = []
    invalid_rows = 0

    for row in data:
        if not isinstance(row, dict):
            invalid_rows += 1
            continue

        company_name = str(row.get("公司名称", "")).strip()
        risk_date = str(row.get("时间", "")).strip()
        if not company_name or not _is_valid_date(risk_date):
            invalid_rows += 1
            logger.warning(
                f"[risk_daily_db_uploader] 跳过非法记录: company={company_name or '-'}, risk_date={risk_date or '-'}"
            )
            continue

        records.append(
            {
                "company_name": company_name,
                "risk_date": risk_date,
                "legal_litigation_types": _normalize_db_text(row.get("法律诉讼类型", "")),
                "legal_litigation_names": _normalize_db_text(row.get("法律诉讼名称", "")),
                "business_risk_types": _normalize_db_text(row.get("经营风险类型", "")),
                "business_risk_names": _normalize_db_text(row.get("经营风险名称", "")),
            }
        )

    if invalid_rows:
        logger.warning(f"[risk_daily_db_uploader] 跳过 {invalid_rows} 条非法记录")

    return records


def _normalize_db_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_valid_date(value: str) -> bool:
    return bool(value) and len(value) == 10 and value[4] == "-" and value[7] == "-"


def _upload_records_to_db(records: list[dict[str, str]]) -> bool:
    connection: Connection | None = None
    had_existing_table = False

    try:
        logger.info(f"[risk_daily_db_uploader] 连接数据库: {DB_HOST}:{DB_PORT}/{DB_NAME}")

        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
            cursorclass=cursors.DictCursor,
            autocommit=False,
        )

        logger.info("[risk_daily_db_uploader] 数据库连接成功")

        with connection.cursor() as cursor:
            logger.info(f"[risk_daily_db_uploader] 删除旧备份表: {DB_TABLE_BACKUP}")
            cursor.execute(f"DROP TABLE IF EXISTS `{DB_TABLE_BACKUP}`")

            had_existing_table = _table_exists(cursor, DB_TABLE)
            if had_existing_table:
                logger.info(f"[risk_daily_db_uploader] 备份主表: {DB_TABLE} → {DB_TABLE_BACKUP}")
                cursor.execute(f"RENAME TABLE `{DB_TABLE}` TO `{DB_TABLE_BACKUP}`")
                logger.info(f"[risk_daily_db_uploader] 创建新主表: {DB_TABLE}")
                cursor.execute(f"CREATE TABLE `{DB_TABLE}` LIKE `{DB_TABLE_BACKUP}`")
            else:
                logger.info(f"[risk_daily_db_uploader] 主表不存在，创建新表: {DB_TABLE}")
                cursor.execute(build_create_table_sql(DB_TABLE))

            insert_sql = f"""
                INSERT INTO `{DB_TABLE}`
                (
                    company_name,
                    risk_date,
                    legal_litigation_types,
                    legal_litigation_names,
                    business_risk_types,
                    business_risk_names
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            inserted_count = 0
            for record in records:
                cursor.execute(
                    insert_sql,
                    (
                        record["company_name"],
                        record["risk_date"],
                        record["legal_litigation_types"],
                        record["legal_litigation_names"],
                        record["business_risk_types"],
                        record["business_risk_names"],
                    ),
                )
                inserted_count += 1

                if inserted_count % 100 == 0:
                    logger.info(
                        f"[risk_daily_db_uploader] 已处理 {inserted_count}/{len(records)} 条记录"
                    )

            connection.commit()
            logger.info(
                f"[risk_daily_db_uploader] 事务提交成功，共插入 {inserted_count} 条记录"
            )
            return True

    except Exception as e:
        logger.error(f"[risk_daily_db_uploader] 插入数据时发生错误: {e}")

        if connection:
            connection.rollback()

            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"DROP TABLE IF EXISTS `{DB_TABLE}`")
                    if had_existing_table and _table_exists(cursor, DB_TABLE_BACKUP):
                        cursor.execute(f"RENAME TABLE `{DB_TABLE_BACKUP}` TO `{DB_TABLE}`")
                        logger.info("[risk_daily_db_uploader] 已还原主表")
            except Exception as restore_error:
                logger.error(f"[risk_daily_db_uploader] 表还原失败: {restore_error}")

        return False

    finally:
        if connection:
            connection.close()
            logger.info("[risk_daily_db_uploader] 数据库连接已关闭")


def _table_exists(cursor: cursors.Cursor, table_name: str) -> bool:
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None


def build_create_table_sql(table_name: str) -> str:
    return f"""
        CREATE TABLE `{table_name}` (
            `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
            `company_name` VARCHAR(255) NOT NULL COMMENT '公司名称',
            `risk_date` DATE NOT NULL COMMENT '时间',
            `legal_litigation_types` TEXT NOT NULL COMMENT '法律诉讼类型，使用换行符拼接',
            `legal_litigation_names` TEXT NOT NULL COMMENT '法律诉讼名称，使用换行符拼接',
            `business_risk_types` TEXT NOT NULL COMMENT '经营风险类型，使用换行符拼接',
            `business_risk_names` TEXT NOT NULL COMMENT '经营风险名称，使用换行符拼接',
            `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_company_date` (`company_name`, `risk_date`),
            KEY `idx_company_name` (`company_name`),
            KEY `idx_risk_date` (`risk_date`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='企业风险按公司按日聚合结果表'
    """


def test_db_connection() -> bool:
    try:
        logger.info(f"[risk_daily_db_uploader] 测试数据库连接: {DB_HOST}:{DB_PORT}/{DB_NAME}")

        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
            cursorclass=cursors.DictCursor,
        )

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

        connection.close()

        if result:
            logger.info("[risk_daily_db_uploader] 数据库连接测试成功")
            return True

        logger.error("[risk_daily_db_uploader] 数据库连接测试失败")
        return False

    except Exception as e:
        logger.error(f"[risk_daily_db_uploader] 数据库连接测试失败: {e}")
        return False


def get_db_config() -> dict[str, Any]:
    return {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": "******",
        "database": DB_NAME,
        "table": DB_TABLE,
        "backup_table": DB_TABLE_BACKUP,
    }


__all__ = [
    "build_create_table_sql",
    "extract_summary_records_from_data",
    "get_db_config",
    "test_db_connection",
    "upload_risk_daily_summary_to_db",
]