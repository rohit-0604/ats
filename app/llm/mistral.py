"""ATS v8 — Mistral provider (OpenAI-compatible SDK, 1B tokens/month)"""
import logging
from typing import Optional
from openai import OpenAI
from app.config import MISTRAL_API_KEY, MISTRAL_BASE_URL, PROVIDER_TIMEOUT

log = logging.getLogger(__name__)
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=MISTRAL_API_KEY,
            base_url=MISTRAL_BASE_URL,
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
    # Mistral uses a different response_format key
    if response_format:
        kwargs["response_format"] = response_format

    resp = _get_client().chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or ""
    log.debug(f"Mistral/{model}: {len(content)} chars")
    return content
