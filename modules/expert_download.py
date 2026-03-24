import random
import time
from pathlib import Path

from playwright.sync_api import Page


def human_wait(min_sec=3, max_sec=6):
    # 随机等待，避免操作过于机械
    t = random.uniform(min_sec, max_sec)
    print(f"wait {t:.2f}s")
    time.sleep(t)


def download_pdf_from_detail_page(detail_page: Page):
    human_wait()
    # 在详情页点击“下载”按钮
    detail_page.get_by_role("button", name="下载").click()
    human_wait()

    # 点击“下载PDF文件”，并等待下载开始
    with detail_page.expect_download() as download_info:
        detail_page.get_by_role("button", name="下载PDF文件").click()

    # 获取下载对象，并保存到项目根目录
    download = download_info.value
    save_path = Path(download.suggested_filename)
    download.save_as(str(save_path))
    print(f"download saved to: {save_path.resolve()}")
    human_wait()
