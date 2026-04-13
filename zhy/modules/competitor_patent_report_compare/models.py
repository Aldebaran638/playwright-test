from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CompetitorPatentReportCompareConfig:
    """简介：描述两份竞争对手专利报表对比流程所需的全部配置。
    参数：包含人工表、程序表和报告输出目录等路径参数。
    返回值：无。
    逻辑：所有业务参数由 task 注入，模块内部不硬编码具体文件路径。
    """

    manual_report_path: Path
    generated_report_path: Path
    output_dir: Path
    report_basename: str


@dataclass(slots=True)
class ComparedPatentRecord:
    """简介：描述一条专利在单份报表中的标准化记录。
    参数：key 为对比主键；fields 为各业务字段；source_row_number 为原 Excel 行号。
    返回值：无。
    逻辑：统一把 Excel 行转换成结构化对象，便于后续按主键对比字段差异。
    """

    key: str
    fields: dict[str, str]
    source_row_number: int
