import json
from pathlib import Path

from loguru import logger
from playwright.async_api import BrowserContext


# 简介：如果本地 Cookie 文件存在，就把 Cookie 加载到当前浏览器上下文。
# 参数：
# - context: 当前浏览器上下文。
# - cookie_path: Cookie 文件路径。
# 返回值：
# - 无返回值。
# 逻辑：
# - 文件不存在或内容为空时直接跳过；否则读取 JSON 后调用 add_cookies。
async def load_cookies_if_present(context: BrowserContext, cookie_path: Path) -> None:
    if not cookie_path.exists():
        return

    cookies = json.loads(cookie_path.read_text(encoding="utf-8"))
    if not cookies:
        return

    await context.add_cookies(cookies)
    logger.info("[browser_cookies] loaded {} cookies from {}", len(cookies), cookie_path)


# 简介：把当前浏览器上下文中的 Cookie 持久化到本地文件。
# 参数：
# - context: 当前浏览器上下文。
# - cookie_path: Cookie 文件路径。
# 返回值：
# - 无返回值。
# 逻辑：
# - 先确保目录存在，再获取 cookies 列表并序列化写入 JSON 文件。
async def save_cookies(context: BrowserContext, cookie_path: Path) -> None:
    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    cookies = await context.cookies()
    cookie_path.write_text(
        json.dumps(cookies, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("[browser_cookies] saved cookies to {}", cookie_path)