from app.metrics import levenshtein_distance, surface_similarity


def test_levenshtein_identical():
    assert levenshtein_distance("abc", "abc") == 0


def test_levenshtein_empty():
    assert levenshtein_distance("", "abc") == 3


def test_surface_similarity():
    assert surface_similarity("hello", "hello") == 1.0
    assert surface_similarity("", "") == 1.0
    assert 0.0 <= surface_similarity("a", "bbbb") <= 1.0
