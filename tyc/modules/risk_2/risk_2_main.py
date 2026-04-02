import json
import re
import sys
import time
from pathlib import Path
from typing import Any, List, Dict
from datetime import datetime

from loguru import logger
from playwright.sync_api import Playwright, sync_playwright, Page, BrowserContext


# 常量定义
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2.navigate import navigate_to_risk_page
from tyc.modules.risk_2.extract import extract_risk_data, _extract_date_from_string
from tyc.modules.run_step import run_step, StepResult
from tyc.modules.browser_context import launch_tyc_browser_context, save_cookies
from tyc.modules.go_to_home import go_to_home_page
from tyc.modules.login_state import wait_until_logged_in


RISK_SEARCH_URL = "https://www.tianyancha.com/risk"
# 将输出文件路径改为 tyc\modules\risk_2 文件夹下
OUTPUT_FILE = Path(__file__).resolve().parent / "risk_2_results.json"
TYC_HOME_URL = "https://www.tianyancha.com/"

# 日期范围配置
DATE_START = "2020-01-01"  # 起始日期
DATE_END = "2026-12-31"    # 结束日期

# 查询条数配置
MAX_QUERY_COUNT = 100      # 最大查询条数
MAX_PAGE_TURNS = 20        # 最大翻页次数

# Edge 浏览器配置（可根据需要修改）
EDGE_EXECUTABLE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
EDGE_USER_DATA_DIR = Path(r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2")

# 从文件中读取测试公司列表
def load_companies_from_file() -> List[str]:
    """
    从 name_list.txt 文件中读取公司列表
    
    Returns:
        公司名称列表
    """
    name_list_path = Path(__file__).resolve().parent.parent / "name_list_test.txt"
    if not name_list_path.exists():
        logger.error(f"[risk_2.main] 公司列表文件不存在: {name_list_path}")
        return []
    
    try:
        with open(name_list_path, "r", encoding="utf-8") as f:
            companies = [line.strip() for line in f if line.strip()]
        logger.info(f"[risk_2.main] 从文件中读取了 {len(companies)} 个公司")
        return companies
    except Exception as e:
        logger.error(f"[risk_2.main] 读取公司列表文件失败: {e}")
        return []

# 测试公司列表（从文件中读取）
test_companies = load_companies_from_file()


def validate_dates():
    """
    验证日期格式和逻辑
    
    Returns:
        bool: 验证是否成功
    """
    try:
        # 验证日期格式
        start_date = datetime.strptime(DATE_START, "%Y-%m-%d")
        end_date = datetime.strptime(DATE_END, "%Y-%m-%d")
        
        # 验证结束日期晚于起始日期
        if end_date <= start_date:
            logger.error(f"[risk_2.main] 结束日期 {DATE_END} 必须晚于起始日期 {DATE_START}")
            return False
        
        logger.info(f"[risk_2.main] 日期验证通过：{DATE_START} 至 {DATE_END}")
        return True
    except ValueError as e:
        logger.error(f"[risk_2.main] 日期格式错误：{e}")
        return False


def _has_valid_date_in_range(record: Dict[str, Any], start_date: str, end_date: str) -> bool:
    """
    检查记录是否有符合日期范围的日期字段

    Args:
        record: 风险记录
        start_date: 起始日期字符串
        end_date: 结束日期字符串

    Returns:
        bool: True表示有符合日期范围的日期字段，False表示没有
    """
    fields = record.get("fields", {})

    for key, value in fields.items():
        if not any(keyword in key for keyword in ["日期", "时间", "刊登", "发布", "发生"]):
            continue

        values = value if isinstance(value, list) else [value]

        for one_value in values:
            date_str = _extract_date_from_string(str(one_value))
            if not date_str:
                continue

            try:
                if len(date_str) == 10:
                    record_date = datetime.strptime(date_str, "%Y-%m-%d")
                else:
                    record_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M")

                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")

                if start <= record_date <= end:
                    return True
            except ValueError:
                continue

    return False


def _should_continue_paging(records: List[Dict[str, Any]], start_date: str, end_date: str) -> bool:
    """
    检查是否需要继续翻页

    Args:
        records: 已抓取的记录列表
        start_date: 起始日期字符串
        end_date: 结束日期字符串

    Returns:
        bool: True表示需要继续翻页，False表示不需要
    """
    if not records:
        return True

    # 检查最后一条记录
    last_record = records[-1]
    return _has_valid_date_in_range(last_record, start_date, end_date)


def _has_next_page(page: Page) -> bool:
    """
    检查是否存在下一页

    Args:
        page: 页面对象

    Returns:
        bool: True表示存在下一页，False表示不存在
    """
    try:
        next_button = page.locator(".tic.tic-laydate-next-m")
        return next_button.count() > 0
    except Exception:
        return False


def _turn_page(page: Page) -> bool:
    """
    执行翻页操作

    Args:
        page: 页面对象

    Returns:
        bool: True表示翻页成功，False表示翻页失败
    """
    try:
        # 等待翻页元素出现
        next_button = page.locator(".tic.tic-laydate-next-m")
        next_button.wait_for(state="visible", timeout=5000)

        # 点击翻页
        turn_result = run_step(
            next_button.click,
            step_name="点击下一页",
            critical=True,
            retries=1,
        )

        if not turn_result.ok:
            return False

        # 等待新页面加载完成
        wait_result = run_step(
            page.wait_for_load_state,
            "networkidle",
            step_name="等待新页面加载",
            critical=True,
            retries=2,
        )

        return wait_result.ok
    except Exception as e:
        logger.warning(f"[risk_2.main] 翻页失败: {e}")
        return False


def reset_to_search_page(page: Page) -> None:
    """
    将 page 无条件重置回查风险搜索页
    """
    logger.info("[risk_2.main] 重置到查风险搜索页")
    
    # 使用 goto 重置页面，不依赖浏览器历史
    run_step(
        page.goto,
        RISK_SEARCH_URL,
        step_name="跳转到查风险搜索页",
        critical=True,
        retries=1,
    )
    
    # 等待搜索框出现，确认页面就绪
    search_box = page.get_by_role("textbox").first
    run_step(
        search_box.wait_for,
        step_name="等待搜索框加载",
        critical=True,
        retries=2,
    )
    
    logger.info("[risk_2.main] 已成功重置到查风险搜索页")


def _save_results(results: List[Dict[str, Any]], failed_companies: List[str]) -> None:
    """保存结果到文件"""
    try:
        output_data = {
            "analysis_params": {
                "date_start": DATE_START,
                "date_end": DATE_END
            },
            "successful_results": results,
            "failed_companies": failed_companies
        }
        OUTPUT_FILE.write_text(
            json.dumps(output_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"[risk_2.main] 已保存结果到: {OUTPUT_FILE}")
    except Exception as exc:
        logger.error(f"[risk_2.main] 保存结果失败: {exc}")


def get_entry_page(context: BrowserContext) -> Page:
    """获取入口页面，优先使用已有页面"""
    if context.pages:
        return context.pages[0]
    return context.new_page()


def process_risk_2(
    companies: List[str],
    *, 
    browser_executable_path: Path | None = None,
    user_data_dir: Path | None = None,
    headless: bool = False,
) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    处理风险2分析的主函数
    
    Args:
        companies: 公司名称列表
        browser_executable_path: 浏览器可执行文件路径
        user_data_dir: 用户数据目录路径
        headless: 是否使用无头模式
    
    Returns:
        tuple[成功结果列表, 失败公司列表]
    """
    logger.info(f"[risk_2.main] 开始处理风险2分析，公司数: {len(companies)}")
    
    # 验证日期
    if not validate_dates():
        logger.error("[risk_2.main] 日期验证失败，中止流程")
        return [], companies
    
    # 如果没有提供浏览器配置，使用默认的 Edge 配置
    if browser_executable_path is None:
        browser_executable_path = EDGE_EXECUTABLE_PATH
    if user_data_dir is None:
        user_data_dir = EDGE_USER_DATA_DIR
    
    results: List[Dict[str, Any]] = []
    failed_companies: List[str] = []
    
    with sync_playwright() as playwright:
        context = None
        page0 = None
        page1 = None
        
        try:
            # 1. 使用固定浏览器上下文启动浏览器
            logger.info("[risk_2.main] 启动浏览器上下文")
            context_result = run_step(
                launch_tyc_browser_context,
                playwright,
                browser_executable_path,
                user_data_dir,
                step_name="启动浏览器上下文",
                critical=True,
                retries=0,
            )
            if not context_result.ok or context_result.value is None:
                logger.error("[risk_2.main] 浏览器上下文启动失败")
                return results, companies  # 所有公司都失败
            
            context, decision_info = context_result.value
            logger.info(f"[risk_2.main] 浏览器环境决策: {decision_info}")
            
            # 2. 获取入口页面
            page0 = get_entry_page(context)
            
            # 3. 打开天眼查首页
            home_result = run_step(
                go_to_home_page,
                page0,
                home_url=TYC_HOME_URL,
                step_name="打开天眼查首页",
                critical=True,
                retries=2,
            )
            if not home_result.ok:
                logger.error("[risk_2.main] 天眼查首页打开失败")
                return results, companies
            
            # 4. 检查登录状态
            logger.info("[risk_2.main] 开始检查当前登录状态")
            wait_until_logged_in(page0)
            
            # 5. 保存 cookies
            logger.info("[risk_2.main] 登录成功，保存 cookies")
            save_cookies(context)
            
            # 6. 点击应用菜单
            app_menu_result = run_step(
                page0.locator("div").filter(has_text=re.compile(r"^应用$")).first.click,
                step_name="点击应用菜单",
                critical=True,
                retries=1,
            )
            if not app_menu_result.ok:
                logger.error("[risk_2.main] 应用菜单点击失败")
                return results, companies
            
            # 7. 点击查风险，触发弹窗
            with page0.expect_popup() as page1_info:
                risk_button_result = run_step(
                    page0.locator("span").filter(has_text="查风险").click,
                    step_name="点击查风险按钮",
                    critical=True,
                    retries=1,
                )
                if not risk_button_result.ok:
                    logger.error("[risk_2.main] 查风险按钮点击失败")
                    return results, companies
            
            # 8. 获取弹窗页面
            page1 = page1_info.value
            
            # 9. 等待弹窗页面加载
            wait_result = run_step(
                page1.wait_for_load_state,
                "networkidle",
                step_name="等待弹窗页面加载",
                critical=True,
                retries=2,
            )
            if not wait_result.ok:
                logger.error("[risk_2.main] 弹窗页面加载失败")
                return results, companies
            
            logger.info("[risk_2.main] 浏览器初始化完成，开始处理公司")
            
            # 10. 批量处理公司
            for i, company in enumerate(companies):
                # 每处理10个公司，延迟5秒
                if i > 0 and i % 10 == 0:
                    logger.info("[risk_2.main] 已处理10个公司，开始延迟5秒")
                    time.sleep(5)
                    logger.info("[risk_2.main] 延迟完成，继续处理")
                
                logger.info(f"[risk_2.main] 开始处理公司: {company} (第{i+1}/{len(companies)}个)")
                
                # ── step 1: 导航 ──────────────────────────────
                nav = run_step(
                    navigate_to_risk_page,
                    page1,
                    company,
                    step_name=f"导航-{company}",
                    critical=False,
                    retries=1,
                )
                if not nav.ok:
                    logger.warning(f"[risk_2.main] 导航失败，跳过公司: {company}")
                    failed_companies.append(company)
                    
                    # 导航失败后重置搜索页
                    reset_result = run_step(
                        reset_to_search_page,
                        page1,
                        step_name="重置搜索页（导航失败后）",
                        critical=True,
                        retries=1,
                    )
                    if not reset_result.ok:
                        logger.error(f"[risk_2.main] 重置搜索页失败，中止流程")
                        break
                    continue
                
                # 检查是否找到风险信息
                if not nav.value:
                    logger.info(f"[risk_2.main] 未找到 {company} 的风险信息，跳过提取步骤")
                    # 未找到风险信息，不添加到失败列表，直接继续下一个公司
                    
                    # 重置搜索页
                    reset_result = run_step(
                        reset_to_search_page,
                        page1,
                        step_name="重置搜索页（未找到风险信息）",
                        critical=True,
                        retries=1,
                    )
                    if not reset_result.ok:
                        logger.error(f"[risk_2.main] 重置搜索页失败，中止流程")
                        break
                    continue
                
                # ── step 2: 提取（支持翻页）─────────────────────────────
                all_risk_records = []
                page_turn_count = 0
                extract_success = True

                while page_turn_count <= MAX_PAGE_TURNS and len(all_risk_records) < MAX_QUERY_COUNT:
                    ext = run_step(
                        extract_risk_data,
                        page1,
                        company,
                        DATE_START,
                        DATE_END,
                        step_name=f"提取-{company}-第{page_turn_count + 1}页",
                        critical=False,
                        retries=0,
                    )
                    if not ext.ok:
                        logger.warning(f"[risk_2.main] 提取失败（第{page_turn_count + 1}页），跳过公司: {company}")
                        extract_success = False
                        break

                    # 合并记录
                    if ext.value and isinstance(ext.value, list):
                        all_risk_records.extend(ext.value)
                    print(len(all_risk_records))
                    # 检查是否达到最大查询条数
                    if len(all_risk_records) >= MAX_QUERY_COUNT:
                        logger.info(f"[risk_2.main] 已达到最大查询条数 {MAX_QUERY_COUNT}，停止翻页")
                        break

                    # 检查最后一条记录的日期是否在范围内
                    if not _should_continue_paging(all_risk_records, DATE_START, DATE_END):
                        logger.info(f"[risk_2.main] 最后一条记录日期不在范围内，停止翻页")
                        break

                    # 检查是否存在下一页
                    if not _has_next_page(page1):
                        logger.warning(
                            f"[risk_2.main] {company} 没有更多页面，已抓取 {len(all_risk_records)} 条，"
                            f"最大查询条数 {MAX_QUERY_COUNT}"
                        )
                        break

                    # 执行翻页
                    if not _turn_page(page1):
                        logger.warning(f"[risk_2.main] 翻页失败（第{page_turn_count + 1}页），停止翻页")
                        extract_success = False
                        break

                    page_turn_count += 1

                # 处理提取结果
                if not extract_success:
                    logger.warning(f"[risk_2.main] 提取失败，跳过公司: {company}")
                    failed_companies.append(company)
                    
                    # 提取失败后重置搜索页
                    reset_result = run_step(
                        reset_to_search_page,
                        page1,
                        step_name="重置搜索页（提取失败后）",
                        critical=True,
                        retries=1,
                    )
                    if not reset_result.ok:
                        logger.error(f"[risk_2.main] 重置搜索页失败，中止流程")
                        break
                    continue
                
                # ── step 3: 正常完成 ──────────────────────────
                # 确保 all_risk_records 是列表类型
                risk_records = []
                if all_risk_records is not None:
                    if isinstance(all_risk_records, list):
                        risk_records = all_risk_records
                    else:
                        logger.warning(f"[risk_2.main] all_risk_records 不是列表类型: {type(all_risk_records)}")
                
                company_result = {
                    "company_name": company,
                    "success": True,
                    "risk_records": risk_records,
                }
                results.append(company_result)
                logger.info(f"[risk_2.main] 公司处理完成: {company}, 记录数: {len(risk_records)}")
                
                # 每处理完一个公司就保存结果
                _save_results(results, failed_companies)
                
                # 正常完成后重置搜索页
                reset_result = run_step(
                    reset_to_search_page,
                    page1,
                    step_name="返回搜索页（正常完成后）",
                    critical=True,
                    retries=1,
                )
                if not reset_result.ok:
                    logger.error(f"[risk_2.main] 重置搜索页失败，中止流程")
                    break
            
            logger.info(f"[risk_2.main] 所有公司处理完成，成功: {len(results)}, 失败: {len(failed_companies)}")
            
        except Exception as exc:
            logger.error(f"[risk_2.main] 处理过程中发生异常: {exc}")
            # 将剩余未处理的公司标记为失败
            processed_companies = set()
            for r in results:
                if isinstance(r, dict) and "company_name" in r:
                    processed_companies.add(r["company_name"])
            
            for company in companies:
                if company not in processed_companies and company not in failed_companies:
                    failed_companies.append(company)
        
        finally:
            # 确保资源正确关闭
            try:
                if context:
                    run_step(
                        context.close,
                        step_name="关闭浏览器上下文",
                        critical=False,
                        retries=0,
                    )
                logger.info("[risk_2.main] 浏览器资源已释放")
            except Exception as exc:
                logger.warning(f"[risk_2.main] 关闭资源时发生异常: {exc}")
    
    # 保存结果
    _save_results(results, failed_companies)
    
    return results, failed_companies


def main() -> None:
    """测试主函数"""
    if not test_companies:
        logger.error("[risk_2.main] 未加载到公司列表，中止测试")
        return
    
    logger.info(f"[risk_2.main] 开始测试风险2分析，测试公司数: {len(test_companies)}")
    
    results, failed = process_risk_2(
        companies=test_companies,
        browser_executable_path=EDGE_EXECUTABLE_PATH,
        user_data_dir=EDGE_USER_DATA_DIR,
        headless=False,
    )
    
    logger.info(f"[risk_2.main] 测试完成，成功: {len(results)}, 失败: {len(failed)}")
    
    if failed:
        logger.warning(f"[risk_2.main] 失败的公司: {failed}")
    
    # 打印成功结果摘要
    for result in results:
        company_name = result["company_name"]
        record_count = len(result["risk_records"])
        logger.info(f"[risk_2.main] {company_name}: {record_count} 条风险记录")


if __name__ == "__main__":
    main()
