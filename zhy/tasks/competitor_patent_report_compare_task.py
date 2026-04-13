import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.common.run_step import run_step_async
from zhy.modules.competitor_patent_report_compare import (
    CompetitorPatentReportCompareConfig,
    run_competitor_patent_report_compare,
)


# 默认人工表路径，等用户自行填写。
DEFAULT_MANUAL_REPORT_PATH = PROJECT_ROOT / "zhy" / "data" / "input" / "附表 主要竞争对手专利情报（2026年2月）.xlsx"
# 默认程序表路径，等用户自行填写。
DEFAULT_GENERATED_REPORT_PATH = PROJECT_ROOT / "zhy" / "data" / "input" / "竞争对手专利情报_2026-02.xlsx"
# 默认差异报告输出目录。
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "zhy" / "data" / "output" / "competitor_patent_report_compare"
# 默认差异报告基础文件名。
DEFAULT_REPORT_BASENAME = "competitor_patent_report_compare"

# 是否强制使用流程文件内默认参数，1 表示强制默认，0 表示按命令行。
DEFAULT_USE_DEFAULTS = 1

# 模块级步骤重试配置。
DEFAULT_MODULE_STEP_RETRIES = 1
DEFAULT_STEP_RETRY_DELAY_SECONDS = 1.0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare manual and generated competitor patent Excel reports.")
    parser.add_argument("--use-defaults", type=int, choices=[0, 1], default=DEFAULT_USE_DEFAULTS)
    parser.add_argument("--manual-report-path", type=Path, default=DEFAULT_MANUAL_REPORT_PATH)
    parser.add_argument("--generated-report-path", type=Path, default=DEFAULT_GENERATED_REPORT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-basename", default=DEFAULT_REPORT_BASENAME)
    return parser


def apply_default_mode(args: argparse.Namespace) -> argparse.Namespace:
    """简介：按 use-defaults 开关决定是否强制回落到流程文件默认参数。
    参数：args 为命令行参数对象。
    返回值：处理后的参数对象。
    逻辑：当 use-defaults=1 时，统一覆盖为流程文件硬编码默认值，方便后续直接替换路径联调。
    """

    # 显式关闭默认模式时，保留外部传入的命令行参数。
    if args.use_defaults == 0:
        return args

    # 打开默认模式时，统一回落到流程文件里硬编码的参数。
    args.manual_report_path = DEFAULT_MANUAL_REPORT_PATH
    args.generated_report_path = DEFAULT_GENERATED_REPORT_PATH
    args.output_dir = DEFAULT_OUTPUT_DIR
    args.report_basename = DEFAULT_REPORT_BASENAME
    return args


def build_config(args: argparse.Namespace) -> CompetitorPatentReportCompareConfig:
    """简介：把命令行参数转换为报表对比模块配置对象。
    参数：args 为命令行参数对象。
    返回值：CompetitorPatentReportCompareConfig。
    逻辑：流程文件统一管理两份表格路径与输出参数，模块内部仅负责解析和对比。
    """

    return CompetitorPatentReportCompareConfig(
        manual_report_path=args.manual_report_path,
        generated_report_path=args.generated_report_path,
        output_dir=args.output_dir,
        report_basename=args.report_basename,
    )


async def run_competitor_patent_report_compare_async(config: CompetitorPatentReportCompareConfig) -> Path:
    """简介：把同步报表对比模块包装成异步步骤函数。
    参数：config 为对比配置对象。
    返回值：Markdown 报告路径。
    逻辑：当前 run_step_async 只能 await 异步函数，这里用 asyncio.to_thread 托管同步对比逻辑。
    """

    return await asyncio.to_thread(run_competitor_patent_report_compare, config)


async def run_task(args: argparse.Namespace) -> Path:
    """简介：执行竞争对手专利报表差异对比流程。
    参数：args 为已解析的流程参数。
    返回值：生成的 Markdown 报告路径。
    逻辑：调用报表对比模块主函数，并通过 run_step_async 统一处理日志、重试和异常。
    """

    workflow_step = await run_step_async(
        run_competitor_patent_report_compare_async,
        build_config(args),
        step_name="生成竞争对手专利报表差异报告",
        critical=True,
        retries=DEFAULT_MODULE_STEP_RETRIES,
        retry_delay_seconds=DEFAULT_STEP_RETRY_DELAY_SECONDS,
    )
    output_path = workflow_step.value
    if output_path is None:
        raise RuntimeError("competitor patent report compare task did not return output path")
    return output_path


def main() -> None:
    parser = build_argument_parser()
    args = apply_default_mode(parser.parse_args())
    output_path = asyncio.run(run_task(args))
    logger.info("[competitor_patent_report_compare_task] done: output={}", output_path)


if __name__ == "__main__":
    # 直接执行任务文件时，从这里进入整条流程。
    main()
