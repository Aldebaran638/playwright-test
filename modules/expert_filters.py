import random
import time

from playwright.sync_api import Page


def human_wait(min_sec=1, max_sec=2):
    # 随机等待，避免操作过于机械
    t = random.uniform(min_sec, max_sec)
    print(f"wait {t:.2f}s")
    time.sleep(t)


def apply_expert_analysis_filters(page: Page):
    # 切换到“产品特征”筛选标签
    page.get_by_role("tab", name="产品特征").click()
    human_wait()

    # 勾选“专利”筛选条件
    page.get_by_role("checkbox", name="专利").click()
    human_wait()

    # 勾选“成分”筛选条件
    page.get_by_role("checkbox", name="成分").click()
    human_wait()

    # 勾选“产品概念”筛选条件
    page.get_by_role("checkbox", name="产品概念").click()
    human_wait()

    # 点击目标分析条目，并等待新弹窗打开
    with page.expect_popup() as page1_info:
        page.get_by_text("美容产品创新亮点，2026年3月Regional2026年").click()

    # 获取新打开的详情页
    detail_page = page1_info.value
    human_wait()

    # 在详情页点击“下载”按钮
    detail_page.get_by_role("button", name="下载").click()
    human_wait()

    # 点击“下载PDF文件”，并等待下载开始
    with detail_page.expect_download() as download_info:
        detail_page.get_by_role("button", name="下载PDF文件").click()

    # 获取下载对象，确保下载流程已触发
    download = download_info.value
    print(f"download started: {download.suggested_filename}")
    human_wait()
