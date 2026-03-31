import json
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from loguru import logger
from playwright.sync_api import BrowserContext, Playwright, Error as PlaywrightError


STEALTH_SCRIPT_PATH = Path(__file__).resolve().parent / "assets" / "stealth.min.js"
COOKIES_FILE_PATH = Path(__file__).resolve().parents[2] / "cookies.json"


class BrowserContextResult:
    """浏览器上下文结果类"""
    def __init__(self):
        self.requested_mode: str = ""
        self.resolved_mode: str = ""
        self.success: bool = False
        self.used_fallback: bool = False
        self.fallback_chain: list[str] = []
        self.reason: str = ""
        self.messages: list[str] = []
        self.context: Optional[BrowserContext] = None


def launch_tyc_browser_context(
    playwright: Playwright,
    browser_executable_path: Optional[Path] = None,
    user_data_dir: Optional[Path] = None
) -> Tuple[BrowserContext, Dict[str, Any]]:
    """
    统一管理 tyc 使用的浏览器环境，并在上下文创建后注入 stealth.js。
    
    Args:
        playwright: Playwright 对象
        browser_executable_path: 浏览器可执行文件路径
        user_data_dir: 浏览器数据文件夹路径
        
    Returns:
        Tuple[BrowserContext, Dict[str, Any]]: 浏览器上下文和决策信息
    """
    result = BrowserContextResult()
    
    # 检查stealth脚本
    if not STEALTH_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"missing stealth script: {STEALTH_SCRIPT_PATH}")
    
    # 确定目标模式
    if browser_executable_path and user_data_dir:
        result.requested_mode = "full_persistent"
        result.fallback_chain.append("full_persistent")
        logger.info(f"[模块] 尝试模式: {result.requested_mode}")
        
        # 测试full_persistent模式
        context, success, reason = _try_full_persistent(
            playwright, browser_executable_path, user_data_dir
        )
        
        if success:
            result.resolved_mode = "full_persistent"
            result.success = True
            result.context = context
        else:
            result.messages.append(f"[模块] 模式 {result.requested_mode} 失败: {reason}")
            logger.warning(f"[模块] 模式 {result.requested_mode} 失败: {reason}")
            
            # 根据失败原因降级
            if not browser_executable_path.exists() or not _is_browser_executable(browser_executable_path):
                # 浏览器不可用，降级到default_browser_persistent
                result.messages.append("[模块] 浏览器不可用，降级到 default_browser_persistent")
                logger.info("[模块] 浏览器不可用，降级到 default_browser_persistent")
                result.fallback_chain.append("default_browser_persistent")
                
                context, success, reason = _try_default_browser_persistent(playwright, user_data_dir)
                if success:
                    result.resolved_mode = "default_browser_persistent"
                    result.success = True
                    result.used_fallback = True
                    result.context = context
                else:
                    result.messages.append(f"[模块] 模式 default_browser_persistent 失败: {reason}")
                    logger.warning(f"[模块] 模式 default_browser_persistent 失败: {reason}")
                    # 继续降级到default_browser_ephemeral
                    result.messages.append("[模块] 继续降级到 default_browser_ephemeral")
                    logger.info("[模块] 继续降级到 default_browser_ephemeral")
                    result.fallback_chain.append("default_browser_ephemeral")
                    
                    context, success, reason = _try_default_browser_ephemeral(playwright)
                    if success:
                        result.resolved_mode = "default_browser_ephemeral"
                        result.success = True
                        result.used_fallback = True
                        result.context = context
                    else:
                        result.messages.append(f"[模块] 模式 default_browser_ephemeral 失败: {reason}")
                        logger.error(f"[模块] 模式 default_browser_ephemeral 失败: {reason}")
                        result.reason = "All modes failed"
            else:
                # 数据目录不可用，降级到custom_browser_ephemeral
                result.messages.append("[模块] 数据目录不可用，降级到 custom_browser_ephemeral")
                logger.info("[模块] 数据目录不可用，降级到 custom_browser_ephemeral")
                result.fallback_chain.append("custom_browser_ephemeral")
                
                context, success, reason = _try_custom_browser_ephemeral(playwright, browser_executable_path)
                if success:
                    result.resolved_mode = "custom_browser_ephemeral"
                    result.success = True
                    result.used_fallback = True
                    result.context = context
                else:
                    result.messages.append(f"[模块] 模式 custom_browser_ephemeral 失败: {reason}")
                    logger.warning(f"[模块] 模式 custom_browser_ephemeral 失败: {reason}")
                    # 继续降级到default_browser_ephemeral
                    result.messages.append("[模块] 继续降级到 default_browser_ephemeral")
                    logger.info("[模块] 继续降级到 default_browser_ephemeral")
                    result.fallback_chain.append("default_browser_ephemeral")
                    
                    context, success, reason = _try_default_browser_ephemeral(playwright)
                    if success:
                        result.resolved_mode = "default_browser_ephemeral"
                        result.success = True
                        result.used_fallback = True
                        result.context = context
                    else:
                        result.messages.append(f"[模块] 模式 default_browser_ephemeral 失败: {reason}")
                        logger.error(f"[模块] 模式 default_browser_ephemeral 失败: {reason}")
                        result.reason = "All modes failed"
    elif browser_executable_path:
        result.requested_mode = "custom_browser_ephemeral"
        result.fallback_chain.append("custom_browser_ephemeral")
        logger.info(f"[模块] 尝试模式: {result.requested_mode}")
        
        # 测试custom_browser_ephemeral模式
        context, success, reason = _try_custom_browser_ephemeral(playwright, browser_executable_path)
        
        if success:
            result.resolved_mode = "custom_browser_ephemeral"
            result.success = True
            result.context = context
        else:
            result.messages.append(f"[模块] 模式 {result.requested_mode} 失败: {reason}")
            logger.warning(f"[模块] 模式 {result.requested_mode} 失败: {reason}")
            # 降级到default_browser_ephemeral
            result.messages.append("[模块] 降级到 default_browser_ephemeral")
            logger.info("[模块] 降级到 default_browser_ephemeral")
            result.fallback_chain.append("default_browser_ephemeral")
            
            context, success, reason = _try_default_browser_ephemeral(playwright)
            if success:
                result.resolved_mode = "default_browser_ephemeral"
                result.success = True
                result.used_fallback = True
                result.context = context
            else:
                result.messages.append(f"[模块] 模式 default_browser_ephemeral 失败: {reason}")
                logger.error(f"[模块] 模式 default_browser_ephemeral 失败: {reason}")
                result.reason = "All modes failed"
    elif user_data_dir:
        result.requested_mode = "default_browser_persistent"
        result.fallback_chain.append("default_browser_persistent")
        logger.info(f"[模块] 尝试模式: {result.requested_mode}")
        
        # 测试default_browser_persistent模式
        context, success, reason = _try_default_browser_persistent(playwright, user_data_dir)
        
        if success:
            result.resolved_mode = "default_browser_persistent"
            result.success = True
            result.context = context
        else:
            result.messages.append(f"[模块] 模式 {result.requested_mode} 失败: {reason}")
            logger.warning(f"[模块] 模式 {result.requested_mode} 失败: {reason}")
            # 降级到default_browser_ephemeral
            result.messages.append("[模块] 降级到 default_browser_ephemeral")
            logger.info("[模块] 降级到 default_browser_ephemeral")
            result.fallback_chain.append("default_browser_ephemeral")
            
            context, success, reason = _try_default_browser_ephemeral(playwright)
            if success:
                result.resolved_mode = "default_browser_ephemeral"
                result.success = True
                result.used_fallback = True
                result.context = context
            else:
                result.messages.append(f"[模块] 模式 default_browser_ephemeral 失败: {reason}")
                logger.error(f"[模块] 模式 default_browser_ephemeral 失败: {reason}")
                result.reason = "All modes failed"
    else:
        result.requested_mode = "default_browser_ephemeral"
        result.fallback_chain.append("default_browser_ephemeral")
        logger.info(f"[模块] 尝试模式: {result.requested_mode}")
        
        # 测试default_browser_ephemeral模式
        context, success, reason = _try_default_browser_ephemeral(playwright)
        
        if success:
            result.resolved_mode = "default_browser_ephemeral"
            result.success = True
            result.context = context
        else:
            result.messages.append(f"[模块] 模式 {result.requested_mode} 失败: {reason}")
            logger.error(f"[模块] 模式 {result.requested_mode} 失败: {reason}")
            result.reason = "All modes failed"
    
    # 如果成功创建上下文，注入stealth脚本并加载cookies
    if result.success and result.context:
        result.context.add_init_script(path=str(STEALTH_SCRIPT_PATH))
        load_cookies(result.context)
        logger.info(f"[模块] 最终使用模式: {result.resolved_mode}")
    else:
        raise Exception(f"Failed to create browser context: {result.reason}")
    
    # 构建返回的决策信息
    decision_info = {
        "requested_mode": result.requested_mode,
        "resolved_mode": result.resolved_mode,
        "success": result.success,
        "used_fallback": result.used_fallback,
        "fallback_chain": result.fallback_chain,
        "reason": result.reason,
        "messages": result.messages
    }
    
    return result.context, decision_info


def _try_full_persistent(
    playwright: Playwright,
    browser_executable_path: Path,
    user_data_dir: Path
) -> Tuple[Optional[BrowserContext], bool, str]:
    """尝试full_persistent模式"""
    try:
        if not browser_executable_path.exists():
            return None, False, "Browser executable not found"
        
        if not user_data_dir.exists():
            return None, False, "User data directory not found"
        
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            executable_path=str(browser_executable_path),
            headless=False,
            slow_mo=100,
            args=["--profile-directory=Default"],
        )
        return context, True, "Success"
    except Exception as e:
        return None, False, str(e)


def _try_custom_browser_ephemeral(
    playwright: Playwright,
    browser_executable_path: Path
) -> Tuple[Optional[BrowserContext], bool, str]:
    """尝试custom_browser_ephemeral模式"""
    try:
        if not browser_executable_path.exists():
            return None, False, "Browser executable not found"
        
        browser = playwright.chromium.launch(
            executable_path=str(browser_executable_path),
            headless=False,
            slow_mo=100
        )
        context = browser.new_context()
        return context, True, "Success"
    except Exception as e:
        return None, False, str(e)


def _try_default_browser_persistent(
    playwright: Playwright,
    user_data_dir: Path
) -> Tuple[Optional[BrowserContext], bool, str]:
    """尝试default_browser_persistent模式"""
    try:
        if not user_data_dir.exists():
            return None, False, "User data directory not found"
        
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            slow_mo=100,
            args=["--profile-directory=Default"],
        )
        return context, True, "Success"
    except Exception as e:
        return None, False, str(e)


def _try_default_browser_ephemeral(
    playwright: Playwright
) -> Tuple[Optional[BrowserContext], bool, str]:
    """尝试default_browser_ephemeral模式"""
    try:
        browser = playwright.chromium.launch(
            headless=False,
            slow_mo=100
        )
        context = browser.new_context()
        return context, True, "Success"
    except Exception as e:
        return None, False, str(e)


def _is_browser_executable(path: Path) -> bool:
    """检查是否为浏览器可执行文件"""
    try:
        return path.is_file() and path.suffix in [".exe", ""]
    except Exception:
        return False


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

