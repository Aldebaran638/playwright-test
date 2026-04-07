import sys
from pathlib import Path

from loguru import logger
from playwright.sync_api import sync_playwright


# 统一把项目根目录加入导入路径，保证直接执行 task 时也能找到 workflow 包。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from workflow.modules.browser_context import (
    BrowserContextBuildError,
    build_browser_context,
    collect_browser_context_user_input,
    display_browser_context_workflow_result,
)
from workflow.modules.common.runtime_config_cli import collect_runtime_config


def main() -> None:
    # 先收集全局运行配置，再进入浏览器上下文创建流程。
    collect_runtime_config()
    user_input = collect_browser_context_user_input()

    with sync_playwright() as playwright:
        try:
            managed_context = build_browser_context(playwright, user_input)
        except BrowserContextBuildError as exc:
            display_browser_context_workflow_result(exc.workflow_result)
            raise

        try:
            display_browser_context_workflow_result(managed_context.workflow_result)
            logger.info("[task] browser context is ready and can now be reused by other modules")
        finally:
            managed_context.close()


if __name__ == "__main__":
    main()
