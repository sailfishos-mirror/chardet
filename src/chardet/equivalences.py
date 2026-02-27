"""Encoding equivalences and legacy name remapping.

This module defines:

1. **Directional supersets** for accuracy evaluation: detecting a superset
   encoding when the expected encoding is a subset is correct (e.g., detecting
   utf-8 when expected is ascii), but not the reverse.

2. **Bidirectional equivalents**: encodings that are byte-for-byte identical
   for all alphanumeric/punctuation/currency characters (currently only
   UTF-16/UTF-32 endian variants).

3. **Preferred superset mapping** for the ``should_rename_legacy`` API option:
   replaces detected ISO/subset encoding names with their Windows/CP superset
   equivalents that modern software actually uses.
"""

from __future__ import annotations

import codecs
import unicodedata


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
    "ascii": frozenset({"utf-8", "windows-1252"}),
    "tis-620": frozenset({"iso-8859-11", "cp874"}),
    "iso-8859-11": frozenset({"cp874"}),
    "gb2312": frozenset({"gb18030"}),
    "shift_jis": frozenset({"cp932"}),
    "euc-kr": frozenset({"cp949"}),
    # Each Windows code page fills the C1 control range (0x80-0x9F) with
    # printable characters, making it a strict superset of its ISO counterpart.
    "iso-8859-1": frozenset({"windows-1252"}),
    "iso-8859-2": frozenset({"windows-1250"}),
    "iso-8859-5": frozenset({"windows-1251"}),
    "iso-8859-6": frozenset({"windows-1256"}),
    "iso-8859-7": frozenset({"windows-1253"}),
    "iso-8859-8": frozenset({"windows-1255"}),
    "iso-8859-9": frozenset({"windows-1254"}),
    "iso-8859-13": frozenset({"windows-1257"}),
}

# Preferred superset name for each encoding, used by the ``should_rename_legacy``
# API option.  When enabled, detected encoding names are replaced with the
# Windows/CP superset that modern software actually uses (browsers, editors,
# etc. treat these ISO subsets as their Windows counterparts).
PREFERRED_SUPERSET: dict[str, str] = {
    "ascii": "Windows-1252",
    "euc-kr": "CP949",
    "iso-8859-1": "Windows-1252",
    "iso-8859-2": "Windows-1250",
    "iso-8859-5": "Windows-1251",
    "iso-8859-6": "Windows-1256",
    "iso-8859-7": "Windows-1253",
    "iso-8859-8": "Windows-1255",
    "iso-8859-9": "Windows-1254",
    "iso-8859-11": "CP874",
    "iso-8859-13": "Windows-1257",
    "tis-620": "CP874",
}


def apply_legacy_rename(
    result: dict[str, str | float | None],
) -> dict[str, str | float | None]:
    """Replace the encoding name with its preferred Windows/CP superset.

    Modifies the ``"encoding"`` value in *result* in-place and returns it.
    """
    enc = result.get("encoding")
    if isinstance(enc, str):
        result["encoding"] = PREFERRED_SUPERSET.get(enc.lower(), enc)
    return result


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


def _strip_combining(text: str) -> str:
    """NFKD-normalize *text* and strip all combining marks."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


# Specific symbol pairs that should be treated as equivalent.
# The generic currency sign (¤) was replaced by the euro sign (€) in later
# encoding revisions (e.g. iso-8859-15 vs iso-8859-1).  Detecting the euro
# encoding is always acceptable.
_EQUIVALENT_SYMBOLS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"¤", "€"}),
    }
)


def _chars_equivalent(a: str, b: str) -> bool:
    """Return True if characters *a* and *b* are functionally equivalent.

    Equivalent means:
    - Same character, OR
    - Same base letter after stripping combining marks, OR
    - An explicitly listed symbol equivalence (e.g. ¤ ↔ €)
    """
    if a == b:
        return True
    if frozenset({a, b}) in _EQUIVALENT_SYMBOLS:
        return True
    # Compare base letters after stripping combining marks.
    return _strip_combining(a) == _strip_combining(b)


def is_equivalent_detection(data: bytes, expected: str, detected: str | None) -> bool:
    """Check whether *detected* produces functionally identical text to *expected*.

    Returns ``True`` when:
    1. *detected* is not ``None`` and both encoding names normalize to the same
       codec, OR
    2. Decoding *data* with both encodings yields identical strings, OR
    3. Every differing character pair is functionally equivalent: same base
       letter after stripping combining marks, or an explicitly listed symbol
       equivalence (e.g. ¤ ↔ €).

    Returns ``False`` if *detected* is ``None``, either encoding is unknown,
    or either encoding cannot decode *data*.
    """
    if detected is None:
        return False

    norm_exp = normalize_encoding_name(expected)
    norm_det = normalize_encoding_name(detected)

    if norm_exp == norm_det:
        return True

    try:
        text_exp = data.decode(norm_exp)
        text_det = data.decode(norm_det)
    except (UnicodeDecodeError, LookupError):
        return False

    if text_exp == text_det:
        return True

    if len(text_exp) != len(text_det):
        return False

    return all(
        _chars_equivalent(a, b) for a, b in zip(text_exp, text_det, strict=False)
    )
