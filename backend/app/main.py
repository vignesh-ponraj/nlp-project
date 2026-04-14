from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.analyze import run_analysis
from app.config import get_settings
from app.embeddings import EmbeddingError
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.translator import TranslationError


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient()
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="PivotDrift API",
    description="Cross-lingual meaning drift via dual-pivot round-trip translation.",
    version="1.0.0",
    lifespan=lifespan,
)

_settings = get_settings()
_origins = [o.strip() for o in _settings.frontend_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest) -> AnalyzeResponse:
    settings = get_settings()
    client: httpx.AsyncClient = app.state.http_client
    try:
        return await run_analysis(
            client,
            settings,
            body.text,
            body.source_lang,
            body.pivot_langs,
        )
    except TranslationError as e:
        code = e.status_code or 502
        if code >= 500:
            raise HTTPException(status_code=502, detail=str(e)) from e
        raise HTTPException(status_code=code, detail=str(e)) from e
    except EmbeddingError as e:
        code = e.status_code or 502
        raise HTTPException(status_code=code, detail=str(e)) from e
