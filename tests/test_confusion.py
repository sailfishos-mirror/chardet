"""Tests for runtime confusion group resolution."""

from __future__ import annotations

from chardet.pipeline import DetectionResult
from chardet.pipeline.confusion import (
    load_confusion_data,
    resolve_by_bigram_rescore,
    resolve_by_category_voting,
    resolve_confusion_groups,
)


def test_load_confusion_data():
    """Loading confusion data from the bundled file should return valid maps."""
    maps = load_confusion_data()
    assert len(maps) > 0
    found_ebcdic = any(
        ("cp037" in key[0] and "cp500" in key[1])
        or ("cp500" in key[0] and "cp037" in key[1])
        for key in maps
    )
    assert found_ebcdic


def test_category_voting_prefers_letter_over_symbol():
    """Category voting should prefer letter (Ll) over symbol (So)."""
    diff_bytes = frozenset({0xD5})
    categories = {0xD5: ("Ll", "So")}
    data = bytes([0x41, 0xD5, 0x42])
    winner = resolve_by_category_voting(data, "enc_a", "enc_b", diff_bytes, categories)
    assert winner == "enc_a"


def test_category_voting_returns_none_on_no_distinguishing_bytes():
    """Category voting should return None when no distinguishing bytes are in data."""
    diff_bytes = frozenset({0xD5})
    categories = {0xD5: ("Ll", "So")}
    data = bytes([0x41, 0x42, 0x43])
    winner = resolve_by_category_voting(data, "enc_a", "enc_b", diff_bytes, categories)
    assert winner is None


def test_bigram_rescore_returns_valid_result():
    """Bigram re-scoring should return one of the encodings or None."""
    from chardet.models import load_models

    models = load_models()
    if not models:
        return
    diff_bytes = frozenset({0xD5})
    data = bytes([0x41, 0xD5, 0x42, 0xD5, 0x43])
    result = resolve_by_bigram_rescore(data, "cp850", "cp858", diff_bytes)
    assert result in ("cp850", "cp858", None)


def test_resolve_confusion_groups_no_change_when_unrelated():
    """Unrelated encodings should not be reordered by confusion resolution."""
    results = [
        DetectionResult(encoding="utf-8", confidence=0.95, language=None),
        DetectionResult(encoding="koi8-r", confidence=0.80, language="Russian"),
    ]
    resolved = resolve_confusion_groups(b"Hello world", results)
    assert resolved[0].encoding == "utf-8"


def test_resolve_confusion_groups_preserves_all_results():
    """Confusion resolution should preserve all results, only reorder."""
    results = [
        DetectionResult(encoding="cp037", confidence=0.95, language="English"),
        DetectionResult(encoding="cp500", confidence=0.94, language="English"),
        DetectionResult(encoding="windows-1252", confidence=0.50, language="English"),
    ]
    resolved = resolve_confusion_groups(bytes(range(256)), results)
    assert len(resolved) == len(results)
    resolved_encs = {r.encoding for r in resolved}
    assert resolved_encs == {"cp037", "cp500", "windows-1252"}
