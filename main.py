import time
from pathlib import Path

from playwright.sync_api import Playwright, TimeoutError, sync_playwright

# 导入：从主页进入“专家分析”页面的模块
from modules.expert_analysis import open_expert_analysis_from_home
# 导入：在“专家分析”页面选择标签的模块
from modules.expert_tags import apply_expert_analysis_tag_filters
# 导入：在结果列表中寻找目标卡片并进入详情页的模块
from modules.expert_load_more import open_target_card_when_ready
# 导入：进入详情页后执行下载的模块
from modules.expert_download import download_pdf_from_detail_page
# 导入：登录模块中的账号、密码、登录判断和登录动作
from modules.login import PASSWORD, USERNAME, do_login, is_logged_in

# 本地登录态文件，用于复用已登录会话
STORAGE_STATE = "auth.json"
# 要寻找的目标卡片标题
TARGET_CARD_TITLE = "The Week in Trends – Feelings First, Products Second"


def run(playwright: Playwright) -> None:
    # 启动可见浏览器，并设置慢动作方便观察
    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=100,
    )

    # 获取登录态文件路径
    state_file = Path(STORAGE_STATE)

    # 如果本地已有登录态文件，则直接复用
    if state_file.exists():
        print(f"found existing state file: {STORAGE_STATE}")
        context = browser.new_context(storage_state=STORAGE_STATE)
    else:
        # 没有登录态文件时，创建新的浏览器上下文
        print("no state file found, creating new session")
        context = browser.new_context()

    # 在当前上下文中打开新页面
    page = context.new_page()

    try:
        # 检查当前会话是否仍然处于登录状态
        if not is_logged_in(page):
            print("login state is missing or expired, logging in again...")
            # 登录态失效时，重新执行登录流程
            do_login(page)
            # 将新的登录态保存到本地文件
            context.storage_state(path=STORAGE_STATE)
            print(f"saved state file: {STORAGE_STATE}")
        else:
            print("already logged in, reusing session state")

        # 从主页进入“专家分析”页面
        open_expert_analysis_from_home(page)
        # 在“专家分析”页面选择筛选标签
        apply_expert_analysis_tag_filters(page)
        # 在结果列表中寻找目标卡片，并进入详情页
        detail_page = open_target_card_when_ready(page, TARGET_CARD_TITLE)
        # 进入详情页后执行下载流程
        download_pdf_from_detail_page(detail_page)
        # 获取当前页面的 HTML 内容
        html = page.content()

        # 将页面 HTML 保存到本地文件
        with open("test.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("saved as test.html")
        # 保留浏览器 10 秒，方便人工确认结果
        print("flow complete, keeping browser open for 10 seconds...")
        time.sleep(60)

    # 单独处理 Playwright 超时异常
    except TimeoutError as e:
        print(f"page timeout: {e}")
    # 兜底处理其他异常
    except Exception as e:
        print(f"execution failed: {e}")
    finally:
        # 无论成功还是失败，都释放浏览器资源
        context.close()
        browser.close()


if __name__ == "__main__":
    # 启动前先确认 keyring 中已经保存账号密码
    if not USERNAME or not PASSWORD:
        raise ValueError("please save mintel username/password in keyring first")

    # 进入 Playwright 同步运行入口
    with sync_playwright() as playwright:
        run(playwright)
