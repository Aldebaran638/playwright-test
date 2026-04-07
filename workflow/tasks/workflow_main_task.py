import sys
from pathlib import Path


# 统一把项目根目录加入导入路径，保证直接执行 task 时也能找到 workflow 包。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from workflow.modules.browser_context.browser_context_cli import (
    collect_browser_context_user_input,
    display_browser_context_workflow_result,
)
from workflow.modules.browser_context.browser_context_probe import probe_browser_context_mode
from workflow.modules.browser_context.browser_context_workflow import (
    BrowserContextUserInput,
    BrowserContextWorkflowResult,
    resolve_browser_context_mode,
)
from workflow.modules.common.runtime_config_cli import collect_runtime_config


def build_browser_context_workflow_result(
    user_input: BrowserContextUserInput,
    probe,
) -> BrowserContextWorkflowResult:
    # 统一从 task 层进入浏览器上下文工作流，方便后续继续扩展更多初始化流程。
    return resolve_browser_context_mode(user_input, probe)


def main() -> None:
    # 先收集全局运行配置，再进入浏览器上下文探测流程。
    collect_runtime_config()

    # 收集用户提供的浏览器路径和用户数据目录。
    user_input = collect_browser_context_user_input()

    # 根据输入和探测器结果，计算最终应采用的浏览器上下文模式。
    result = build_browser_context_workflow_result(
        user_input,
        probe_browser_context_mode,
    )

    # 把结构化结果输出成终端可读摘要。
    display_browser_context_workflow_result(result)


if __name__ == "__main__":
    main()
