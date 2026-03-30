from pathlib import Path

from playwright.sync_api import BrowserContext, Playwright


EDGE_EXECUTABLE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
EDGE_USER_DATA_DIR = Path(r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2")
EDGE_PROFILE_DIRECTORY = "Default"
STEALTH_SCRIPT_PATH = Path(__file__).resolve().parent / "assets" / "stealth.min.js"


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
    return context
