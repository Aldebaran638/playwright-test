from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CompetitorPatentReportConfig:
    """简介：描述竞争对手专利情报表流程所需的全部配置。
    参数：包含原始数据目录、补充数据目录、映射文件、月份和输出目录。
    返回值：无。
    逻辑：由任务文件统一构建配置对象，再交给报表模块执行。
    """

    month: str
    original_root: Path
    enriched_root: Path
    folder_mapping_file: Path
    legal_status_mapping_file: Path
    output_dir: Path
    translated_root: Path | None = None


@dataclass(slots=True)
class CompetitorPatentReportRow:
    """简介：表示一行最终要写入 Excel 的专利情报记录。
    参数：包含排序、展示和单元格合并所需的全部字段。
    返回值：无。
    逻辑：先收集和规范化，再统一排序并写入表格。
    """

    sequence: int
    competitor_name: str
    invention_title: str
    applicant_or_patentee: str
    inventors: str
    application_or_publication_number: str
    application_date: str
    publication_date: str
    authorization_date: str
    legal_status_text: str
    technical_solution: str
    source_folder_id: str
    source_page_file: str
