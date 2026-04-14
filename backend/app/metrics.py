def levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def surface_similarity(a: str, b: str) -> float:
    """1.0 = identical, 0.0 = maximally different under normalized Levenshtein."""
    if not a and not b:
        return 1.0
    dist = levenshtein_distance(a, b)
    denom = max(len(a), len(b), 1)
    return max(0.0, 1.0 - dist / denom)
