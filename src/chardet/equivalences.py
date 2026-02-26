"""Directional encoding equivalences for accuracy evaluation.

This module defines the single source of truth for which encoding detections
count as "correct" when compared against expected encodings. It is used by
the test framework and diagnostic scripts.

Two kinds of acceptable mismatch:

1. **Directional supersets**: detecting a superset encoding when the expected
   encoding is a subset is correct (e.g., detecting utf-8 when expected is
   ascii), but not the reverse. Each superset must map every
   alphanumeric/punctuation/currency byte in the subset to the identical
   character, with only additional such characters in the superset.

2. **Bidirectional equivalents**: encodings that are byte-for-byte identical
   for all alphanumeric/punctuation/currency characters (currently only
   UTF-16/UTF-32 endian variants).
"""

from __future__ import annotations

import codecs


def normalize_encoding_name(name: str) -> str:
    """Normalize encoding name for comparison."""
    try:
        return codecs.lookup(name).name
    except LookupError:
        return name.lower().replace("-", "").replace("_", "")


# Directional superset relationships: detecting any of the supersets
# when the expected encoding is the subset counts as correct.
# E.g., expected=ascii, detected=utf-8 -> correct (utf-8 ⊃ ascii).
# But expected=utf-8, detected=ascii -> wrong (ascii ⊄ utf-8).
SUPERSETS: dict[str, frozenset[str]] = {
    "ascii": frozenset({"utf-8"}),
    "tis-620": frozenset({"iso-8859-11", "cp874"}),
    "iso-8859-11": frozenset({"cp874"}),
    "gb2312": frozenset({"gb18030"}),
    "shift_jis": frozenset({"cp932"}),
    "euc-kr": frozenset({"cp949"}),
    # windows-1252 ⊃ iso-8859-1 (fills C1 control range 0x80-0x9F with 27 printable chars)
    "iso-8859-1": frozenset({"windows-1252"}),
    # windows-1254 ⊃ iso-8859-9 (fills C1 control range 0x80-0x9F with 25 printable chars)
    "iso-8859-9": frozenset({"windows-1254"}),
}

# Bidirectional equivalents -- byte-order variants only.
BIDIRECTIONAL_GROUPS: list[tuple[str, ...]] = [
    ("utf-16", "utf-16-le", "utf-16-be"),
    ("utf-32", "utf-32-le", "utf-32-be"),
]

# Pre-built normalized lookups for fast comparison.
_NORMALIZED_SUPERSETS: dict[str, frozenset[str]] = {
    normalize_encoding_name(subset): frozenset(
        normalize_encoding_name(s) for s in supersets
    )
    for subset, supersets in SUPERSETS.items()
}

_NORMALIZED_BIDIR: dict[str, frozenset[str]] = {}
for _group in BIDIRECTIONAL_GROUPS:
    _normed = frozenset(normalize_encoding_name(n) for n in _group)
    for _name in _group:
        _NORMALIZED_BIDIR[normalize_encoding_name(_name)] = _normed


def is_correct(expected: str, detected: str | None) -> bool:
    """Check whether *detected* is an acceptable answer for *expected*.

    Acceptable means:
    1. Exact match (after normalization), OR
    2. Both belong to the same bidirectional byte-order group, OR
    3. *detected* is a known superset of *expected*.
    """
    if detected is None:
        return False
    norm_exp = normalize_encoding_name(expected)
    norm_det = normalize_encoding_name(detected)

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
