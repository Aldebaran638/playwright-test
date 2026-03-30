from datetime import datetime
import re
from loguru import logger
from playwright.sync_api import Page

from .vip_detector import is_vip_section
from tyc.modules.run_step import run_step


def extract_sections_by_date(
    page: Page,
    date_start: str,
    date_end: str,
    max_rows: int = 20
) -> list[dict]:
    """
    提取页面中符合日期范围的板块数据
    
    Args:
        page: Playwright Page 对象
        date_start: 日期范围起始，格式 YYYY-MM-DD
        date_end: 日期范围结束，格式 YYYY-MM-DD
        max_rows: 最大抓取行数，默认为20
        
    Returns:
        list[dict]: 符合日期范围的板块数据列表
    """
    logger.info(f"[模块] 开始提取，日期范围：{date_start} ~ {date_end}")
    
    # 入参校验
    try:
        start = datetime.strptime(date_start, "%Y-%m-%d").date()
        end = datetime.strptime(date_end, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"日期格式不合法: {e}")
    
    if end <= start:
        raise ValueError("结束日期必须晚于开始日期")
    
    result = []
    
    # 自动发现所有带有data-dim属性的元素
    data_dim_elements = run_step(
        lambda: page.locator("[data-dim]").all(),
        "获取所有带有data-dim属性的元素",
        page_getter=lambda: page
    )
    
    # 遍历所有data-dim元素
    for element in data_dim_elements:
        try:
            # 获取data-dim属性值
            dim = run_step(
                lambda: element.get_attribute("data-dim"),
                "获取data-dim属性值",
                page_getter=lambda: page
            )
            if not dim:
                continue
            
            # 提取板块标题
            section_title = "未知板块"
            # 遍历容器内所有元素，找到第一个非空文本
            elements = run_step(
                lambda: element.locator("*").all(),
                "获取容器内所有元素",
                page_getter=lambda: page
            )
            for sub_element in elements:
                text = sub_element.inner_text().strip()
                if text:
                    section_title = text
                    break
            
            # VIP检测
            if is_vip_section(page, dim):
                continue
            
            if section_title == "未知板块":
                logger.warning(f"[模块] 板块 data-dim='{dim}' 未找到标题元素")
            
            # 提取表格数据
            table = run_step(
                lambda: element.locator("table"),
                "定位表格元素",
                page_getter=lambda: page
            )
            if run_step(
                lambda: table.count(),
                "获取表格数量",
                page_getter=lambda: page
            ) == 0:
                logger.warning(f"[模块] 板块 '{section_title}' 未找到表格，跳过")
                continue
            
            # 定位日期列
            date_col_indices = []
            date_col_names = []
            
            # 优先：从表头查找
            thead = run_step(
                lambda: table.locator("thead"),
                "定位表头元素",
                page_getter=lambda: page
            )
            if run_step(
                lambda: thead.count(),
                "获取表头数量",
                page_getter=lambda: page
            ) > 0:
                th_elements = run_step(
                    lambda: thead.locator("th").all(),
                    "获取表头列元素",
                    page_getter=lambda: page
                )
                for i, th in enumerate(th_elements):
                    th_text = th.inner_text().strip()
                    if "日期" in th_text or "时间" in th_text:
                        date_col_indices.append(i)
                        date_col_names.append(th_text)
            
            # 降级兜底：从第一行数据查找
            if not date_col_indices:
                tbody = run_step(
                    lambda: table.locator("tbody"),
                    "定位表体元素",
                    page_getter=lambda: page
                )
                if run_step(
                    lambda: tbody.count(),
                    "获取表体数量",
                    page_getter=lambda: page
                ) > 0:
                    first_row = run_step(
                        lambda: tbody.locator("tr").first,
                        "获取第一行数据",
                        page_getter=lambda: page
                    )
                    td_elements = run_step(
                        lambda: first_row.locator("td").all(),
                        "获取第一行列元素",
                        page_getter=lambda: page
                    )
                    for i, td in enumerate(td_elements):
                        td_text = td.inner_text().strip()
                        if re.match(r"\d{4}-\d{2}-\d{2}", td_text):
                            date_col_indices.append(i)
                            date_col_names.append(f"列{i+1}")
            
            if not date_col_indices:
                logger.warning(f"[模块] 板块 '{section_title}' 未找到日期列，跳过")
                continue
            
            # 输出多日期列检测日志
            if len(date_col_indices) > 1:
                logger.info(f"[模块] 板块 '{section_title}' 检测到多个日期列：{date_col_names}，将对所有日期列取并集筛选")
            
            # 提取表头字段名
            field_names = []
            if run_step(
                lambda: thead.count(),
                "获取表头数量",
                page_getter=lambda: page
            ) > 0:
                th_elements = run_step(
                    lambda: thead.locator("th").all(),
                    "获取表头列元素",
                    page_getter=lambda: page
                )
                for i, th in enumerate(th_elements):
                    th_text = th.inner_text().strip()
                    if th_text:
                        field_names.append(th_text)
                    else:
                        field_names.append(f"列{i+1}")
            else:
                # 没有表头，使用默认字段名
                tbody = run_step(
                    lambda: table.locator("tbody"),
                    "定位表体元素",
                    page_getter=lambda: page
                )
                if run_step(
                    lambda: tbody.count(),
                    "获取表体数量",
                    page_getter=lambda: page
                ) > 0:
                    first_row = run_step(
                        lambda: tbody.locator("tr").first,
                        "获取第一行数据",
                        page_getter=lambda: page
                    )
                    td_count = run_step(
                        lambda: first_row.locator("td").count(),
                        "获取第一行列数",
                        page_getter=lambda: page
                    )
                    for i in range(td_count):
                        field_names.append(f"列{i+1}")
            
            # 分页抓取数据
            collected_rows = []
            page_num = 1
            
            while len(collected_rows) < max_rows:
                # 提取当前页数据
                tbody = run_step(
                    lambda: table.locator("tbody"),
                    "定位表体元素",
                    page_getter=lambda: page
                )
                tr_elements = run_step(
                    lambda: tbody.locator("tr").all(),
                    "获取所有行元素",
                    page_getter=lambda: page
                )
                
                # 记录当前页的首行信息，用于检测页面是否更新
                first_row_info = None
                if tr_elements:
                    first_tds = run_step(
                        lambda: tr_elements[0].locator("td").all(),
                        "获取首行元素",
                        page_getter=lambda: page
                    )
                    if first_tds:
                        first_row_info = first_tds[0].inner_text().strip()
                
                # 处理当前页的行
                current_page_rows = []
                for tr in tr_elements:
                    td_elements = run_step(
                        lambda: tr.locator("td").all(),
                        "获取行内列元素",
                        page_getter=lambda: page
                    )
                    
                    # 提取该行所有列的文本
                    row_data = {}
                    for i, td in enumerate(td_elements):
                        text = td.inner_text().strip()
                        if i < len(field_names):
                            row_data[field_names[i]] = text
                        else:
                            row_data[f"列{i+1}"] = text
                    
                    # 检查是否有日期列在范围内
                    is_date_in_range = False
                    for i in date_col_indices:
                        if i >= len(td_elements):
                            continue
                        
                        # 解析日期
                        date_text = td_elements[i].inner_text().strip()
                        if not date_text or date_text == "-":
                            continue
                        
                        try:
                            row_date = datetime.strptime(date_text, "%Y-%m-%d").date()
                        except ValueError:
                            continue
                        
                        # 判断日期范围
                        if start <= row_date <= end:
                            is_date_in_range = True
                            break
                    
                    if is_date_in_range:
                        current_page_rows.append(row_data)
                
                # 添加当前页的行到收集列表
                collected_rows.extend(current_page_rows)
                
                # 检查是否达到最大行数
                if len(collected_rows) >= max_rows:
                    collected_rows = collected_rows[:max_rows]
                    logger.info(f"[模块] 板块 '{section_title}' 分页抓取完成，共抓取 {len(collected_rows)} 条数据")
                    break
                
                # 查找下一页按钮
                next_page_btn = None
                try:
                    # 尝试通过文本查找下一页按钮
                    next_page_btn = run_step(
                        lambda: element.locator("text=下一页"),
                        "查找下一页按钮",
                        page_getter=lambda: page
                    )
                except Exception:
                    pass
                
                if not next_page_btn or run_step(
                    lambda: next_page_btn.count(),
                    "获取下一页按钮数量",
                    page_getter=lambda: page
                ) == 0:
                    # 未找到下一页按钮，停止循环
                    logger.warning(f"[模块] 板块 '{section_title}' 未找到下一页按钮，仅抓取当前页数据")
                    break
                
                # 点击下一页按钮
                run_step(
                    lambda: next_page_btn.click(),
                    "点击下一页按钮",
                    page_getter=lambda: page
                )
                
                # 等待页面更新
                page_num += 1
                logger.info(f"[模块] 板块 '{section_title}' 翻页 {page_num} / 共未知，已抓取 {len(collected_rows)} 条数据")
                
                # 等待表格更新（通过首行信息变化判断）
                def is_table_updated():
                    new_tbody = table.locator("tbody")
                    new_trs = new_tbody.locator("tr").all()
                    if not new_trs:
                        return False
                    new_first_tds = new_trs[0].locator("td").all()
                    if not new_first_tds:
                        return False
                    new_first_row_info = new_first_tds[0].inner_text().strip()
                    return new_first_row_info != first_row_info
                
                # 使用run_step等待表格更新
                try:
                    run_step(
                        lambda: page.wait_for_function(is_table_updated, timeout=10000),
                        "等待表格更新",
                        page_getter=lambda: page
                    )
                except Exception as e:
                    logger.warning(f"[模块] 等待表格更新超时: {e}，继续抓取")
            
            # 处理结果
            if collected_rows:
                logger.info(f"[模块] 板块 '{section_title}' 共找到 {len(collected_rows)} 行符合要求的数据")
                result.append({
                    "section": section_title,
                    "dim": dim,
                    "rows": collected_rows
                })
            else:
                logger.info(f"[模块] 板块 '{section_title}' 找到日期列，但无符合 {date_start} ~ {date_end} 范围的行")
                
        except Exception as e:
            logger.error(f"[模块] 处理板块 data-dim='{dim}' 时出错: {e}")
            continue
    
    logger.info(f"[模块] 提取完成，共 {len(result)} 个板块有数据")
    return result
