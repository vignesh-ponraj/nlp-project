import asyncio
import math
from typing import Optional, Sequence

import httpx

from app.config import Settings


class EmbeddingError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


async def embed_openai(
    client: httpx.AsyncClient,
    settings: Settings,
    texts: list[str],
) -> list[list[float]]:
    if not settings.openai_api_key.strip():
        raise EmbeddingError("OPENAI_API_KEY is not set", status_code=500)

    url = f"{settings.openai_base_url.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.openai_embedding_model,
        "input": texts,
    }
    resp = await client.post(url, headers=headers, json=payload, timeout=120.0)
    if resp.status_code >= 400:
        raise EmbeddingError(
            f"OpenAI embeddings error: {resp.status_code} {resp.text[:500]}",
            status_code=resp.status_code,
        )
    data = resp.json()
    try:
        items = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in items]
    except (KeyError, TypeError, ValueError) as e:
        raise EmbeddingError(f"Unexpected OpenAI embedding response: {data!r}") from e


async def _gemini_embed_one(
    client: httpx.AsyncClient,
    settings: Settings,
    text: str,
) -> list[float]:
    model = settings.gemini_embedding_model.strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
    params = {"key": settings.gemini_api_key.strip()}
    body = {"content": {"parts": [{"text": text}]}}
    resp = await client.post(url, params=params, json=body, timeout=60.0)
    if resp.status_code >= 400:
        raise EmbeddingError(
            f"Gemini embedContent error: {resp.status_code} {resp.text[:500]}",
            status_code=resp.status_code,
        )
    data = resp.json()
    try:
        emb = data["embedding"]
        if isinstance(emb, dict) and "values" in emb:
            return emb["values"]
        if isinstance(emb, list):
            return emb
    except (KeyError, TypeError):
        pass
    raise EmbeddingError(f"Unexpected Gemini embedding response: {data!r}")


async def embed_gemini(
    client: httpx.AsyncClient,
    settings: Settings,
    texts: list[str],
) -> list[list[float]]:
    if not settings.gemini_api_key.strip():
        raise EmbeddingError("GEMINI_API_KEY is not set", status_code=500)

    results = await asyncio.gather(
        *[_gemini_embed_one(client, settings, t) for t in texts],
    )
    return list(results)


async def embed_texts(
    client: httpx.AsyncClient,
    settings: Settings,
    texts: list[str],
) -> list[list[float]]:
    provider = settings.embedding_provider.strip().lower()
    if provider == "openai":
        return await embed_openai(client, settings, texts)
    if provider == "gemini":
        return await embed_gemini(client, settings, texts)
    raise EmbeddingError(f"Unknown EMBEDDING_PROVIDER: {provider}", status_code=500)
