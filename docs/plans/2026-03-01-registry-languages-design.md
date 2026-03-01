# Add Language Metadata to Encoding Registry — Design

## Goal

Make the encoding registry (`src/chardet/registry.py`) the single source of truth for all supported encodings and their associated languages. Standardize language identifiers to ISO 639-1 codes throughout the codebase.

## Problem

Language-encoding mappings currently live in three places:

1. **`scripts/train.py`** — `ENCODING_LANG_MAP` (multi-language, used only for training)
2. **`src/chardet/models/__init__.py`** — `_SINGLE_LANG_MAP` (single-language, used at runtime)
3. **`src/chardet/pipeline/escape.py`** — hardcoded full names (`"Japanese"`, `"Korean"`, `"Chinese"`)

This causes inconsistency (ISO 639-1 codes vs full names), duplication, and hides useful metadata from users.

Additionally, utf-7 is a supported encoding but is not in the registry.

## Design

### Data Model

Add a `languages` field to `EncodingInfo`:

```python
@dataclasses.dataclass(frozen=True, slots=True)
class EncodingInfo:
    name: str
    aliases: tuple[str, ...]
    era: EncodingEra
    is_multibyte: bool
    python_codec: str
    languages: tuple[str, ...]  # ISO 639-1 codes
```

Semantics:
- Empty tuple `()` — language-agnostic (ascii, utf-8, utf-16/32 variants, utf-7, utf-8-sig)
- Single element `("ja",)` — single-language encoding (shift_jis, euc-jp, etc.)
- Multiple elements `("en", "fr", "de", ...)` — multi-language encoding (windows-1252, etc.)

### Registry Completeness

Add utf-7 to `REGISTRY` so it contains every encoding the detector can return. utf-7 will have `languages=()` since it's language-agnostic. gb2312 stays out (the detector returns gb18030 instead).

### Language Standardization

All `DetectionResult.language` values will use ISO 639-1 two-letter codes. The three hardcoded full names in `escape.py` change:
- `"Japanese"` → `"ja"`
- `"Korean"` → `"ko"`
- `"Chinese"` → `"zh"`

This is a **breaking change** for users checking `result["language"]` against these three full names.

### Files Changed

1. **`src/chardet/registry.py`** — Add `languages` field to `EncodingInfo` and every registry entry. Add utf-7. Values sourced from current `train.py` `ENCODING_LANG_MAP`.

2. **`src/chardet/models/__init__.py`** — Delete `_SINGLE_LANG_MAP`. Rewrite `infer_language()` to look up from the registry (single-language encodings: `len(info.languages) == 1`).

3. **`scripts/train.py`** — Delete `ENCODING_LANG_MAP` and its helper lists (`_WESTERN_EUROPEAN_LANGS`, etc.). Import language info from the registry instead.

4. **`src/chardet/pipeline/escape.py`** — Change three language strings to ISO 639-1 codes.

5. **Tests** — Update any assertions that check for full language names (none found, but verify).

### What Doesn't Change

- `get_candidates()` — still filters by era only
- Pipeline stage order — escape detection still returns before registry candidates are used
- `DetectionResult` type — still `language: str | None`
- Model file format — still `language/encoding` keyed in `models.bin`
- `_ALL_LANGS` list in train.py — still needed to know which CulturaX languages to download; derived from registry at import time instead of hardcoded

### Migration Path for `infer_language()`

Current:
```python
def infer_language(encoding: str) -> str | None:
    return _SINGLE_LANG_MAP.get(encoding)
```

After:
```python
# Build lookup once from registry
_LANG_BY_ENCODING: dict[str, str] = {
    enc.name: enc.languages[0]
    for enc in REGISTRY
    if len(enc.languages) == 1
}

def infer_language(encoding: str) -> str | None:
    return _LANG_BY_ENCODING.get(encoding)
```

### Migration Path for `train.py`

Current:
```python
ENCODING_LANG_MAP = {
    "shift_jis": ["ja"],
    "windows-1252": _WESTERN_EUROPEAN_LANGS,
    ...
}
```

After:
```python
from chardet.registry import REGISTRY

ENCODING_LANG_MAP = {
    enc.name: list(enc.languages)
    for enc in REGISTRY
    if enc.languages  # skip language-agnostic encodings
}
```

Helper lists like `_WESTERN_EUROPEAN_LANGS` and `_ALL_LANGS` are derived from the registry data rather than hardcoded.
