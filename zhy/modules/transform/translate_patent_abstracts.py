from __future__ import annotations

import asyncio
import copy
import re
from pathlib import Path

from loguru import logger

from zhy.modules.common.openai_compatible_client import create_chat_completion_text
from zhy.modules.common.types.translation import PatentAbstractTranslationConfig
from zhy.modules.persist.json_io import load_json_file_any_utf, save_json
from zhy.modules.persist.page_path import build_enrichment_page_path, iter_input_page_files


def detect_text_language(value: str) -> str:
    text = str(value or "")
    if not text.strip():
        return ""
    has_hiragana = bool(re.search(r"[\u3040-\u309f]", text))
    has_katakana = bool(re.search(r"[\u30a0-\u30ff\u31f0-\u31ff]", text))
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", text))
    has_latin = bool(re.search(r"[A-Za-z]", text))
    if has_hiragana or has_katakana:
        return "ja"
    if has_cjk and not has_latin:
        return "zh"
    if has_latin and not has_cjk:
        return "en"
    if has_cjk and has_latin:
        return "mixed"
    return "other"


def should_translate_abstract(text: str) -> bool:
    language = detect_text_language(text)
    return bool(text.strip()) and language not in {"", "zh", "mixed"}


def build_translation_system_prompt(target_language: str) -> str:
    return (
        "你是专利摘要翻译助手。"
        f"请把用户提供的专利摘要准确翻译成{target_language}。"
        "只输出译文，不要解释，不要加标题，不要补充原文中没有的信息。"
    )


def normalize_translation_text(text: str) -> str:
    return " ".join(str(text or "").replace("\r", " ").split())


async def translate_abstract_text(text: str, config: PatentAbstractTranslationConfig) -> str:
    if config.client is None:
        raise ValueError("translation client config is missing")
    system_prompt = build_translation_system_prompt(config.target_language)
    user_prompt = f"请翻译下面这段专利摘要：\n\n{text}"
    translated = await asyncio.to_thread(
        create_chat_completion_text,
        config=config.client,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.0,
    )
    normalized = normalize_translation_text(translated)
    if not normalized:
        raise ValueError("translation result is empty")
    return normalized


async def translate_supplement_payload(payload: dict, config: PatentAbstractTranslationConfig) -> dict:
    translated_payload = copy.deepcopy(payload) if isinstance(payload, dict) else {}
    records = translated_payload.get("records")
    if not isinstance(records, list):
        raise ValueError("records is not a list")

    semaphore = asyncio.Semaphore(max(int(config.request_concurrency), 1))

    async def process_record(record: object) -> None:
        if not isinstance(record, dict):
            return
        original_text = str(record.get("ABST") or "").strip()
        record["ABST_ORIGINAL"] = original_text
        record["ABST_LANGUAGE"] = detect_text_language(original_text)
        record["ABST_TRANSLATED"] = False
        if not should_translate_abstract(original_text):
            return
        async with semaphore:
            translated_text = await translate_abstract_text(original_text, config)
        record["ABST"] = translated_text
        record["ABST_TRANSLATED"] = True

    await asyncio.gather(*(process_record(record) for record in records))
    translated_payload["translation_enabled"] = True
    translated_payload["translation_target_language"] = config.target_language
    return translated_payload


async def run_translate_patent_abstracts(config: PatentAbstractTranslationConfig) -> Path:
    if not config.enabled:
        raise ValueError("translation step is disabled")
    if config.client is None:
        raise ValueError("translation client config is missing")
    if not config.input_root.exists():
        raise FileNotFoundError(f"translation input root not found: {config.input_root}")

    page_files = iter_input_page_files(config.input_root)
    summary = {
        "input_root": str(config.input_root),
        "output_root": str(config.output_root),
        "total_page_files": len(page_files),
        "pages_written": 0,
        "pages_skipped": 0,
        "pages_failed": 0,
        "files": [],
    }
    summary_path = config.output_root / "run_summary.json"
    save_json(summary_path, summary)

    for page_file in page_files:
        output_path = build_enrichment_page_path(config.output_root, config.input_root, page_file)
        if config.resume and output_path.exists():
            summary["pages_skipped"] += 1
            summary["files"].append({"input_file": str(page_file), "output_file": str(output_path), "status": "skipped"})
            save_json(summary_path, summary)
            continue

        try:
            payload = load_json_file_any_utf(page_file)
            translated_payload = await translate_supplement_payload(payload, config)
            save_json(output_path, translated_payload)
            summary["pages_written"] += 1
            translated_count = 0
            records = translated_payload.get("records")
            if isinstance(records, list):
                translated_count = sum(1 for record in records if isinstance(record, dict) and record.get("ABST_TRANSLATED"))
            summary["files"].append(
                {
                    "input_file": str(page_file),
                    "output_file": str(output_path),
                    "status": "ok",
                    "translated_record_count": translated_count,
                }
            )
        except Exception as exc:
            logger.exception("[translate_patent_abstracts] page failed: {}", page_file)
            summary["pages_failed"] += 1
            summary["files"].append(
                {
                    "input_file": str(page_file),
                    "output_file": str(output_path),
                    "status": "error",
                    "error": str(exc),
                }
            )

        save_json(summary_path, summary)

    save_json(summary_path, summary)
    return summary_path
