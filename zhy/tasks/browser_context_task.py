import sys
from pathlib import Path


# 统一把项目根目录加入导入路径，保证直接执行 task 时也能找到 zhy 包。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from zhy.modules.browser_context.browser_context_cli import (
    collect_browser_context_user_input,
    display_browser_context_workflow_result,
)
from zhy.modules.browser_context.browser_context_probe import probe_browser_context_mode
from zhy.modules.browser_context.browser_context_workflow import (
    BrowserContextUserInput,
    BrowserContextWorkflowResult,
    resolve_browser_context_mode,
)


# 统一从 task 层进入浏览器上下文工作流。
#
# 参数：
# - user_input: 用户提供的浏览器上下文输入。
# - probe: 浏览器模式探测函数。
# 返回：
# - 浏览器上下文工作流结果。
# 逻辑：
# - 只负责串联工作流模块，便于后续扩展更多初始化流程。
def build_browser_context_workflow_result(
    user_input: BrowserContextUserInput,
    probe,
) -> BrowserContextWorkflowResult:
    return resolve_browser_context_mode(user_input, probe)


def main() -> None:
    # 先收集用户输入的浏览器路径信息。
    user_input = collect_browser_context_user_input()

    # 根据输入和探测结果，计算最终应采用的浏览器上下文模式。
    result = build_browser_context_workflow_result(
        user_input,
        probe_browser_context_mode,
    )

    # 把结构化结果输出成终端摘要。
    display_browser_context_workflow_result(result)


if __name__ == "__main__":
    main()
