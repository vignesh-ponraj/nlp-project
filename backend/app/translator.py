"""LLM-based translation via OpenAI or Anthropic (Claude) — uses your existing API subscriptions."""

import json
import re
from typing import Optional

import httpx

from app.config import Settings


class TranslationError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


# ISO-style codes used by the UI → English name for clearer model instructions
_LANG_LABELS: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "zh-hans": "Chinese (Simplified)",
    "zh-hant": "Chinese (Traditional)",
    "ar": "Arabic",
    "hi": "Hindi",
    "ru": "Russian",
    "nl": "Dutch",
    "pl": "Polish",
    "sv": "Swedish",
}


def _lang_label(code: str) -> str:
    return _LANG_LABELS.get(code.strip().lower(), code.strip())


def _parse_translation_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)
        raw = raw.strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "translation" in data:
            t = data["translation"]
            if isinstance(t, str):
                return t.strip()
    except json.JSONDecodeError:
        pass
    return raw.strip().strip('"\'')


async def _translate_openai(
    client: httpx.AsyncClient,
    settings: Settings,
    text: str,
    from_lang: str,
    to_lang: str,
) -> str:
    if not settings.openai_api_key.strip():
        raise TranslationError("OPENAI_API_KEY is not set (required for OpenAI translation)", status_code=500)

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key.strip()}",
        "Content-Type": "application/json",
    }
    src = _lang_label(from_lang)
    tgt = _lang_label(to_lang)
    user_msg = (
        f"Source language: {src} (code {from_lang}).\n"
        f"Target language: {tgt} (code {to_lang}).\n\n"
        f"Translate the following text. Preserve tone, register, and line breaks where reasonable.\n\n"
        f"{text}"
    )
    payload = {
        "model": settings.openai_translation_model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional translator. "
                    'Respond with a single JSON object only: {"translation": "<translated text here>"}. '
                    "Escape any double quotes inside the translation as needed. No other keys or prose."
                ),
            },
            {"role": "user", "content": user_msg},
        ],
    }
    resp = await client.post(url, headers=headers, json=payload, timeout=120.0)
    if resp.status_code >= 400:
        raise TranslationError(
            f"OpenAI translation error: {resp.status_code} {resp.text[:800]}",
            status_code=resp.status_code,
        )
    data = resp.json()
    try:
        raw = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise TranslationError(f"Unexpected OpenAI chat response: {data!r}") from e
    return _parse_translation_json(raw)


async def _translate_anthropic(
    client: httpx.AsyncClient,
    settings: Settings,
    text: str,
    from_lang: str,
    to_lang: str,
) -> str:
    if not settings.anthropic_api_key.strip():
        raise TranslationError("ANTHROPIC_API_KEY is not set (required for Anthropic translation)", status_code=500)

    base = settings.anthropic_base_url.strip().rstrip("/")
    url = f"{base}/v1/messages"
    headers = {
        "x-api-key": settings.anthropic_api_key.strip(),
        "anthropic-version": settings.anthropic_version.strip() or "2023-06-01",
        "Content-Type": "application/json",
    }
    src = _lang_label(from_lang)
    tgt = _lang_label(to_lang)
    user_msg = (
        f"Source language: {src} (code {from_lang}).\n"
        f"Target language: {tgt} (code {to_lang}).\n\n"
        f"Translate the following text. Preserve tone, register, and line breaks where reasonable.\n\n"
        f"{text}\n\n"
        'Return ONLY valid JSON: {"translation": "<translated text>"}. No markdown fences or other text.'
    )
    payload = {
        "model": settings.anthropic_translation_model,
        "max_tokens": 8192,
        "system": (
            "You are a professional translator. "
            "Always output a single JSON object with key \"translation\" only."
        ),
        "messages": [{"role": "user", "content": user_msg}],
    }
    resp = await client.post(url, headers=headers, json=payload, timeout=120.0)
    if resp.status_code >= 400:
        raise TranslationError(
            f"Anthropic translation error: {resp.status_code} {resp.text[:800]}",
            status_code=resp.status_code,
        )
    data = resp.json()
    try:
        parts = data["content"]
        raw = "".join(p["text"] for p in parts if p.get("type") == "text")
    except (KeyError, TypeError) as e:
        raise TranslationError(f"Unexpected Anthropic response: {data!r}") from e
    return _parse_translation_json(raw)


async def translate_text(
    client: httpx.AsyncClient,
    settings: Settings,
    text: str,
    from_lang: str,
    to_lang: str,
) -> str:
    from_lang = from_lang.strip().lower()
    to_lang = to_lang.strip().lower()
    if from_lang == to_lang:
        return text

    provider = settings.translation_provider.strip().lower()
    if provider == "openai":
        return await _translate_openai(client, settings, text, from_lang, to_lang)
    if provider == "anthropic":
        return await _translate_anthropic(client, settings, text, from_lang, to_lang)
    raise TranslationError(
        f"Unknown TRANSLATION_PROVIDER: {provider}. Use 'openai' or 'anthropic'.",
        status_code=500,
    )


async def round_trip(
    client: httpx.AsyncClient,
    settings: Settings,
    text: str,
    source_lang: str,
    pivot_lang: str,
) -> str:
    mid = await translate_text(client, settings, text, source_lang, pivot_lang)
    return await translate_text(client, settings, mid, pivot_lang, source_lang)
