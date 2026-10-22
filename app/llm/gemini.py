"""
ATS v8 — Gemini provider
Uses google-genai SDK (replaces deprecated google-generativeai).
Handles 1M context window for requirement extraction.

IMPORTANT: gemini-2.0-flash RETIRED March 3 2026.
Current models: gemini-2.5-flash (primary), gemini-2.5-flash-lite (fallback)
RPD limits are community-reported (not confirmed from official docs table):
  gemini-2.5-flash:      ~10 RPM, ~500 RPD
  gemini-2.5-flash-lite: ~15 RPM, ~1000 RPD
Verify at: https://ai.google.dev/gemini-api/docs/rate-limits
"""

from __future__ import annotations
import logging
from typing import Optional

from app.config import GEMINI_API_KEY, PROVIDER_TIMEOUT

log = logging.getLogger(__name__)
_client = None


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def call(
    model: str,
    messages: list[dict],
    temperature: float,
    max_tokens: int,
) -> str:
    """
    Convert OpenAI-format messages to Gemini format and call.
    System message is passed as system_instruction.
    """
    from google import genai
    from google.genai import types

    client = _get_client()

    # Extract system prompt
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    user_parts   = [m for m in messages if m["role"] != "system"]

    system_instruction = "\n\n".join(system_parts) if system_parts else None

    # Convert to Gemini Content objects
    contents = []
    for m in user_parts:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(
            role=role,
            parts=[types.Part(text=m["content"])],
        ))

    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        system_instruction=system_instruction,
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )

    text = response.text or ""
    log.debug(f"Gemini/{model} response: {len(text)} chars")
    return text
