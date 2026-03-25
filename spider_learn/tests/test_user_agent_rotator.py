"""Tests for the user agent rotator module."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

from loguru import logger

# 允许直接运行当前测试脚本时也能找到 spider_learn 下的模块。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入被测试函数，下面会直接调用它获取随机 UA。
from modules.user_agent_rotator import get_rotating_user_agent

# 打开调试日志，方便观察测试过程里的 UA 输出。
logger.remove()
logger.add(sys.stdout, level="DEBUG")


class UserAgentRotatorTests(unittest.TestCase):
    def test_returns_a_plausible_user_agent(self) -> None:
        # 调用被测试函数，获取一个随机且可信的桌面浏览器 UA。
        logger.debug("[测试1] 开始调用 get_rotating_user_agent()")
        user_agent = get_rotating_user_agent()
        logger.debug("[测试1] 函数返回的 UA: {ua}", ua=user_agent)

        self.assertTrue(user_agent.startswith("Mozilla/5.0"))
        self.assertNotIn("HeadlessChrome", user_agent)
        self.assertNotIn("PhantomJS", user_agent)
        self.assertTrue(
            any(token in user_agent for token in ("Chrome/", "Firefox/", "Safari/", "Edg/")),
            msg=f"Unexpected UA format: {user_agent}",
        )

    def test_rotation_produces_multiple_user_agents(self) -> None:
        # 连续调用被测试函数，确认它会返回不同的 UA。
        logger.debug("[测试2] 开始连续调用 get_rotating_user_agent() 12 次")
        user_agents = [get_rotating_user_agent() for _ in range(12)]
        unique_user_agents = set(user_agents)

        logger.debug("[测试2] 已生成 UA 总数: {count}, 去重后数量: {unique}", count=len(user_agents), unique=len(unique_user_agents))
        for user_agent in sorted(unique_user_agents):
            logger.debug("[测试2] 去重后的 UA 样本: {ua}", ua=user_agent)

        self.assertGreaterEqual(len(unique_user_agents), 2)


if __name__ == "__main__":
    # 支持用 python 直接执行当前测试文件。
    unittest.main(verbosity=1)
