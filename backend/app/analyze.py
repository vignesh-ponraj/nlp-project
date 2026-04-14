import httpx

from app.config import Settings
from app.embeddings import cosine_similarity, embed_texts
from app.metrics import surface_similarity
from app.schemas import (
    AnalyzeMeta,
    AnalyzeResponse,
    RoundTripResult,
    SegmentRow,
    Summary,
)
from app.segmentation import align_segments, segment_text
from app.translator import round_trip, TranslationError


def _risk_level(mean_cosines: dict[str, float], cross_gap: float) -> str:
    means = list(mean_cosines.values())
    if not means:
        return "unknown"
    lowest = min(means)
    if lowest >= 0.92 and cross_gap < 0.05:
        return "low"
    if lowest >= 0.85 and cross_gap < 0.12:
        return "medium"
    return "high"


async def run_analysis(
    client: httpx.AsyncClient,
    settings: Settings,
    text: str,
    source_lang: str,
    pivot_langs: list[str],
) -> AnalyzeResponse:
    text = text.strip()
    if len(text) > settings.max_input_chars:
        raise TranslationError(
            f"Text exceeds max length ({settings.max_input_chars} characters)",
            status_code=400,
        )

    p1, p2 = pivot_langs[0].strip().lower(), pivot_langs[1].strip().lower()
    if p1 == p2:
        raise TranslationError("Pivot languages must be distinct", status_code=400)
    if p1 == source_lang.lower() or p2 == source_lang.lower():
        raise TranslationError("Pivot languages must differ from source language", status_code=400)

    round_trips: list[RoundTripResult] = []
    backs: dict[str, str] = {}
    for piv in (p1, p2):
        try:
            back = await round_trip(client, settings, text, source_lang.lower(), piv)
        except TranslationError:
            raise
        backs[piv] = back
        round_trips.append(RoundTripResult(pivot_lang=piv, back_translation=back))

    orig_segs = segment_text(text)
    back_segs_map = {piv: segment_text(backs[piv]) for piv in (p1, p2)}
    orig_aligned, back_aligned = align_segments(orig_segs, back_segs_map)

    # Per segment: original, then back for p1, then back for p2 — one batch for OpenAI
    embed_inputs: list[str] = []
    for i, seg in enumerate(orig_aligned):
        embed_inputs.append(seg)
        embed_inputs.append(back_aligned[p1][i])
        embed_inputs.append(back_aligned[p2][i])

    vectors = await embed_texts(client, settings, embed_inputs)

    vec_by_key: dict[tuple[int, str], list[float]] = {}
    base = 0
    for i in range(len(orig_aligned)):
        vec_by_key[(i, "orig")] = vectors[base]
        vec_by_key[(i, p1)] = vectors[base + 1]
        vec_by_key[(i, p2)] = vectors[base + 2]
        base += 3

    segments_out: list[SegmentRow] = []
    cosines_p1: list[float] = []
    cosines_p2: list[float] = []

    for i in range(len(orig_aligned)):
        o = orig_aligned[i]
        b1 = back_aligned[p1][i]
        b2 = back_aligned[p2][i]
        c1 = cosine_similarity(vec_by_key[(i, "orig")], vec_by_key[(i, p1)])
        c2 = cosine_similarity(vec_by_key[(i, "orig")], vec_by_key[(i, p2)])
        cosines_p1.append(c1)
        cosines_p2.append(c2)
        segments_out.append(
            SegmentRow(
                i=i,
                original=o,
                back_by_pivot={p1: b1, p2: b2},
                cosine_by_pivot={p1: round(c1, 6), p2: round(c2, 6)},
                surface_by_pivot={
                    p1: round(surface_similarity(o, b1), 6),
                    p2: round(surface_similarity(o, b2), 6),
                },
            )
        )

    mean_p1 = sum(cosines_p1) / len(cosines_p1) if cosines_p1 else 0.0
    mean_p2 = sum(cosines_p2) / len(cosines_p2) if cosines_p2 else 0.0
    cross_gap = abs(mean_p1 - mean_p2)
    mean_cosine_by_pivot = {p1: round(mean_p1, 6), p2: round(mean_p2, 6)}

    emb_model = (
        settings.openai_embedding_model
        if settings.embedding_provider.lower() == "openai"
        else settings.gemini_embedding_model
    )

    return AnalyzeResponse(
        original_text=text,
        source_lang=source_lang.lower(),
        pivot_langs=[p1, p2],
        round_trips=round_trips,
        segments=segments_out,
        summary=Summary(
            mean_cosine_by_pivot=mean_cosine_by_pivot,
            cross_pivot_gap=round(cross_gap, 6),
            risk_level=_risk_level(mean_cosine_by_pivot, cross_gap),
        ),
        meta=AnalyzeMeta(
            translator_id="azure_translator_v3",
            embedding_provider=settings.embedding_provider.lower(),
            embedding_model_id=emb_model,
        ),
    )
