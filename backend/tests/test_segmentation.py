from app.segmentation import align_segments, segment_text


def test_segment_sentences():
    s = "First. Second! Third?"
    parts = segment_text(s)
    assert len(parts) >= 2


def test_align_equal_lengths():
    orig = ["a", "b"]
    back = {"es": ["x", "y"], "ja": ["p", "q"]}
    o, b = align_segments(orig, back)
    assert o == ["a", "b"]
    assert b["es"] == ["x", "y"]


def test_align_mismatch_falls_back_to_single():
    orig = ["a", "b"]
    back = {"es": ["only"], "ja": ["x", "y"]}
    o, b = align_segments(orig, back)
    assert len(o) == 1
    assert o[0] == "a b"
    assert len(b["es"]) == 1
