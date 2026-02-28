"""Tests for confusion group computation and resolution."""

from __future__ import annotations

from chardet.pipeline.confusion import (
    compute_confusion_groups,
    compute_distinguishing_maps,
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
    diff_bytes, categories = maps[pair_key]
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
