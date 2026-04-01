import json
import re
import sys
import time
from pathlib import Path
from typing import Any, List, Dict

from loguru import logger
from playwright.sync_api import Playwright, sync_playwright, Page, BrowserContext


# 常量定义
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tyc.modules.risk_2.navigate import navigate_to_risk_page
from tyc.modules.risk_2.extract import extract_risk_data
from tyc.modules.run_step import run_step, StepResult
from tyc.modules.browser_context import launch_tyc_browser_context, save_cookies
from tyc.modules.go_to_home import go_to_home_page
from tyc.modules.login_state import wait_until_logged_in


RISK_SEARCH_URL = "https://www.tianyancha.com/risk"
# 将输出文件路径改为 tyc\modules\risk_2 文件夹下
OUTPUT_FILE = Path(__file__).resolve().parent / "risk_2_results.json"
TYC_HOME_URL = "https://www.tianyancha.com/"

# Edge 浏览器配置（可根据需要修改）
EDGE_EXECUTABLE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
EDGE_USER_DATA_DIR = Path(r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2")

# 测试公司列表（可根据需要修改）
test_companies = [
    "阿鲁科尔沁旗罕乌拉街道理棠皮肤护理会所",
    "阿谱赛国际科技发展（北京）有限公司",
    "艾后生物科技（上海）有限公司",
    "艾琳生物制造（江苏）有限公司",
    "艾研实业（上海）有限公司",
    "艾因特丽（苏州）生物科技有限公司",
    "爱肌色（河南）生物科技有限公司",
    "爱乐士（惠州）化妆品有限公司",
    "爱生泽（上海）生物科技有限公司",
    "安徽创领化妆品科技有限公司",
    "安徽椿禾科技有限公司",
    "安徽玳妍生物科技有限公司",
    "安徽德莱康生物医疗科技有限公司",
    "安徽科门生物科技有限公司",
    "安徽科治医疗科技有限公司",
    "安徽链创品牌管理有限公司",
    "安徽润叶生物科技有限公司",
    "安徽鑫冉美生物科技有限公司",
    "安徽一威欧生供应链有限公司",
    "安徽孕大夫生物科技有限公司",
    "安婕妤化妆品科技股份有限公司",
    "安阳蓝玫生物科技有限公司",
    "傲雪（广州）生物科技有限公司",
    "奥珀莱健康产业科技（广州）有限公司",
    "奥妍（上海）化妆品商贸有限公司",
    "奥易生物科技（杭州）有限公司",
    "澳宝化妆品（惠州）有限公司",
    "澳诗澜（广州）药业有限公司",
    "澳思美科技（广州）有限公司",
    "澳亚生物医药科技（广州）有限公司",
    "百世妥技术（深圳）有限公司",
    "百特威（海南）供应链管理有限公司",
    "百特威（上海）化妆品有限公司",
    "栢锐（东莞）科技贸易有限公司",
    "拜斯特药业（广州）有限公司",
    "宝肌（广州）医疗美容投资有限责任公司",
    "宝爵生物科技（广州）有限公司",
    "宝丽（广东）生物科技有限公司",
    "保定肤钥琳生物科技有限公司",
    "北京安秀科技发展有限公司",
    "北京葆来生物科技有限公司",
    "北京贝潞生物科技有限公司",
    "北京地尧科技有限公司",
    "北京蒂芙润生物科技有限公司",
    "北京梵泽心悦生物科技有限公司",
    "北京芙洛迪科技有限公司",
    "北京好美洋生物技术有限公司",
    "北京华纳微校文化传媒有限公司",
    "北京华妍生物科技有限公司",
    "北京康宝得美健康管理有限公司",
    "北京科学城日化有限公司",
    "北京利和冏冏科技有限公司",
    "北京利和制药有限公司",
    "北京茂思商贸有限公司",
    "北京美好小事科技有限公司",
    "北京美丽臻颜化妆品有限公司",
    "北京美颜家科技有限公司",
    "北京名世金颜科技有限公司",
    "北京沛奇科技有限公司",
    "北京普隆达科贸有限公司",
    "北京青颜博识健康管理有限公司",
    "北京热景生物科技股份有限公司",
    "北京瑞贝可生物科技有限公司",
    "北京瑞丽天承医疗美容诊所有限公司",
    "北京赛多克生物科技有限公司",
    "北京石榴健康科技有限公司",
    "北京同仁堂健康药业股份有限公司",
    "北京薇肯生物科技有限公司",
    "北京弦云生物科技有限公司",
    "北京幸福益生再生医学科技有限公司",
    "北京奕科医学研究院",
    "北京植物医生生物科技有限公司",
    "北京至乐界生物科技有限公司",
    "北京紫琪医疗科技有限公司",
    "北粤药业（广东）有限公司",
    "卞在雄",
    "伯德创研（广州）生物科技有限公司",
    "伯德智造（广州）生物科技有限公司",
    "铂臻（广州）生物科技有限公司",
    "博德生物技术（德州）有限公司",
    "博汇美萃生物工程技术（广东）有限公司",
    "不止化妆品(上海)有限公司",
    "采研国际医药科技研究（广东）有限公司",
    "长春市紫秘笈生物科技有限公司",
    "长青生物技术有限公司",
    "长沙黛西生物科技有限公司",
    "长沙观颂源生物科技有限公司",
    "长沙迈芮生物医药有限公司",
    "长沙牛得很网络科技有限公司",
    "长沙市芙蓉区嘉人化妆品经营部",
    "长沙市开福区丹提化妆品经营部",
    "长沙天南医疗管理有限公司",
    "长兴中科明圣生物技术有限公司",
    "常州谙美生物科技有限公司",
    "常州百瑞吉生物医药股份有限公司",
    "常州诺莎商贸有限公司",
    "常州仕萃姿医疗器械有限公司",
    "常州药物研究所有限公司",
    "常州药物研究所有限公司第一分公司",
    "郴州纤华生物科技有限公司",
    "晨笛医药科技(上海)有限公司",
    "成都恒美盛生物科技有限公司",
    "成都欧泊商贸有限责任公司",
    "成都普什制药有限公司",
    "成都青山利康药业股份有限公司双流分公司",
    "成都宇泽康养生物技术推广服务有限公司",
    "成都宇泽联华生物科技有限公司",
    "承德蒂璞凯瑞生物科技有限公司",
    "承基（珠海横琴）医药科技有限公司",
    "橙品（广州）设计研发有限公司",
    "池州达尔智电子商务有限公司",
    "赤峰仁泽化妆品有限公司",
    "初之印（上海）化妆品有限公司",
    "楚雅化妆品（上海）有限公司",
    "楚业健康产业（广州）有限公司",
    "创惠葆生物科技（上海）有限公司",
    "创庭化妆品科技（上海）有限公司",
    "创庭生物科技(上海)有限公司",
    "创赢新材料科技（广州）有限公司",
    "春日来信（上海）生物科技有限公司",
    "纯富供应链科技（上海）有限公司",
    "纯沅（佛山）医药生物科技有限公司",
    "纯之熙（北京）生物科技有限公司",
    "大疆（天津）生物制药有限公司",
    "大连韩朴生物工程有限公司",
    "大连美烁药业有限公司",
    "大连双迪科技股份有限公司",
    "大美仁生物制造（江苏）有限公司",
    "大通汉麻生物科技研究院（青岛）有限公司",
    "大涯国际进出口深圳有限公司",
    "待定客户",
    "黛郡（广州）科技有限公司",
    "德慧（大连）国际贸易有限公司",
    "德薇（上海）化妆品有限公司",
    "德亿美生技术有限公司",
    "蝶泉（广东）生物科技有限公司",
    "蝶柔化妆品(浙江)有限公司",
    "东方美谷企业集团美创（上海）科技有限公司",
    "东莞东芳漾生物科技有限公司",
    "东莞力大化妆品有限公司",
    "东莞美态生物科技有限公司",
    "东莞市艾欧西实业有限公司",
    "东莞市贝芝商贸有限公司",
    "东莞市乘美生物科技有限公司",
    "东莞市东和日化用品有限公司",
    "东莞市加减乘除生物科技有限公司",
    "东莞市金贝肤化妆品有限公司",
    "东莞市力大生命健康科技有限公司",
    "东莞市塑伽管理咨询有限公司",
    "东莞市维琪科技有限公司",
    "东莞市羽馨化妆品有限公司",
    "东莞市悦泽生物科技有限公司",
    "东阳市欧恋化妆品有限公司",
    "東湶貿易股份有限公司",
    "洞玛生物技术（深圳）有限公司",
    "恩客斯（上海）化妆品有限公司",
    "二元（苏州）工业科技有限公司",
    "法致（上海）化妆品有限公司",
    "范莎",
    "梵乔（苏州）生物科技有限公司",
    "芳香奏鸣曲（天津）科贸有限公司",
    "芳妍（上海）生物科技有限公司",
    "菲朗生物科技（湖北）有限公司",
    "菲诗倾城（广州）生物科技有限公司",
    "佛山美婕斯生物科技有限公司",
    "佛山市奥姿美生物科技有限公司",
    "佛山市纯悦雅科技有限公司",
    "佛山市可佳生物科技有限公司",
    "佛山市立图包装有限公司",
    "佛山市南海区舟航精细日用化工有限公司",
    "佛山市三水飞马包装有限公司",
    "佛山市顺德区香江精细化工实业有限公司",
    "佛山市皙贝生物科技有限公司",
    "佛山市鑫宝堂医药生物科技有限公司",
    "佛山市妍发生物科技有限公司",
    "佛山素本生物科技有限公司",
    "佛山新森印刷科技有限公司",
    "福建艾尚化妆品有限公司",
    "福建东亮生物科技有限公司",
    "福建晶华生物科技有限公司",
    "福建省轻工业研究所中间试验工厂",
    "福州艾维德生物医药有限公司",
    "抚州市临川区丝一域养发馆（个体工商户）",
    "复皙药业（上海）有限公司",
    "高莎科技(苏州)有限公司",
    "鼓楼区巧凝化妆品经营部",
    "鼓楼区燕云化妆品经营部",
    "鼓楼区玉莹化妆品经营部",
    "广东艾圣日用化学品有限公司",
    "广东澳莎医药科技有限公司",
    "广东巴松那生物科技有限公司",
    "广东柏文生物科技股份有限公司",
    "广东柏亚化妆品有限公司",
    "广东保格丽生物科技实业有限公司",
    "广东贝豪生物科技有限公司",
    "广东贝诗特生物科技有限公司",
    "广东碧素堂生物科技有限公司",
    "广东博然堂生物科技有限公司",
    "广东大澳生物科技有限公司",
    "广东大一生物科技有限公司",
    "广东袋鼠妈妈集团有限公司",
    "广东鼎纯生物医药科技有限公司",
    "广东鼎尖国际生物科技有限公司",
    "广东定悦医药科技有限公司",
]


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
                
                # ── step 2: 提取 ──────────────────────────────
                ext = run_step(
                    extract_risk_data,
                    page1,
                    company,
                    step_name=f"提取-{company}",
                    critical=False,
                    retries=0,
                )
                if not ext.ok:
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
                # 确保 ext.value 是列表类型
                risk_records = []
                if ext.value is not None:
                    if isinstance(ext.value, list):
                        risk_records = ext.value
                    else:
                        logger.warning(f"[risk_2.main] ext.value 不是列表类型: {type(ext.value)}")
                
                company_result = {
                    "company_name": company,
                    "success": True,
                    "risk_records": risk_records,
                }
                results.append(company_result)
                logger.info(f"[risk_2.main] 公司处理完成: {company}, 记录数: {len(risk_records)}")
                
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
    logger.info(f"[risk_2.main] 开始测试风险2分析，测试公司: {test_companies}")
    
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
