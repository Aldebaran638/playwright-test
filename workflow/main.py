import sys
from pathlib import Path


# 兼容直接执行 `python workflow/main.py` 时的导入路径。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from workflow.modules.browser_context_workflow import (
    BrowserContextUserInput,
    BrowserContextWorkflowResult,
    resolve_browser_context_mode,
)
from workflow.modules.browser_context_cli import (
    collect_browser_context_user_input,
    display_browser_context_workflow_result,
)
from workflow.modules.browser_context_probe import probe_browser_context_mode
from workflow.modules.runtime_config_cli import (
    collect_runtime_config,
)


def build_browser_context_workflow_result(
    user_input: BrowserContextUserInput,
    probe,
) -> BrowserContextWorkflowResult:
    # 统一从 main.py 调用浏览器环境工作流模块，方便后续继续扩展更多工作流模块。
    return resolve_browser_context_mode(user_input, probe)


def main() -> None:
    # 先收集全局运行配置，再进入浏览器环境工作流。
    collect_runtime_config()
    user_input = collect_browser_context_user_input()
    result = build_browser_context_workflow_result(
        user_input,
        probe_browser_context_mode,
    )
    display_browser_context_workflow_result(result)


if __name__ == "__main__":
    main()
