"""
ATS v8 — LLM Router
Routes LLM calls by task tier. Handles fallback chain, retries, and rate-limit switching.
All providers use OpenAI-compatible SDK (different base_url) except Gemini.
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Optional, Any
from enum import IntEnum

from app.config import (
    Models, MAX_RETRIES, RETRY_BASE_DELAY, PROVIDER_TIMEOUT,
    GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY,
    CEREBRAS_API_KEY, MISTRAL_API_KEY,
    DEFAULT_TEMPERATURE, PLANNING_TEMPERATURE,
)

log = logging.getLogger(__name__)


class Tier(IntEnum):
    CLASSIFICATION  = 1   # fast 8B: domain inference, validation, lessons
    EXTRACTION      = 2   # long-context: Gemini 2.5 Flash (1M ctx)
    CODEGEN         = 3   # code: Kimi K2 on Groq
    REASONING       = 4   # planning: DeepSeek R1 on OpenRouter
    EMBEDDING       = 5   # local: all-MiniLM-L6-v2
    LESSONS         = 6   # same as Tier 1


# Provider availability flags (set False after repeated failures in a session)
_provider_available: dict[str, bool] = {
    "groq":       bool(GROQ_API_KEY),
    "gemini":     bool(GEMINI_API_KEY),
    "openrouter": bool(OPENROUTER_API_KEY),
    "cerebras":   bool(CEREBRAS_API_KEY),
    "mistral":    bool(MISTRAL_API_KEY),
}

# Consecutive failure counter per provider (reset on success)
_failure_counts: dict[str, int] = {k: 0 for k in _provider_available}
_MAX_CONSECUTIVE_FAILURES = 3


def _mark_failure(provider: str) -> None:
    _failure_counts[provider] += 1
    if _failure_counts[provider] >= _MAX_CONSECUTIVE_FAILURES:
        log.warning(f"Router: {provider} marked unavailable after {_MAX_CONSECUTIVE_FAILURES} failures")
        _provider_available[provider] = False


def _mark_success(provider: str) -> None:
    _failure_counts[provider] = 0
    _provider_available[provider] = True


def _available(provider: str) -> bool:
    return _provider_available.get(provider, False)


# ─── Fallback chains per tier ─────────────────────────────────────────────────

def _tier1_chain() -> list[tuple[str, str]]:
    """(provider, model_id) in fallback order."""
    chain = []
    if _available("groq"):
        chain.append(("groq", Models.TIER1_PRIMARY))
    if _available("cerebras"):
        chain.append(("cerebras", Models.TIER1_FB1))
    if _available("mistral"):
        chain.append(("mistral", Models.TIER1_FB2))
    return chain


def _tier2_chain() -> list[tuple[str, str]]:
    chain = []
    if _available("gemini"):
        chain.append(("gemini", Models.TIER2_PRIMARY))
        chain.append(("gemini", Models.TIER2_FB1))
    if _available("groq"):
        chain.append(("groq", Models.TIER2_FB2))   # chunked fallback
    return chain


def _tier3_chain() -> list[tuple[str, str]]:
    chain = []
    if _available("groq"):
        chain.append(("groq", Models.TIER3_PRIMARY))    # kimi-k2
    if _available("mistral"):
        chain.append(("mistral", Models.TIER3_FB1))     # codestral
    if _available("groq"):
        chain.append(("groq", Models.TIER3_FB2))        # llama-3.3-70b
    if _available("openrouter"):
        chain.append(("openrouter", Models.TIER3_FB3))  # deepseek-v3-2 (paid)
    return chain


def _tier4_chain() -> list[tuple[str, str]]:
    chain = []
    if _available("groq"):
        chain.append(("groq", Models.TIER4_PRIMARY))    # qwq-32b
        chain.append(("groq", Models.TIER4_FB1))        # llama-3.3-70b
    if _available("openrouter"):
        chain.append(("openrouter", Models.TIER4_FB2))  # deepseek-v3-2 (paid)
    return chain


def _tier6_chain() -> list[tuple[str, str]]:
    return _tier1_chain()


_TIER_CHAINS = {
    Tier.CLASSIFICATION: _tier1_chain,
    Tier.EXTRACTION:     _tier2_chain,
    Tier.CODEGEN:        _tier3_chain,
    Tier.REASONING:      _tier4_chain,
    Tier.LESSONS:        _tier6_chain,
}


# ─── Provider call dispatcher ─────────────────────────────────────────────────

def _call_provider(
    provider: str,
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    response_format: Optional[dict] = None,
) -> str:
    """Synchronous call to a single provider. Raises on failure."""
    if provider == "groq":
        from app.llm.groq import call as groq_call
        return groq_call(model, messages, temperature, max_tokens, response_format)
    elif provider == "gemini":
        from app.llm.gemini import call as gemini_call
        return gemini_call(model, messages, temperature, max_tokens)
    elif provider == "openrouter":
        from app.llm.openrouter import call as or_call
        return or_call(model, messages, temperature, max_tokens, response_format)
    elif provider == "cerebras":
        from app.llm.cerebras import call as cb_call
        return cb_call(model, messages, temperature, max_tokens, response_format)
    elif provider == "mistral":
        from app.llm.mistral import call as ms_call
        return ms_call(model, messages, temperature, max_tokens, response_format)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def complete(
    tier: Tier,
    messages: list[dict],
    max_tokens: int = 2048,
    temperature: Optional[float] = None,
    response_format: Optional[dict] = None,
    label: str = "",            # descriptive label for logging
) -> str:
    """
    Main router entry point. Synchronous.
    Tries each (provider, model) in the tier's fallback chain.
    Retries with exponential backoff on 429. Falls through on other errors.
    Returns the text content of the first successful response.
    Raises RuntimeError if all providers fail.
    """
    if temperature is None:
        temperature = PLANNING_TEMPERATURE if tier == Tier.REASONING else DEFAULT_TEMPERATURE

    chain = _TIER_CHAINS[tier]()
    if not chain:
        raise RuntimeError(f"No available providers for Tier {tier}. Check API keys in .env")

    last_error: Optional[Exception] = None

    for provider, model in chain:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                log.debug(f"Router [{label}] Tier{tier} → {provider}/{model} attempt {attempt}")
                result = _call_provider(
                    provider, model, messages, temperature, max_tokens, response_format
                )
                _mark_success(provider)
                log.debug(f"Router [{label}] ✓ {provider}/{model} ({len(result)} chars)")
                return result

            except Exception as e:
                err_str = str(e).lower()
                last_error = e

                if "429" in err_str or "rate limit" in err_str or "quota" in err_str:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    log.warning(
                        f"Router [{label}] {provider}/{model} rate-limited. "
                        f"Retry {attempt}/{MAX_RETRIES} in {delay:.1f}s"
                    )
                    time.sleep(delay)
                    if attempt == MAX_RETRIES:
                        _mark_failure(provider)
                        log.warning(f"Router [{label}] Falling through from {provider}")
                        break  # try next in chain

                elif "401" in err_str or "authentication" in err_str:
                    log.error(f"Router [{label}] {provider} auth error — check API key. Skipping provider.")
                    _mark_failure(provider)
                    break  # auth errors don't retry

                elif "404" in err_str or "not found" in err_str:
                    log.error(f"Router [{label}] Model {model} not found on {provider}. Skipping.")
                    break

                else:
                    delay = RETRY_BASE_DELAY * attempt
                    log.warning(f"Router [{label}] {provider} error: {e}. Retry {attempt}/{MAX_RETRIES}")
                    time.sleep(delay)
                    if attempt == MAX_RETRIES:
                        _mark_failure(provider)
                        break

    raise RuntimeError(
        f"All providers failed for Tier {tier} [{label}]. Last error: {last_error}"
    )


async def complete_async(
    tier: Tier,
    messages: list[dict],
    max_tokens: int = 2048,
    temperature: Optional[float] = None,
    response_format: Optional[dict] = None,
    label: str = "",
) -> str:
    """Async wrapper — runs complete() in a thread pool to avoid blocking event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: complete(tier, messages, max_tokens, temperature, response_format, label)
    )


def embed(texts: list[str]) -> list[list[float]]:
    """Local embedding via sentence-transformers. No API call, no rate limits."""
    from app.llm.huggingface import embed as hf_embed
    return hf_embed(texts)


def provider_status() -> dict[str, bool]:
    """Returns current availability of all providers."""
    return dict(_provider_available)


def reset_provider(provider: str) -> None:
    """Manually re-enable a provider (e.g. after daily limit resets)."""
    _failure_counts[provider] = 0
    _provider_available[provider] = bool({
        "groq": GROQ_API_KEY,
        "gemini": GEMINI_API_KEY,
        "openrouter": OPENROUTER_API_KEY,
        "cerebras": CEREBRAS_API_KEY,
        "mistral": MISTRAL_API_KEY,
    }.get(provider, ""))
    log.info(f"Router: {provider} manually reset")
