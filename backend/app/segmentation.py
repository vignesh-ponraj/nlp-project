import re


def segment_text(text: str, max_window: int = 80) -> list[str]:
    """
    Split into sentences on . ! ? (optionally followed by quote/space).
    If that yields a single chunk or empty, fall back to overlapping windows.
    """
    text = text.strip()
    if not text:
        return []

    parts = re.split(r"(?<=[.!?])\s+", text)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        return parts

    if len(text) <= max_window:
        return [text] if text else []

    out: list[str] = []
    step = max_window * 2 // 3
    for i in range(0, len(text), step):
        chunk = text[i : i + max_window].strip()
        if chunk:
            out.append(chunk)
    return out if out else [text]


def align_segments(
    original_segments: list[str],
    back_segments_by_pivot: dict[str, list[str]],
) -> tuple[list[str], dict[str, list[str]]]:
    """
    If every pivot has the same segment count as original, return as-is.
    Otherwise fall back to single-segment (full text) mode for all.
    """
    n = len(original_segments)
    if n == 0:
        return [], {k: [] for k in back_segments_by_pivot}

    for segs in back_segments_by_pivot.values():
        if len(segs) != n:
            merged_orig = [" ".join(original_segments)]
            merged_back = {k: [" ".join(v)] for k, v in back_segments_by_pivot.items()}
            return merged_orig, merged_back

    return original_segments, back_segments_by_pivot
