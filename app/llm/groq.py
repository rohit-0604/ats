"""ATS v8 — Groq provider (OpenAI-compatible SDK)"""
import logging
from typing import Optional
from openai import OpenAI
from app.config import GROQ_API_KEY, GROQ_BASE_URL, PROVIDER_TIMEOUT

log = logging.getLogger(__name__)
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url=GROQ_BASE_URL,
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
    log.debug(
        f"Groq/{model} usage: "
        f"in={resp.usage.prompt_tokens} out={resp.usage.completion_tokens}"
    )
    return content
