import sys
from pathlib import Path

from loguru import logger
from playwright.sync_api import sync_playwright


# 统一把项目根目录加入导入路径，保证直接执行 task 时也能找到 zhy 包。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.site_init.initialize_site import TARGET_HOME_URL, initialize_site


def main() -> None:
    # 这里直接创建一个默认浏览器上下文，用于演示和运行人工登录型网站初始化流程。
    logger.info("[site_init_task] 准备启动浏览器，并打开目标首页：{}", TARGET_HOME_URL)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()

        try:
            page = initialize_site(context)
            logger.info("[site_init_task] 网站初始化完成，当前页面地址：{}", page.url)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
