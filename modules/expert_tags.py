import random
import time

from playwright.sync_api import Page


def human_wait(min_sec=3, max_sec=6):
    # 随机等待，避免操作过于机械
    t = random.uniform(min_sec, max_sec)
    print(f"wait {t:.2f}s")
    time.sleep(t)


def apply_expert_analysis_tag_filters(page: Page):
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

    # 切回“结果”视图，查看筛选后的卡片列表
    page.get_by_text("结果").click()
    human_wait()
