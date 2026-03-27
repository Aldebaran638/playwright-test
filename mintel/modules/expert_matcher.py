import json
from typing import Any

from modules.llm_config import DEEPSEEK_BASE_URL, get_deepseek_api_key, get_deepseek_model

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


def _build_client():
    # 按 DeepSeek 官方推荐方式，使用 OpenAI 兼容 SDK 创建客户端
    if OpenAI is None:
        raise ImportError("please install the openai package first")

    api_key = get_deepseek_api_key()
    if not api_key:
        raise ValueError("please save deepseek api_key in keyring first")

    return OpenAI(
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL,
    )


def _call_deepseek_json(system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    # 调用 DeepSeek Chat Completions 接口，并要求返回 JSON 结果
    client = _build_client()
    model = get_deepseek_model()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
            },
        ],
        response_format={"type": "json_object"},
        stream=False,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("deepseek returned an empty response")

    return json.loads(content)


def match_card_with_user_intent(user_intent: str, card_data: dict) -> dict:
    # 调用 DeepSeek 对当前卡片标题列表做初筛，并选出最值得打开的一篇标题
    system_prompt = (
        "你是一个文章卡片筛选助手。"
        "请仅根据文章标题判断当前候选卡片列表中是否存在符合用户意图的文章。"
        "如果存在，请返回最值得打开的一篇标题。"
        "如果不存在，请明确返回没有候选。"
        "你必须返回 JSON。"
        "JSON 字段必须包含: found_candidate, best_title, reason。"
    )

    payload = {
        "task": "card_match",
        "user_intent": user_intent,
        "card_data": card_data,
        "expected_json_schema": {
            "found_candidate": True,
            "best_title": "string",
            "reason": "string",
        },
    }

    result = _call_deepseek_json(system_prompt, payload)
    result.setdefault("found_candidate", False)
    result.setdefault("best_title", "")
    result.setdefault("reason", "")
    return result


def match_cards_with_user_intent(user_intent: str, visible_cards: list[dict]) -> dict:
    # 让模型从当前这一批新增标题里挑出所有符合用户意图的文章标题
    system_prompt = (
        "你是一个文章标题筛选助手。"
        "你只能根据当前传入的文章标题列表做判断。"
        "如果某个标题符合用户意图，就把这个标题原样放进 matched_titles。"
        "如果没有任何符合项，就返回空列表。"
        "你绝不能改写标题，不能返回页面上不存在的标题。"
        "你必须返回 JSON。"
        "JSON 字段必须包含: matched_titles, reason。"
    )

    payload = {
        "task": "card_batch_match",
        "user_intent": user_intent,
        "visible_cards": visible_cards,
        "expected_json_schema": {
            "matched_titles": ["string"],
            "reason": "string",
        },
    }

    result = _call_deepseek_json(system_prompt, payload)
    raw_titles = result.get("matched_titles", [])
    if not isinstance(raw_titles, list):
        raw_titles = []

    # 只保留当前批次里真实存在的标题，避免模型返回页面中不存在的内容
    available_titles = {
        card.get("title", "").strip(): card.get("title", "").strip()
        for card in visible_cards
        if card.get("title", "").strip()
    }

    matched_titles = []
    seen_titles = set()
    for title in raw_titles:
        normalized_title = str(title).strip()
        if not normalized_title:
            continue
        if normalized_title not in available_titles:
            continue
        if normalized_title in seen_titles:
            continue
        matched_titles.append(available_titles[normalized_title])
        seen_titles.add(normalized_title)

    return {
        "matched_titles": matched_titles,
        "reason": str(result.get("reason", "")).strip(),
    }
