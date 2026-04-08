import asyncio

from loguru import logger
from playwright.async_api import BrowserContext

from zhy.modules.folder_table.models import FolderTarget
from zhy.modules.folder_table_probe.models import FolderTableProbeConfig, FolderTableProbeSummary
from zhy.modules.folder_table_probe.output import write_folder_probe_output
from zhy.modules.folder_table_probe.page_probe import probe_single_page


# 简介：根据命令行页码参数构造当前文件夹要探测的页码列表。
# 参数：
# - page_number: 单页模式下的页码。
# - start_page: 区间模式起始页。
# - end_page: 区间模式结束页。
# 返回值：
# - 需要探测的页码列表。
# 逻辑：
# - 单页模式优先走 page_number；如果给了 start/end，则生成一个连续页码范围。
def build_page_numbers(
    page_number: int,
    start_page: int | None,
    end_page: int | None,
) -> list[int]:
    if start_page is None and end_page is None:
        return [page_number]
    if start_page is None or end_page is None:
        raise ValueError("start-page and end-page must be provided together")
    if start_page <= 0 or end_page <= 0:
        raise ValueError("start-page and end-page must be positive integers")
    if end_page < start_page:
        raise ValueError("end-page must be greater than or equal to start-page")
    return list(range(start_page, end_page + 1))


# 简介：在单个文件夹内按给定并发度探测多个页码，并把结果写入同一个文件夹目录。
# 参数：
# - context: 浏览器上下文。
# - target: 当前文件夹目标。
# - config: 文件夹探测配置。
# - selectors: 表格选择器字典。
# 返回值：
# - FolderTableProbeSummary，包含输出目录、成功页、失败页和总写入行数。
# 逻辑：
# - 文件夹内部使用页级并发执行单页探测；全部页结束后统一聚合写盘。
async def probe_folder_pages(
    context: BrowserContext,
    target: FolderTarget,
    config: FolderTableProbeConfig,
    selectors: dict[str, str],
) -> FolderTableProbeSummary:
    page_semaphore = asyncio.Semaphore(max(config.page_concurrency, 1))

    async def run_page_with_limit(page_number: int):
        async with page_semaphore:
            return await probe_single_page(
                context=context,
                target=target,
                page_number=page_number,
                config=config,
                selectors=selectors,
            )

    page_tasks = [
        asyncio.create_task(run_page_with_limit(page_number))
        for page_number in config.page_numbers
    ]
    page_results = await asyncio.gather(*page_tasks)

    output_dir, appended_count, schema = write_folder_probe_output(
        output_root_dir=config.output_root_dir,
        target=target,
        page_results=page_results,
    )

    successful_pages = [result.page_number for result in page_results if result.success]
    failed_pages = [result.page_number for result in page_results if not result.success]
    logger.info(
        "[folder_table_probe] folder {} finished: success_pages={} failed_pages={} appended_rows={}",
        target.folder_id,
        successful_pages,
        failed_pages,
        appended_count,
    )
    return FolderTableProbeSummary(
        folder_id=target.folder_id,
        space_id=target.space_id,
        output_dir=output_dir,
        successful_pages=successful_pages,
        failed_pages=failed_pages,
        total_rows_written=appended_count,
        schema=schema,
    )