import random
import re
import time
from pathlib import Path

from playwright.sync_api import Page

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_RETRY_TIMES = 3


def human_wait(min_sec=3, max_sec=6):
    # 随机等待，避免操作过于机械
    t = random.uniform(min_sec, max_sec)
    print(f"wait {t:.2f}s")
    time.sleep(t)


def observe_detail_page(min_sec=6, max_sec=12):
    # 打开详情页后停留一段时间，模拟用户阅读页面
    wait_seconds = random.uniform(min_sec, max_sec)
    print(f"observe detail page for {wait_seconds:.2f}s")
    time.sleep(wait_seconds)


def scroll_detail_page_by_random_percent(detail_page: Page, min_percent=0.15, max_percent=0.55):
    # 随机向下滚动详情页总可滚动距离的一部分
    page_metrics = detail_page.evaluate(
        """
        () => {
            const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
            const pageHeight = Math.max(
                document.body.scrollHeight,
                document.documentElement.scrollHeight
            );
            return {
                viewportHeight,
                pageHeight,
                maxScrollable: Math.max(pageHeight - viewportHeight, 0),
            };
        }
        """
    )

    max_scrollable = int(page_metrics.get("maxScrollable", 0))
    if max_scrollable <= 0:
        print("detail page has no extra scrollable distance")
        return

    scroll_percent = random.uniform(min_percent, max_percent)
    scroll_distance = max(200, int(max_scrollable * scroll_percent))
    print(
        f"scroll detail page by {scroll_percent:.2%}, distance: {scroll_distance}px"
    )
    detail_page.mouse.wheel(0, scroll_distance)
    time.sleep(random.uniform(1.5, 3.5))


def build_download_path(article_title: str, suggested_filename: str) -> Path:
    # 取下载对象原始扩展名，默认按 pdf 保存
    suffix = Path(suggested_filename).suffix or ".pdf"

    # 清理 Windows 文件名非法字符，避免保存失败
    safe_title = re.sub(r'[<>:"/\\|?*]', "_", article_title).strip().rstrip(".")
    if not safe_title:
        safe_title = Path(suggested_filename).stem or "download"

    save_path = DOWNLOAD_DIR / f"{safe_title}{suffix}"
    duplicate_index = 1
    while save_path.exists():
        save_path = DOWNLOAD_DIR / f"{safe_title}_{duplicate_index}{suffix}"
        duplicate_index += 1

    return save_path


def download_pdf_from_detail_page(
    detail_page: Page,
    article_title: str,
    should_download: bool = True,
    allow_detail_scroll: bool = False,
) -> bool:
    # 打开详情页后，按参数决定是否滚动详情页以及是否执行下载
    if allow_detail_scroll:
        scroll_detail_page_by_random_percent(detail_page)

    # 伪装浏览文章时，只停留不下载
    if not should_download:
        print(f"browse only, skip download: {article_title}")
        observe_detail_page()
        return True

    # 对下载流程进行最多三次重试，避免单次点击失败就中断整个任务
    for attempt in range(1, DOWNLOAD_RETRY_TIMES + 1):
        try:
            human_wait()
            # 在详情页点击“下载”按钮
            detail_page.get_by_role("button", name="下载").click()
            human_wait()

            # 点击“下载PDF文件”，并等待下载开始
            with detail_page.expect_download() as download_info:
                detail_page.get_by_role("button", name="下载PDF文件").click()

            # 创建项目根目录下的 downloads 文件夹
            DOWNLOAD_DIR.mkdir(exist_ok=True)

            # 获取下载对象，并按文章标题保存到 downloads 文件夹
            download = download_info.value
            save_path = build_download_path(article_title, download.suggested_filename)
            download.save_as(str(save_path))
            print(f"download saved to: {save_path.resolve()}")
            human_wait()
            return True
        except Exception as exc:
            print(f"download attempt {attempt} failed: {exc}")
            if attempt == DOWNLOAD_RETRY_TIMES:
                print("download failed after retries, skipping current article")
                return False

            # 在下一次重试前稍作等待，给页面一点恢复时间
            time.sleep(2)

    return False
