"""Tests for confusion group computation and resolution."""

from __future__ import annotations

import tempfile
from pathlib import Path

from chardet.pipeline import DetectionResult
from chardet.pipeline.confusion import (
    compute_confusion_groups,
    compute_distinguishing_maps,
    deserialize_confusion_data,
    load_confusion_data,
    resolve_by_bigram_rescore,
    resolve_by_category_voting,
    resolve_confusion_groups,
    serialize_confusion_data,
)


def test_compute_confusion_groups_finds_ebcdic():
    """EBCDIC encodings (cp037, cp500) should be in the same confusion group."""
    groups = compute_confusion_groups(threshold=0.80)
    cp037_group = None
    for group in groups:
        if "cp037" in group:
            cp037_group = group
            break
    assert cp037_group is not None, "cp037 should be in a confusion group"
    assert "cp500" in cp037_group, "cp500 should be in the same group as cp037"


def test_compute_confusion_groups_finds_dos():
    """DOS encodings cp437 and cp865 differ by only 3 bytes — same group."""
    groups = compute_confusion_groups(threshold=0.80)
    cp437_group = None
    for group in groups:
        if "cp437" in group:
            cp437_group = group
            break
    assert cp437_group is not None
    assert "cp865" in cp437_group


def test_unrelated_encodings_not_grouped():
    """Unrelated encodings should not be in the same group."""
    groups = compute_confusion_groups(threshold=0.80)
    for group in groups:
        # KOI8-R (Cyrillic) should never be grouped with cp437 (DOS Latin)
        assert not ("koi8-r" in group and "cp437" in group)


def test_distinguishing_map_cp037_cp500():
    """cp037 and cp500 should have exactly 7 distinguishing bytes."""
    maps = compute_distinguishing_maps(threshold=0.80)
    pair_key = ("cp037", "cp500") if ("cp037", "cp500") in maps else ("cp500", "cp037")
    assert pair_key in maps
    diff_bytes, _categories = maps[pair_key]
    assert len(diff_bytes) == 7


def test_distinguishing_map_has_categories():
    """Each distinguishing byte should have Unicode category info."""
    maps = compute_distinguishing_maps(threshold=0.80)
    for diff_bytes, categories in maps.values():
        for byte_val in diff_bytes:
            assert byte_val in categories
            cat_a, cat_b = categories[byte_val]
            # Categories should be 2-char Unicode general category strings
            assert len(cat_a) == 2
            assert len(cat_b) == 2


def test_serialize_deserialize_roundtrip():
    """Serialization and deserialization should preserve all data."""
    maps = compute_distinguishing_maps(threshold=0.80)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = Path(f.name)
    try:
        serialize_confusion_data(maps, str(path))
        loaded = deserialize_confusion_data(str(path))
        assert len(loaded) == len(maps)
        for key in maps:
            assert key in loaded or (key[1], key[0]) in loaded
    finally:
        path.unlink(missing_ok=True)


def test_serialized_file_is_small():
    """Confusion data should be <10KB."""
    maps = compute_distinguishing_maps(threshold=0.80)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = Path(f.name)
    try:
        serialize_confusion_data(maps, str(path))
        assert path.stat().st_size < 10_000
    finally:
        path.unlink(missing_ok=True)


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
