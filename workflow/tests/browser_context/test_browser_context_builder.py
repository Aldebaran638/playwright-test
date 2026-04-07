import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflow.modules.browser_context.browser_context_builder import build_browser_context
from workflow.modules.browser_context.browser_context_workflow import BrowserContextProbeResult, BrowserContextUserInput


class FakeContext:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self) -> None:
        self.closed = False
        self.created_context = FakeContext()

    def new_context(self) -> FakeContext:
        return self.created_context

    def close(self) -> None:
        self.closed = True


class FakeChromium:
    def __init__(self) -> None:
        self.last_launch_kwargs = None
        self.last_persistent_kwargs = None
        self.last_user_data_dir = None
        self.browser = FakeBrowser()
        self.persistent_context = FakeContext()

    def launch(self, **kwargs) -> FakeBrowser:
        self.last_launch_kwargs = kwargs
        return self.browser

    def launch_persistent_context(self, user_data_dir: str, **kwargs) -> FakeContext:
        self.last_user_data_dir = user_data_dir
        self.last_persistent_kwargs = kwargs
        return self.persistent_context


class FakePlaywright:
    def __init__(self) -> None:
        self.chromium = FakeChromium()


class TestBrowserContextBuilder(unittest.TestCase):
    def test_build_browser_context_returns_ephemeral_handle(self) -> None:
        # 验证临时模式会创建 browser + context，并在句柄中一并返回。
        playwright = FakePlaywright()

        def fake_probe(mode: str, user_input: BrowserContextUserInput) -> BrowserContextProbeResult:
            return BrowserContextProbeResult(mode=mode, success=True, detail="ok")

        handle = build_browser_context(
            playwright,
            BrowserContextUserInput(),
            probe=fake_probe,
            headless=True,
        )

        self.assertIs(handle.context, playwright.chromium.browser.created_context)
        self.assertIs(handle.browser, playwright.chromium.browser)
        self.assertEqual(handle.workflow_result.resolved_mode, "default_browser_ephemeral")
        self.assertEqual(playwright.chromium.last_launch_kwargs, {"headless": True})

    def test_build_browser_context_returns_persistent_handle(self) -> None:
        # 验证持久化模式会直接返回 persistent context，并传入用户数据目录。
        playwright = FakePlaywright()

        def fake_probe(mode: str, user_input: BrowserContextUserInput) -> BrowserContextProbeResult:
            return BrowserContextProbeResult(mode=mode, success=True, detail="ok")

        handle = build_browser_context(
            playwright,
            BrowserContextUserInput(
                browser_executable_path="C:/Edge/msedge.exe",
                user_data_dir="D:/browser_data",
            ),
            probe=fake_probe,
        )

        self.assertIs(handle.context, playwright.chromium.persistent_context)
        self.assertIsNone(handle.browser)
        self.assertEqual(handle.workflow_result.resolved_mode, "full_persistent")
        self.assertEqual(playwright.chromium.last_user_data_dir, "D:/browser_data")
        self.assertEqual(
            playwright.chromium.last_persistent_kwargs,
            {"executable_path": "C:/Edge/msedge.exe", "headless": False},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
