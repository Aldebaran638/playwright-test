import sys
import unittest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from zhy.modules.common.browser_cookies import load_cookies_if_present, save_cookies


# 本测试文件用于验证 browser_cookies 模块的核心行为是否符合预期。
# 整体测试思路是：模拟浏览器上下文和文件操作，验证 cookie 加载和保存功能的正确性。
#
# 具体测试方案包括：
# 1. 成功加载场景：验证当 cookie 文件存在且有效时，是否能正确加载到浏览器上下文
# 2. 文件不存在场景：验证当 cookie 文件不存在时，是否能正确跳过加载
# 3. 空 cookie 场景：验证当 cookie 文件存在但内容为空时，是否能正确跳过加载
# 4. 保存 cookie 场景：验证是否能正确将浏览器上下文的 cookie 保存到文件
class TestBrowserCookies(unittest.IsolatedAsyncioTestCase):
    # 测试当 cookie 文件存在且有效时，是否能正确加载到浏览器上下文
    async def test_loads_cookies_successfully_when_file_exists(self) -> None:
        mock_context = AsyncMock()
        mock_context.add_cookies = AsyncMock()
        
        test_cookies = [{"name": "test", "value": "value"}]
        cookie_path = Path("test_cookies.json")
        cookie_path.write_text(json.dumps(test_cookies), encoding="utf-8")
        
        try:
            await load_cookies_if_present(mock_context, cookie_path)
            mock_context.add_cookies.assert_called_once_with(test_cookies)
        finally:
            if cookie_path.exists():
                cookie_path.unlink()
    
    # 测试当 cookie 文件不存在时，是否能正确跳过加载
    async def test_skips_loading_when_file_does_not_exist(self) -> None:
        mock_context = AsyncMock()
        mock_context.add_cookies = AsyncMock()
        
        non_existent_path = Path("non_existent_cookies.json")
        if non_existent_path.exists():
            non_existent_path.unlink()
        
        await load_cookies_if_present(mock_context, non_existent_path)
        mock_context.add_cookies.assert_not_called()
    
    # 测试当 cookie 文件存在但内容为空时，是否能正确跳过加载
    async def test_skips_loading_when_cookies_are_empty(self) -> None:
        mock_context = AsyncMock()
        mock_context.add_cookies = AsyncMock()
        
        cookie_path = Path("empty_cookies.json")
        cookie_path.write_text("[]", encoding="utf-8")
        
        try:
            await load_cookies_if_present(mock_context, cookie_path)
            mock_context.add_cookies.assert_not_called()
        finally:
            if cookie_path.exists():
                cookie_path.unlink()
    
    # 测试是否能正确将浏览器上下文的 cookie 保存到文件
    async def test_saves_cookies_successfully(self) -> None:
        mock_context = AsyncMock()
        test_cookies = [{"name": "test", "value": "value"}]
        mock_context.cookies = AsyncMock(return_value=test_cookies)
        
        cookie_path = Path("saved_cookies.json")
        if cookie_path.exists():
            cookie_path.unlink()
        
        try:
            await save_cookies(mock_context, cookie_path)
            self.assertTrue(cookie_path.exists())
            saved_cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
            self.assertEqual(saved_cookies, test_cookies)
        finally:
            if cookie_path.exists():
                cookie_path.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)
