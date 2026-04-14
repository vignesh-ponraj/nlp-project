from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source_lang: str = Field(..., min_length=2, max_length=10, description="BCP-47 / ISO code, e.g. en")
    pivot_langs: list[str] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Exactly two pivot language codes",
    )


class RoundTripResult(BaseModel):
    pivot_lang: str
    back_translation: str


class SegmentRow(BaseModel):
    i: int
    original: str
    back_by_pivot: dict[str, str] = Field(
        ...,
        description="Map pivot_lang -> back-translated segment text",
    )
    cosine_by_pivot: dict[str, float]
    surface_by_pivot: dict[str, float]


class Summary(BaseModel):
    mean_cosine_by_pivot: dict[str, float]
    cross_pivot_gap: float
    risk_level: str


class AnalyzeMeta(BaseModel):
    translator_id: str
    embedding_provider: str
    embedding_model_id: str


class AnalyzeResponse(BaseModel):
    original_text: str
    source_lang: str
    pivot_langs: list[str]
    round_trips: list[RoundTripResult]
    segments: list[SegmentRow]
    summary: Summary
    meta: AnalyzeMeta
