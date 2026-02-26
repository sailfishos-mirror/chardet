# tests/test_accuracy.py
"""Accuracy evaluation against the chardet test suite."""

from __future__ import annotations

import codecs
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

import chardet
from chardet.enums import EncodingEra

_MIN_OVERALL_ACCURACY = 0.75


def _normalize_encoding_name(name: str) -> str:
    """Normalize encoding name for comparison."""
    try:
        return codecs.lookup(name).name
    except LookupError:
        return name.lower().replace("-", "").replace("_", "")


# Directional superset relationships: detecting any of the supersets
# when the expected encoding is the subset counts as correct.
# E.g., expected=ascii, detected=utf-8 -> correct (utf-8 ⊃ ascii).
# But expected=utf-8, detected=ascii -> wrong (ascii ⊄ utf-8).
_SUPERSETS: dict[str, frozenset[str]] = {
    "ascii": frozenset({"utf-8"}),
    "tis-620": frozenset({"iso-8859-11", "cp874"}),
    "iso-8859-11": frozenset({"cp874"}),
    "gb2312": frozenset({"gb18030"}),
    "shift_jis": frozenset({"cp932"}),
    "euc-kr": frozenset({"cp949"}),
}

# Bidirectional equivalents — same character repertoire, byte-order only.
_BIDIRECTIONAL_GROUPS: list[tuple[str, ...]] = [
    ("utf-16", "utf-16-le", "utf-16-be"),
    ("utf-32", "utf-32-le", "utf-32-be"),
]

# Build normalized superset lookup: normalized subset -> frozenset of normalized supersets
_NORMALIZED_SUPERSETS: dict[str, frozenset[str]] = {
    _normalize_encoding_name(subset): frozenset(
        _normalize_encoding_name(s) for s in supersets
    )
    for subset, supersets in _SUPERSETS.items()
}

# Build normalized bidirectional lookup: normalized name -> frozenset of normalized group members
_NORMALIZED_BIDIR: dict[str, frozenset[str]] = {}
for _group in _BIDIRECTIONAL_GROUPS:
    _normed = frozenset(_normalize_encoding_name(n) for n in _group)
    for _name in _group:
        _NORMALIZED_BIDIR[_normalize_encoding_name(_name)] = _normed


def _is_correct(expected: str, detected: str | None) -> bool:
    """Check whether *detected* is an acceptable answer for *expected*.

    Acceptable means:
    1. Exact match (after normalization), OR
    2. Both belong to the same bidirectional byte-order group, OR
    3. *detected* is a known superset of *expected*.
    """
    if detected is None:
        return False
    norm_exp = _normalize_encoding_name(expected)
    norm_det = _normalize_encoding_name(detected)

    # 1. Exact match
    if norm_exp == norm_det:
        return True

    # 2. Bidirectional (same byte-order group)
    if norm_exp in _NORMALIZED_BIDIR and norm_det in _NORMALIZED_BIDIR[norm_exp]:
        return True

    # 3. Superset is acceptable (detected is a known superset of expected)
    return (
        norm_exp in _NORMALIZED_SUPERSETS
        and norm_det in _NORMALIZED_SUPERSETS[norm_exp]
    )


def _collect_test_files(data_dir: Path) -> list[tuple[str, str, Path]]:
    """Collect (encoding, language, filepath) tuples from test data.

    Directory name format: "{encoding}-{language}" e.g. "utf-8-english",
    "iso-8859-1-french", "hz-gb-2312-chinese".

    Since all language names are single words (no hyphens), we can reliably
    split on the last hyphen to separate encoding from language.
    """
    test_files: list[tuple[str, str, Path]] = []
    for encoding_dir in sorted(data_dir.iterdir()):
        if not encoding_dir.is_dir():
            continue
        # Split on last hyphen: encoding may contain hyphens, language never does
        parts = encoding_dir.name.rsplit("-", 1)
        if len(parts) != 2:
            # Directories without a hyphen (e.g. "ascii", "None") are skipped
            continue
        encoding_name, language = parts
        for filepath in sorted(encoding_dir.iterdir()):
            if filepath.is_file():
                test_files.append((encoding_name, language, filepath))
    return test_files


def test_overall_accuracy(chardet_test_data_dir: Path) -> None:
    """Test overall detection accuracy across all test files."""
    test_files = _collect_test_files(chardet_test_data_dir)
    if not test_files:
        pytest.skip("No test data found")

    correct = 0
    total = 0
    failures: list[str] = []

    for expected_encoding, _language, filepath in test_files:
        data = filepath.read_bytes()
        result = chardet.detect(data, encoding_era=EncodingEra.ALL)
        detected = result["encoding"]

        total += 1

        if _is_correct(expected_encoding, detected):
            correct += 1
        else:
            failures.append(
                f"  {filepath.parent.name}/{filepath.name}: "
                f"expected={expected_encoding}, got={detected} "
                f"(confidence={result['confidence']:.2f})"
            )

    accuracy = correct / total if total > 0 else 0.0
    print(f"\nAccuracy: {correct}/{total} = {accuracy:.1%}")
    if failures:
        print(f"Failures ({len(failures)}):")
        for f in failures[:30]:
            print(f)
        if len(failures) > 30:
            print(f"  ... and {len(failures) - 30} more")

    assert accuracy >= _MIN_OVERALL_ACCURACY, (
        f"Overall accuracy {accuracy:.1%} below threshold {_MIN_OVERALL_ACCURACY:.0%}"
    )
