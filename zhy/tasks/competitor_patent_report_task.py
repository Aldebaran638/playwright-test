import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.competitor_patent_report import CompetitorPatentReportConfig, run_competitor_patent_report
from zhy.modules.common.run_step import run_step_async


# 默认月份，按公开/公告日期 PBD 的 YYYY-MM 过滤。
DEFAULT_MONTH = "2016-11"
DEFAULT_OUTPUT_DATE_LAYER = DEFAULT_MONTH
# 默认原始数据目录。
DEFAULT_ORIGINAL_ROOT = PROJECT_ROOT / "zhy" / "data" / "output" / DEFAULT_OUTPUT_DATE_LAYER / "folder_patents_hybrid"
# 默认补充信息目录。
DEFAULT_ENRICHED_ROOT = PROJECT_ROOT / "zhy" / "data" / "output" / DEFAULT_OUTPUT_DATE_LAYER / "folder_patents_hybrid_enriched"
# 默认 folder_id 到主要竞争对手名称映射文件。
DEFAULT_FOLDER_MAPPING_FILE = PROJECT_ROOT / "zhy" / "data" / "tmp" / "mid3.json"
# 默认法律状态映射文件。
DEFAULT_LEGAL_STATUS_MAPPING_FILE = PROJECT_ROOT / "zhy" / "data" / "tmp" / "mid1.json"
# 默认 Excel 输出目录。
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / DEFAULT_OUTPUT_DATE_LAYER / "excel_reports"

# 是否强制使用流程文件内默认参数，1 表示强制默认，0 表示按命令行。
DEFAULT_USE_DEFAULTS = 1

# 模块级步骤重试配置。
DEFAULT_MODULE_STEP_RETRIES = 1
DEFAULT_STEP_RETRY_DELAY_SECONDS = 1.0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate competitor patent intelligence Excel report for a given month.")
    parser.add_argument("--use-defaults", type=int, choices=[0, 1], default=DEFAULT_USE_DEFAULTS)
    parser.add_argument("--month", default=DEFAULT_MONTH, help="Month in YYYY-MM format, filtered by PBD.")
    parser.add_argument("--original-root", type=Path, default=DEFAULT_ORIGINAL_ROOT)
    parser.add_argument("--enriched-root", type=Path, default=DEFAULT_ENRICHED_ROOT)
    parser.add_argument("--folder-mapping-file", type=Path, default=DEFAULT_FOLDER_MAPPING_FILE)
    parser.add_argument("--legal-status-mapping-file", type=Path, default=DEFAULT_LEGAL_STATUS_MAPPING_FILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def apply_default_mode(args: argparse.Namespace) -> argparse.Namespace:
    """简介：按 use-defaults 开关决定是否强制回落到流程文件默认参数。
    参数：args 为命令行参数对象。
    返回值：处理后的参数对象。
    逻辑：当 use-defaults=1 时，统一覆盖为流程文件硬编码默认值，方便直接运行。
    """

    # 显式关闭默认模式时，保留外部传入的命令行参数。
    if args.use_defaults == 0:
        return args

    # 打开默认模式时，统一回落到流程文件里硬编码的参数。
    args.month = DEFAULT_MONTH
    args.original_root = DEFAULT_ORIGINAL_ROOT
    args.enriched_root = DEFAULT_ENRICHED_ROOT
    args.folder_mapping_file = DEFAULT_FOLDER_MAPPING_FILE
    args.legal_status_mapping_file = DEFAULT_LEGAL_STATUS_MAPPING_FILE
    args.output_dir = DEFAULT_OUTPUT_DIR
    return args


def build_config(args: argparse.Namespace) -> CompetitorPatentReportConfig:
    """简介：把命令行参数转换为模块配置对象。
    参数：args 为命令行参数对象。
    返回值：CompetitorPatentReportConfig。
    逻辑：流程文件负责注入所有模块参数，模块内部不再硬编码业务值。
    """

    return CompetitorPatentReportConfig(
        month=args.month,
        original_root=args.original_root,
        enriched_root=args.enriched_root,
        folder_mapping_file=args.folder_mapping_file,
        legal_status_mapping_file=args.legal_status_mapping_file,
        output_dir=args.output_dir,
    )


async def run_competitor_patent_report_async(config: CompetitorPatentReportConfig) -> Path:
    """简介：把同步报表模块包装成异步步骤函数。
    参数：config 为报表配置对象。
    返回值：生成的 Excel 文件路径。
    逻辑：当前 run_step_async 只能 await 异步函数，这里用 asyncio.to_thread 托管同步报表生成。
    """

    return await asyncio.to_thread(run_competitor_patent_report, config)


async def run_task(args: argparse.Namespace) -> Path:
    """简介：执行竞争对手专利情报 Excel 生成流程。
    参数：args 为已解析的流程参数。
    返回值：生成的 Excel 文件路径。
    逻辑：调用报表模块主函数，并通过 run_step_async 统一处理日志、重试和异常。
    """

    workflow_step = await run_step_async(
        run_competitor_patent_report_async,
        build_config(args),
        step_name="生成竞争对手专利情报Excel",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )
    output_path = workflow_step.value
    if output_path is None:
        raise RuntimeError("competitor patent report task did not return output path")
    return output_path


def main() -> None:
    parser = build_argument_parser()
    args = apply_default_mode(parser.parse_args())
    output_path = asyncio.run(run_task(args))
    logger.info("[competitor_patent_report_task] done: output={}", output_path)


if __name__ == "__main__":
    # 直接执行任务文件时，从这里进入整条流程。
    main()
