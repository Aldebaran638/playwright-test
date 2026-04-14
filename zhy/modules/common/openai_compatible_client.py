from __future__ import annotations

import time
from urllib.parse import urljoin

import requests

from zhy.modules.common.types.translation import OpenAICompatibleClientConfig


def _build_chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/") + "/"
    return urljoin(normalized, "chat/completions")


def _extract_message_text(payload: dict) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("chat completion response missing choices")

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ValueError("chat completion response missing message")

    content = message.get("content")
    if isinstance(content, str):
        text = content.strip()
        if text:
            return text

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if text:
                parts.append(text)
        joined = "\n".join(parts).strip()
        if joined:
            return joined

    raise ValueError("chat completion response content is empty")


def create_chat_completion_text(
    *,
    config: OpenAICompatibleClientConfig,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
) -> str:
    url = _build_chat_completions_url(config.base_url)
    headers = {
        "authorization": f"Bearer {config.api_key}",
        "content-type": "application/json",
    }
    body = {
        "model": config.model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    attempts = max(config.retry_count, 1)
    last_error: Exception | None = None
    for attempt_index in range(attempts):
        try:
            response = requests.post(url, headers=headers, json=body, timeout=config.timeout_seconds)
            if response.status_code == 429 or 500 <= response.status_code < 600:
                raise requests.HTTPError(f"transient status code: {response.status_code}", response=response)
            response.raise_for_status()
            return _extract_message_text(response.json())
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError) as exc:
            last_error = exc
            if attempt_index >= attempts - 1:
                break
            time.sleep(config.retry_backoff_base_seconds * (2 ** attempt_index))

    raise RuntimeError(f"openai compatible request failed: {last_error}")
