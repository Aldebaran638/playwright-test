import random
import time
from pathlib import Path

from playwright.sync_api import Playwright, TimeoutError, sync_playwright

from modules.expert_analysis import open_expert_analysis_from_home
from modules.expert_card_opener import open_target_card_detail
from modules.expert_card_reader import collect_visible_expert_cards
from modules.expert_download import download_pdf_from_detail_page
from modules.expert_matcher import match_cards_with_user_intent
from modules.expert_result_loader import click_load_more, scroll_page_to_bottom
from modules.expert_tags import apply_expert_analysis_tag_filters
from modules.expert_target_card import wait_for_target_card_image
from modules.login import PASSWORD, USERNAME, do_login, is_logged_in

EDGE_EXECUTABLE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\146.0.3856.78\msedge.exe")
EDGE_USER_DATA_DIR = Path(r"C:\Users\winkey\AppData\Local\Microsoft\Edge\User Data2")
EDGE_PROFILE_DIRECTORY = "Default"
USER_INTENT = "请根据文章标题筛选符合用户需求、值得下载的文章。用户只对每一页的前三个文章感兴趣。请只从当前传入的新增标题中筛选。"
MAX_LOAD_MORE_CLICKS = 1
FAKE_DETAIL_OPEN_ENABLED = True
FAKE_DETAIL_OPEN_COUNT_RANGE = (0, 2)
ALLOW_DETAIL_SCROLL = True


def get_new_cards(visible_cards: list[dict], seen_titles: set[str]) -> list[dict]:
    # 只保留当前这一轮第一次出现的新卡片，避免重复评估旧结果
    new_cards = []
    current_batch_titles = set()

    for card in visible_cards:
        title = str(card.get("title", "")).strip()
        if not title:
            continue
        if title in seen_titles or title in current_batch_titles:
            continue

        new_cards.append(card)
        current_batch_titles.add(title)

    return new_cards


def observe_after_article_download(min_sec=6, max_sec=12):
    # 下载完一篇文章后，多停留一会儿，避免立刻连续处理下一篇
    wait_seconds = random.uniform(min_sec, max_sec)
    print(f"observe after download for {wait_seconds:.2f}s")
    time.sleep(wait_seconds)


def observe_between_load_more_rounds(min_sec=8, max_sec=15):
    # 每轮加载更多之间增加更长的观察时间，避免节奏过紧
    wait_seconds = random.uniform(min_sec, max_sec)
    print(f"observe before next load more for {wait_seconds:.2f}s")
    time.sleep(wait_seconds)


def build_detail_action_queue(
    cards_to_match: list[dict],
    matched_titles: list[str],
    downloaded_titles: set[str],
) -> list[dict]:
    # 将真实下载文章与随机伪装浏览文章混合成统一的详情处理队列
    available_titles = []
    seen_batch_titles = set()
    for card in cards_to_match:
        title = str(card.get("title", "")).strip()
        if not title:
            continue
        if title in seen_batch_titles:
            continue
        available_titles.append(title)
        seen_batch_titles.add(title)

    normalized_matched_titles = []
    seen_matched_titles = set()
    for title in matched_titles:
        normalized_title = str(title).strip()
        if not normalized_title:
            continue
        if normalized_title not in seen_batch_titles:
            continue
        if normalized_title in seen_matched_titles:
            continue
        if normalized_title in downloaded_titles:
            continue
        normalized_matched_titles.append(normalized_title)
        seen_matched_titles.add(normalized_title)

    detail_action_queue = [
        {
            "title": title,
            "should_download": True,
            "allow_detail_scroll": ALLOW_DETAIL_SCROLL,
        }
        for title in normalized_matched_titles
    ]

    if FAKE_DETAIL_OPEN_ENABLED:
        fake_candidates = [
            title
            for title in available_titles
            if title not in seen_matched_titles and title not in downloaded_titles
        ]
        fake_count = min(
            len(fake_candidates),
            random.randint(*FAKE_DETAIL_OPEN_COUNT_RANGE),
        )
        fake_titles = random.sample(fake_candidates, fake_count) if fake_count > 0 else []

        for title in fake_titles:
            detail_action_queue.append(
                {
                    "title": title,
                    "should_download": False,
                    "allow_detail_scroll": ALLOW_DETAIL_SCROLL,
                }
            )

    random.shuffle(detail_action_queue)
    print(f"detail action queue: {detail_action_queue}")
    return detail_action_queue


def process_detail_action_queue(page, detail_action_queue: list[dict], downloaded_titles: set[str]) -> int:
    # 按混合队列逐个打开详情页，决定是真下载还是仅停留浏览
    downloaded_count = 0

    for task in detail_action_queue:
        title = str(task.get("title", "")).strip()
        should_download = bool(task.get("should_download", False))
        allow_detail_scroll = bool(task.get("allow_detail_scroll", False))

        if not title:
            continue
        if should_download and title in downloaded_titles:
            print(f"skip already downloaded title: {title}")
            continue

        action_label = "download" if should_download else "browse_only"
        print(f"processing detail action: {action_label}, title: {title}")
        target_card = wait_for_target_card_image(page, title)
        detail_page = open_target_card_detail(page, target_card)

        try:
            action_success = download_pdf_from_detail_page(
                detail_page,
                title,
                should_download=should_download,
                allow_detail_scroll=allow_detail_scroll,
            )
            if not action_success:
                print(f"skip current article after failed detail action: {title}")
                continue

            if should_download:
                downloaded_titles.add(title)
                downloaded_count += 1
                observe_after_article_download()
        finally:
            detail_page.close()

    return downloaded_count


def process_card_batch(page, cards_to_match: list[dict], downloaded_titles: set[str]) -> int:
    # 对一批待判断标题执行模型筛选，并处理真实下载与伪装浏览队列
    if not cards_to_match:
        print("no cards to evaluate in current batch")
        return 0

    card_match_result = match_cards_with_user_intent(USER_INTENT, cards_to_match)
    matched_titles = card_match_result.get("matched_titles", [])
    print(f"matched titles in current batch: {matched_titles}")
    print(f"match reason: {card_match_result.get('reason', '')}")

    detail_action_queue = build_detail_action_queue(
        cards_to_match,
        matched_titles,
        downloaded_titles,
    )
    return process_detail_action_queue(page, detail_action_queue, downloaded_titles)


def run(playwright: Playwright) -> None:
    # 直接使用本机已安装的 Edge 和现有用户数据目录，避免创建新的浏览器环境
    if not EDGE_EXECUTABLE_PATH.exists():
        raise FileNotFoundError(f"missing Edge executable: {EDGE_EXECUTABLE_PATH}")
    if not EDGE_USER_DATA_DIR.exists():
        raise FileNotFoundError(f"missing Edge user data dir: {EDGE_USER_DATA_DIR}")

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(EDGE_USER_DATA_DIR),
        executable_path=str(EDGE_EXECUTABLE_PATH),
        headless=False,
        slow_mo=100,
        args=[f"--profile-directory={EDGE_PROFILE_DIRECTORY}"],
    )

    # 复用已打开页面，没有时再创建新页面
    page = context.pages[0] if context.pages else context.new_page()

    try:
        # 直接基于 Edge 现有用户环境检查登录状态，未登录时再走原登录流程
        if not is_logged_in(page):
            print("edge profile is not logged in, starting login flow...")
            do_login(page)
        else:
            print("already logged in in existing Edge profile")

        # 进入“专家分析”页面
        open_expert_analysis_from_home(page)

        # 选择标签，缩小结果范围
        apply_expert_analysis_tag_filters(page)

        # 先读取初始页标题，首轮就对当前已经出现的卡片做一次判断
        initial_visible_cards = collect_visible_expert_cards(page)
        seen_titles = set()
        # 记录已经下载过的标题，避免重复下载
        downloaded_titles = set()
        total_downloaded = 0

        print(f"initial cards found: {len(initial_visible_cards)}")
        total_downloaded += process_card_batch(page, initial_visible_cards, downloaded_titles)
        seen_titles.update(
            str(card.get("title", "")).strip()
            for card in initial_visible_cards
            if str(card.get("title", "")).strip()
        )

        for search_round in range(MAX_LOAD_MORE_CLICKS):
            print(f"starting load-more search round: {search_round + 1}")

            # 在每轮加载更多前先观察一段时间，避免轮次之间切换过快
            observe_between_load_more_rounds()

            # 每一轮都先滚到底部并点击一次“加载更多”，再处理这次新增的结果
            reached_bottom = scroll_page_to_bottom(page)
            if not reached_bottom:
                raise RuntimeError("failed to scroll near the bottom of the page")

            click_load_more(page)

            # 读取当前页所有已出现的卡片，再过滤出本次加载更多新增的标题
            visible_cards = collect_visible_expert_cards(page)
            new_cards = get_new_cards(visible_cards, seen_titles)
            print(f"new cards found after load more: {len(new_cards)}")

            # 当前轮没有新增标题时，说明后续继续查找意义不大，直接结束流程
            if not new_cards:
                print("no new cards found in current round, stopping search")
                break

            # 先把本轮新增标题记入已评估集合，避免下一轮重复送给模型
            seen_titles.update(card["title"].strip() for card in new_cards)

            # 处理本轮新增结果里的真实下载和伪装浏览任务
            total_downloaded += process_card_batch(page, new_cards, downloaded_titles)

        print(f"main2 flow complete, total downloaded articles: {total_downloaded}")
        # 保留浏览器一段时间，方便人工确认结果
        time.sleep(10)

    except TimeoutError as e:
        print(f"page timeout: {e}")
    except Exception as e:
        print(f"execution failed: {e}")
    finally:
        context.close()


if __name__ == "__main__":
    # 启动前先确认 keyring 中已经保存 Mintel 账号密码
    if not USERNAME or not PASSWORD:
        raise ValueError("please save mintel username/password in keyring first")

    with sync_playwright() as playwright:
        run(playwright)
