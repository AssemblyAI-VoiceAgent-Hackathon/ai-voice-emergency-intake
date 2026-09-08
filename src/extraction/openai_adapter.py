"""OpenAI-compatible ModelAdapter for extract_structured_case.

The engine (src/extraction/engine.py) already builds the full provider-neutral
prompt: it embeds OUTPUT_SCHEMA (the structured-case JSON Schema) and
SOURCE_DATA (the sanitized transcript) as delimited text and asks for exactly
one JSON object back. This module's only job is to hand that prompt to a
chat-completions model and return the parsed JSON object. All safety, identity
and schema enforcement still happens in the engine after this returns.

Works with OpenAI directly, or with any OpenAI-compatible gateway (e.g.
OpenRouter) by pointing ARIA_EXTRACTION_BASE_URL / ARIA_EXTRACTION_API_KEY at
it. Defaults to OpenRouter + DeepSeek (cheap, strong at structured extraction)
when OPENROUTER_API_KEY is set and no explicit OpenAI key is configured.
"""

from __future__ import annotations

import json
import os
from typing import Any

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENROUTER_MODEL = "deepseek/deepseek-chat"


class OpenAIAdapterError(RuntimeError):
    """Raised when the provider call fails or returns non-JSON content."""


def _resolve_credentials() -> tuple[str, str | None, str]:
    """Returns (api_key, base_url, default_model)."""

    api_key = os.environ.get("ARIA_EXTRACTION_API_KEY")
    base_url = os.environ.get("ARIA_EXTRACTION_BASE_URL")
    if api_key:
        return api_key, base_url, DEFAULT_OPENAI_MODEL

    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        return openrouter_key, base_url or "https://openrouter.ai/api/v1", DEFAULT_OPENROUTER_MODEL

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        return openai_key, base_url, DEFAULT_OPENAI_MODEL

    raise OpenAIAdapterError(
        "No extraction API key set. Set OPENROUTER_API_KEY (DeepSeek) or OPENAI_API_KEY."
    )


def _client():
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - import guard
        raise OpenAIAdapterError(
            "The 'openai' package is not installed. Add it to requirements and pip install."
        ) from exc

    api_key, base_url, default_model = _resolve_credentials()
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    return client, default_model


def openai_generate(prompt: str) -> dict[str, Any]:
    """ModelAdapter: send the engine-built prompt to the configured model and return JSON.

    Uses JSON mode so the model is constrained to emit a single JSON object,
    matching what extract_structured_case expects back from `generate`.
    """

    client, default_model = _client()
    model = os.environ.get("ARIA_EXTRACTION_OPENAI_MODEL", default_model)
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict data-extraction engine. Follow the caller's "
                        "instructions exactly and return only the JSON object requested. "
                        "Never add commentary, markdown, or extra keys."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as exc:  # noqa: BLE001 - surfaced as GENERATOR_FAILURE by the engine
        raise OpenAIAdapterError(f"OpenAI request failed: {exc}") from exc

    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise OpenAIAdapterError("OpenAI returned an empty response.")
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenAIAdapterError("OpenAI did not return valid JSON.") from exc
