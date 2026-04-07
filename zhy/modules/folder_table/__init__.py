from zhy.modules.folder_table.models import (
    FolderCollectResult,
    FolderTableConfig,
    FolderTarget,
    PageCollectResult,
    TableRowRecord,
    TableSchema,
)
from zhy.modules.folder_table.folder_table_workflow import collect_folder_table, collect_single_page
from zhy.modules.folder_table.page_url import build_folder_page_url, parse_folder_target

__all__ = [
    "FolderCollectResult",
    "FolderTableConfig",
    "FolderTarget",
    "PageCollectResult",
    "TableRowRecord",
    "TableSchema",
    "build_folder_page_url",
    "collect_folder_table",
    "collect_single_page",
    "parse_folder_target",
]
