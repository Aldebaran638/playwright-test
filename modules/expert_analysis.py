import random
import re
import time

from playwright.sync_api import Page

# 门户主页地址和 clients 首页地址
PORTAL_HOME = "https://portal.mintel.com/"
CLIENTS_HOME = "https://clients.mintel.com/home"


def human_wait(min_sec=5, max_sec=9):
    # 随机等待，避免操作过于机械
    t = random.uniform(min_sec, max_sec)
    print(f"wait {t:.2f}s")
    time.sleep(t)


def open_expert_analysis_from_home(page: Page):
    # 先进入门户主页
    print("open target page...")
    page.goto(PORTAL_HOME, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    human_wait()

    try:
        # 优先使用包含 Mintel 的按钮进行定位，减少语言差异影响
        explore_btn = page.get_by_role("button", name=re.compile("Mintel", re.I)).first
        # 只有按钮可见时才点击
        if explore_btn.is_visible(timeout=5000):
            explore_btn.click()
            human_wait()
    except Exception:
        # 这个步骤找不到也不中断流程
        pass

    # 进入 clients 首页，准备查找“专家分析”入口
    page.goto(CLIENTS_HOME, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    human_wait()

    try:
        # 第一种方式：通过 href 关键词定位目标链接
        expert_link = page.locator("a[href*='expert'][href*='analysis']").first
        if expert_link.is_visible(timeout=5000):
            expert_link.click()
            human_wait()
            # 点击成功后直接结束函数
            return
    except Exception:
        # href 定位失败时，回退到文本匹配方案
        pass

    try:
        # 第二种方式：通过可见文本匹配“专家分析”链接
        page.get_by_role(
            "link",
            name=re.compile(r"专家分析|expert\s*analysis", re.I),
        ).first.click(timeout=10000)
        human_wait()
    except Exception:
        # 两种方式都失败时，仅记录日志并继续
        print("did not click expert analysis, but already entered clients home.")
