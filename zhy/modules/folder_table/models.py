from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from typing import Literal


PageCollectStatus = Literal["success", "empty", "error"]


@dataclass(frozen=True)
class FolderTarget:
    # 标识一个待抓取文件夹的稳定目标信息。
    space_id: str
    folder_id: str
    base_url: str


@dataclass(frozen=True)
class TableSchema:
    # 保存当前文件夹表格解析出的列结构。
    columns: list[str]
    column_count: int


@dataclass(frozen=True)
class TableRowRecord:
    # 表示单条表格记录，data 保留当前文件夹自己的字段结构。
    folder_id: str
    page_number: int
    row_key: str
    data: dict[str, str]


@dataclass(frozen=True)
class PageCollectResult:
    # 汇总单页抓取结果，显式区分成功、空页和异常。
    folder_id: str
    page_number: int
    status: PageCollectStatus
    schema: TableSchema | None
    rows: list[TableRowRecord]
    is_empty: bool
    error_message: str | None = None
    debug_payload: dict[str, Any] | None = None


@dataclass
class FolderCollectResult:
    # 汇总整个文件夹的抓取结果和最终输出位置。
    folder_id: str
    space_id: str
    schema: TableSchema | None
    output_dir: Path
    total_pages_collected: int
    total_rows_collected: int
    empty_page_number: int | None = None
    collected_page_numbers: list[int] = field(default_factory=list)


@dataclass(frozen=True)
class FolderTableConfig:
    # 抓取阶段的所有业务参数都要求由 task 显式传入，模块层不保留默认值。
    output_root_dir: Path
    concurrency: int
    start_page: int
    expected_page_size: int
    zoom_ratio: float
    page_timeout_ms: int
    table_ready_timeout_ms: int
    scroll_step_pixels: int
    scroll_pause_seconds: float
    max_stable_scroll_rounds: int
    empty_page_wait_seconds: float
    retry_count: int
    retry_wait_seconds: float
