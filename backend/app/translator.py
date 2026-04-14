"""Azure AI Translator REST API v3."""

from typing import Optional

import httpx

from app.config import Settings


class TranslationError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


async def translate_text(
    client: httpx.AsyncClient,
    settings: Settings,
    text: str,
    from_lang: str,
    to_lang: str,
) -> str:
    if not settings.azure_translator_key.strip():
        raise TranslationError("AZURE_TRANSLATOR_KEY is not set", status_code=500)

    from_lang = from_lang.strip().lower()
    to_lang = to_lang.strip().lower()
    if from_lang == to_lang:
        return text

    url = f"{settings.azure_translator_endpoint.rstrip('/')}/translate"
    params = {
        "api-version": "3.0",
        "from": from_lang,
        "to": to_lang,
    }
    headers = {
        "Ocp-Apim-Subscription-Key": settings.azure_translator_key.strip(),
        "Content-Type": "application/json",
    }
    region = settings.azure_translator_region.strip()
    if region:
        headers["Ocp-Apim-Subscription-Region"] = region

    body = [{"text": text}]

    resp = await client.post(url, params=params, headers=headers, json=body, timeout=60.0)
    if resp.status_code >= 400:
        raise TranslationError(
            f"Azure Translator error: {resp.status_code} {resp.text[:500]}",
            status_code=resp.status_code,
        )
    data = resp.json()
    try:
        return data[0]["translations"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise TranslationError(f"Unexpected translator response: {data!r}") from e


async def round_trip(
    client: httpx.AsyncClient,
    settings: Settings,
    text: str,
    source_lang: str,
    pivot_lang: str,
) -> str:
    mid = await translate_text(client, settings, text, source_lang, pivot_lang)
    return await translate_text(client, settings, mid, pivot_lang, source_lang)
