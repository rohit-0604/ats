"""ATS v8 — Cerebras provider (OpenAI-compatible SDK, 1M tokens/day)"""
import logging
from typing import Optional
from openai import OpenAI
from app.config import CEREBRAS_API_KEY, CEREBRAS_BASE_URL, PROVIDER_TIMEOUT

log = logging.getLogger(__name__)
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=CEREBRAS_API_KEY,
            base_url=CEREBRAS_BASE_URL,
            timeout=PROVIDER_TIMEOUT,
        )
    return _client


def call(
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    response_format: Optional[dict] = None,
) -> str:
    kwargs: dict = dict(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if response_format:
        kwargs["response_format"] = response_format

    resp = _get_client().chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or ""
    log.debug(f"Cerebras/{model}: {len(content)} chars")
    return content
