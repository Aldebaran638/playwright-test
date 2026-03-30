import json
from pathlib import Path

from loguru import logger
from playwright.sync_api import BrowserContext, Playwright


EDGE_EXECUTABLE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
EDGE_USER_DATA_DIR = Path(r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2")
EDGE_PROFILE_DIRECTORY = "Default"
STEALTH_SCRIPT_PATH = Path(__file__).resolve().parent / "assets" / "stealth.min.js"
COOKIES_FILE_PATH = Path(__file__).resolve().parents[2] / "cookies.json"


def launch_tyc_browser_context(playwright: Playwright) -> BrowserContext:
    # 统一管理 tyc 使用的浏览器环境，并在上下文创建后注入 stealth.js。
    if not EDGE_EXECUTABLE_PATH.exists():
        raise FileNotFoundError(f"missing Edge executable: {EDGE_EXECUTABLE_PATH}")
    if not EDGE_USER_DATA_DIR.exists():
        raise FileNotFoundError(f"missing Edge user data dir: {EDGE_USER_DATA_DIR}")
    if not STEALTH_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"missing stealth script: {STEALTH_SCRIPT_PATH}")

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(EDGE_USER_DATA_DIR),
        executable_path=str(EDGE_EXECUTABLE_PATH),
        headless=False,
        slow_mo=100,
        args=[f"--profile-directory={EDGE_PROFILE_DIRECTORY}"],
    )
    context.add_init_script(path=str(STEALTH_SCRIPT_PATH))
    
    # 加载cookies
    load_cookies(context)
    
    return context


def save_cookies(context: BrowserContext) -> None:
    """
    保存cookies到文件
    
    Args:
        context: Playwright BrowserContext 对象
    """
    try:
        cookies = context.cookies()
        with open(COOKIES_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        logger.info(f"[模块] 成功保存cookies到 {COOKIES_FILE_PATH}")
    except Exception as e:
        logger.error(f"[模块] 保存cookies失败: {e}")


def load_cookies(context: BrowserContext) -> None:
    """
    从文件加载cookies
    
    Args:
        context: Playwright BrowserContext 对象
    """
    try:
        if COOKIES_FILE_PATH.exists():
            with open(COOKIES_FILE_PATH, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
            logger.info(f"[模块] 成功从 {COOKIES_FILE_PATH} 加载cookies")
        else:
            logger.info(f"[模块] 未找到cookies文件: {COOKIES_FILE_PATH}")
    except Exception as e:
        logger.error(f"[模块] 加载cookies失败: {e}")

