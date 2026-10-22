"""ATS v8 — OpenRouter provider (OpenAI-compatible SDK, :free model access)"""
import logging
from typing import Optional
from openai import OpenAI
from app.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, PROVIDER_TIMEOUT

log = logging.getLogger(__name__)
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            timeout=PROVIDER_TIMEOUT,
            default_headers={
                "HTTP-Referer": "https://github.com/ats-v8",
                "X-Title": "ATS-v8",
            },
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

    # DeepSeek R1 returns thinking tokens in <think> blocks — strip them
    if "<think>" in content:
        import re
        # Log reasoning for planner analysis before stripping
        think_match = re.search(r"<think>(.*?)</think>", content, re.DOTALL)
        if think_match:
            log.debug(f"R1 reasoning ({len(think_match.group(1))} chars): [logged]")
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    log.debug(f"OpenRouter/{model} response: {len(content)} chars")
    return content
