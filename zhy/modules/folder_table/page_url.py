from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from zhy.modules.folder_table.models import FolderTarget


def parse_folder_target(url: str) -> FolderTarget:
    # 从文件夹 URL 中解析 spaceId 和 folderId，统一为后续流程使用的数据结构。
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    space_id = (query.get("spaceId") or [""])[0].strip()
    folder_id = (query.get("folderId") or [""])[0].strip()

    if not space_id:
        raise ValueError("folder url missing query parameter: spaceId")
    if not folder_id:
        raise ValueError("folder url missing query parameter: folderId")

    return FolderTarget(
        space_id=space_id,
        folder_id=folder_id,
        base_url=url,
    )


def build_folder_page_url(base_url: str, page_number: int) -> str:
    # 直接改写 page 参数，避免依赖前端翻页按钮。
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page_number)]
    rebuilt_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=rebuilt_query))
