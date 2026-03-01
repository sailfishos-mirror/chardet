# Add Language Metadata to Encoding Registry — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the encoding registry the single source of truth for encoding-language mappings, add utf-7 to the registry, and standardize all language identifiers to ISO 639-1 codes.

**Architecture:** Add a `languages` field to `EncodingInfo`, populate it from the current `ENCODING_LANG_MAP` in train.py, then delete the duplicate mappings in train.py and models/__init__.py. Update escape.py to use ISO 639-1 codes.

**Tech Stack:** Python 3.10+, pytest

---

### Task 1: Add `languages` field to `EncodingInfo` and populate the registry

**Files:**
- Modify: `src/chardet/registry.py`

**Step 1: Add `languages` field to the `EncodingInfo` dataclass**

Add after the `python_codec` field (line 19):

```python
    languages: tuple[str, ...]  # ISO 639-1 codes for associated languages
```

**Step 2: Add `languages` to every existing `EncodingInfo` entry in `REGISTRY`**

Add `languages=(...)` to each entry. The values come from `scripts/train.py`'s `ENCODING_LANG_MAP`. Encodings not in `ENCODING_LANG_MAP` (e.g., ascii, utf-8-sig, utf-16/32 variants) get `languages=()`.

Here is the complete mapping to use (encoding name → languages tuple):

```
ascii              → ()
utf-8              → ()  # utf-8 models are trained on _ALL_LANGS but that's for language detection, not encoding identity
utf-8-sig          → ()
utf-16             → ()
utf-16-be          → ()
utf-16-le          → ()
utf-32             → ()
utf-32-be          → ()
utf-32-le          → ()
big5               → ("zh",)
cp932              → ("ja",)
cp949              → ("ko",)
euc-jp             → ("ja",)
euc-kr             → ("ko",)
gb18030            → ("zh",)
hz-gb-2312         → ("zh",)
iso-2022-jp        → ("ja",)
iso-2022-kr        → ("ko",)
shift_jis          → ("ja",)
cp874              → ("th",)
windows-1250       → ("pl", "cs", "hu", "hr", "ro", "sk", "sl")
windows-1251       → ("ru", "bg", "uk", "sr", "mk", "be")
windows-1252       → ("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms")
windows-1253       → ("el",)
windows-1254       → ("tr",)
windows-1255       → ("he",)
windows-1256       → ("ar", "fa")
windows-1257       → ("et", "lt", "lv")
windows-1258       → ("vi",)
koi8-r             → ("ru",)
koi8-u             → ("uk",)
tis-620            → ("th",)
iso-8859-1         → ("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms")
iso-8859-2         → ("pl", "cs", "hu", "hr", "ro", "sk", "sl")
iso-8859-3         → ("eo", "mt", "tr")
iso-8859-4         → ("et", "lt", "lv")
iso-8859-5         → ("ru", "bg", "uk", "sr", "mk", "be")
iso-8859-6         → ("ar", "fa")
iso-8859-7         → ("el",)
iso-8859-8         → ("he",)
iso-8859-9         → ("tr",)
iso-8859-10        → ("is", "fi")
iso-8859-13        → ("et", "lt", "lv")
iso-8859-14        → ("cy", "ga", "br", "gd")
iso-8859-15        → ("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms")
iso-8859-16        → ("ro", "pl", "hr", "hu", "sk", "sl")
johab              → ("ko",)
mac-cyrillic       → ("ru", "bg", "uk", "sr", "mk", "be")
mac-greek          → ("el",)
mac-iceland        → ("is",)
mac-latin2         → ("pl", "cs", "hu", "hr", "sk", "sl")
mac-roman          → ("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms")
mac-turkish        → ("tr",)
cp720              → ("ar", "fa")
cp1006             → ("ur",)
cp1125             → ("uk",)
koi8-t             → ("tg",)
kz-1048            → ("kk",)
ptcp154            → ("kk",)
hp-roman8          → ("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms")
cp437              → ("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "fi")
cp737              → ("el",)
cp775              → ("et", "lt", "lv")
cp850              → ("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms")
cp852              → ("pl", "cs", "hu", "hr", "sk", "sl")
cp855              → ("ru", "bg", "uk", "sr", "mk", "be")
cp856              → ("he",)
cp857              → ("tr",)
cp858              → ("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms")
cp860              → ("pt",)
cp861              → ("is",)
cp862              → ("he",)
cp863              → ("fr",)
cp864              → ("ar",)
cp865              → ("da", "no")
cp866              → ("ru", "bg", "uk", "sr", "mk", "be")
cp869              → ("el",)
cp037              → ("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms", "tr")
cp424              → ("he",)
cp500              → ("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms")
cp875              → ("el",)
cp1026             → ("tr",)
cp273              → ("de",)
```

**Important notes:**
- `utf-8` gets `languages=()` even though it has bigram models for all languages. The `languages` field represents what languages the encoding was *designed for*, not what models exist. utf-8 is language-agnostic. The training script will handle utf-8 specially.
- The values above include the pending train.py changes (cp866 with uk, cp437 with fi, cp850/cp858 with Nordic+SEA, mac-latin2 with sk/sl).

**Step 3: Add utf-7 to the REGISTRY**

Add after the utf-32-le entry (in the MODERN_WEB section):

```python
    EncodingInfo(
        name="utf-7",
        aliases=("utf7",),
        era=EncodingEra.MODERN_WEB,
        is_multibyte=False,
        python_codec="utf-7",
        languages=(),
    ),
```

**Step 4: Run registry tests to verify they pass**

Run: `uv run python -m pytest tests/test_registry.py -v`
Expected: All PASS (the new `languages` field doesn't break existing tests)

**Step 5: Commit**

```bash
git add src/chardet/registry.py
git commit -m "feat: add languages field to EncodingInfo and utf-7 to registry"
```

---

### Task 2: Write tests for registry language data

**Files:**
- Modify: `tests/test_registry.py`

**Step 1: Add tests for the new `languages` field**

Append to `tests/test_registry.py`:

```python
def test_languages_field_exists():
    """Every EncodingInfo has a languages tuple."""
    for enc in REGISTRY:
        assert isinstance(enc.languages, tuple), f"{enc.name} missing languages"
        for lang in enc.languages:
            assert isinstance(lang, str), f"{enc.name} has non-str language: {lang}"
            assert len(lang) == 2, f"{enc.name} has non-ISO-639-1 language: {lang}"


def test_single_language_encodings():
    """Spot-check single-language encodings."""
    by_name = {e.name: e for e in REGISTRY}
    assert by_name["shift_jis"].languages == ("ja",)
    assert by_name["euc-kr"].languages == ("ko",)
    assert by_name["gb18030"].languages == ("zh",)
    assert by_name["cp273"].languages == ("de",)
    assert by_name["koi8-r"].languages == ("ru",)


def test_multi_language_encodings():
    """Spot-check multi-language encodings."""
    by_name = {e.name: e for e in REGISTRY}
    assert "en" in by_name["windows-1252"].languages
    assert "fr" in by_name["windows-1252"].languages
    assert "ru" in by_name["windows-1251"].languages
    assert "bg" in by_name["windows-1251"].languages


def test_language_agnostic_encodings():
    """Unicode and ASCII encodings have empty languages tuple."""
    by_name = {e.name: e for e in REGISTRY}
    assert by_name["ascii"].languages == ()
    assert by_name["utf-8"].languages == ()
    assert by_name["utf-7"].languages == ()
    assert by_name["utf-16"].languages == ()


def test_utf7_in_registry():
    """utf-7 is in the registry as MODERN_WEB."""
    by_name = {e.name: e for e in REGISTRY}
    assert "utf-7" in by_name
    assert EncodingEra.MODERN_WEB in by_name["utf-7"].era
```

**Step 2: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_registry.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_registry.py
git commit -m "test: add tests for registry languages field and utf-7 entry"
```

---

### Task 3: Migrate `infer_language()` from `_SINGLE_LANG_MAP` to registry

**Files:**
- Modify: `src/chardet/models/__init__.py`

**Step 1: Replace `_SINGLE_LANG_MAP` with registry-based lookup**

Delete the `_SINGLE_LANG_MAP` dict (lines 27-72) and its preceding comment (lines 25-26).

Replace with:

```python
from chardet.registry import REGISTRY

# Built once from the registry: encoding -> language for single-language encodings.
_SINGLE_LANG_MAP: dict[str, str] = {
    enc.name: enc.languages[0]
    for enc in REGISTRY
    if len(enc.languages) == 1
}
# gb2312 is not in the registry (detector returns gb18030 instead) but
# needs a language mapping for accuracy test evaluation.
_SINGLE_LANG_MAP["gb2312"] = "zh"
```

The `infer_language()` function (line 157-164) stays exactly as-is — it already does `return _SINGLE_LANG_MAP.get(encoding)`.

**Important:** This module has a comment at the top saying `from __future__ import annotations` is intentionally omitted for mypyc compatibility. The import `from chardet.registry import REGISTRY` must be at module level (not inside a function) since mypyc needs it resolved at compile time.

**Step 2: Run tests to verify nothing breaks**

Run: `uv run python -m pytest tests/ -v -x`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/chardet/models/__init__.py
git commit -m "refactor: derive _SINGLE_LANG_MAP from registry instead of hardcoding"
```

---

### Task 4: Migrate `train.py` to import language data from registry

**Files:**
- Modify: `scripts/train.py`

**Step 1: Replace `ENCODING_LANG_MAP` and helper lists with registry import**

Delete `_WESTERN_EUROPEAN_LANGS` (lines 50-65), `_ALL_LANGS` (lines 67-117), and `ENCODING_LANG_MAP` (lines 119-249).

Replace with:

```python
from chardet.registry import REGISTRY

# Build encoding → language map from the registry.
ENCODING_LANG_MAP: dict[str, list[str]] = {
    enc.name: list(enc.languages)
    for enc in REGISTRY
    if enc.languages
}
# utf-8 is language-agnostic but we train it on ALL languages for
# language detection (Tier 3 fallback in the pipeline).
_ALL_LANGS = sorted({lang for enc in REGISTRY for lang in enc.languages})
ENCODING_LANG_MAP["utf-8"] = _ALL_LANGS
```

**Important:** `_ALL_LANGS` must stay available as a variable because it's used further down in the training script to determine which CulturaX languages to download. Verify by checking for `_ALL_LANGS` references elsewhere in the file.

**Step 2: Verify `_ALL_LANGS` is still correct**

Run:
```bash
uv run python -c "
from chardet.registry import REGISTRY
langs = sorted({lang for enc in REGISTRY for lang in enc.languages})
print(langs)
print(len(langs))
"
```

Expected: All 35 language codes, matching the old `_ALL_LANGS` list.

**Step 3: Run training dry-run to verify the mapping is correct**

Run: `uv run python -c "from scripts.train import ENCODING_LANG_MAP; print(len(ENCODING_LANG_MAP)); print(sorted(ENCODING_LANG_MAP.keys()))"`

Expected: Same number of entries as before (the old `ENCODING_LANG_MAP` had entries for all encodings with language associations, plus utf-8).

**Step 4: Run full test suite**

Run: `uv run python -m pytest`
Expected: All PASS

**Step 5: Commit**

```bash
git add scripts/train.py
git commit -m "refactor: derive ENCODING_LANG_MAP from registry instead of hardcoding"
```

---

### Task 5: Standardize escape.py language strings to ISO 639-1

**Files:**
- Modify: `src/chardet/pipeline/escape.py`

**Step 1: Change the three hardcoded language names**

In `detect_escape_encoding()`, change:
- Line 129: `language="Japanese"` → `language="ja"`
- Line 137: `language="Korean"` → `language="ko"`
- Line 146: `language="Chinese"` → `language="zh"`

**Step 2: Run escape tests**

Run: `uv run python -m pytest tests/test_escape.py -v`
Expected: All PASS (no tests check the language value)

**Step 3: Run full test suite to verify no regressions**

Run: `uv run python -m pytest`
Expected: All PASS. The accuracy tests use `normalize_language()` from `scripts/utils.py` which maps `"ja"` → `"japanese"`, `"ko"` → `"korean"`, `"zh"` → `"chinese"`, so the change is transparent to accuracy evaluation.

**Step 4: Commit**

```bash
git add src/chardet/pipeline/escape.py
git commit -m "refactor: standardize escape.py language strings to ISO 639-1 codes"
```

---

### Task 6: Update test_pipeline_types.py for consistency

**Files:**
- Modify: `tests/test_pipeline_types.py`

**Step 1: Change the test language string**

In `test_detection_result_fields()` (line 10), change:
- `language="English"` → `language="en"`

And on line 13:
- `assert r.language == "English"` → `assert r.language == "en"`

This test is just testing the dataclass works — it would pass either way — but keeping it consistent with the new standard avoids confusion.

**Step 2: Run the test**

Run: `uv run python -m pytest tests/test_pipeline_types.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/test_pipeline_types.py
git commit -m "test: use ISO 639-1 code in pipeline types test for consistency"
```

---

### Task 7: Final verification

**Step 1: Run full test suite**

Run: `uv run python -m pytest`
Expected: All PASS, same count as before (2454 passed, 75 xfailed)

**Step 2: Verify registry is the single source of truth**

Run:
```bash
uv run python -c "
from chardet.registry import REGISTRY
# Count total encodings
print(f'Total encodings in registry: {len(REGISTRY)}')
# Count with languages
with_langs = [e for e in REGISTRY if e.languages]
print(f'Encodings with language data: {len(with_langs)}')
# Count unique languages
all_langs = sorted({lang for e in REGISTRY for lang in e.languages})
print(f'Unique languages: {len(all_langs)}')
print(f'Languages: {all_langs}')
# Verify utf-7 is present
utf7 = next(e for e in REGISTRY if e.name == 'utf-7')
print(f'utf-7 in registry: era={utf7.era}, languages={utf7.languages}')
"
```

Expected: 84 encodings, ~65 with language data, 35 unique languages, utf-7 present.

**Step 3: Verify no hardcoded language maps remain**

Run:
```bash
grep -rn "Japanese\|Korean\|Chinese" src/chardet/ --include="*.py" | grep -v "test\|comment\|__pycache__"
```

Expected: No matches (all full language names removed from source).

**Step 4: Verify `_SINGLE_LANG_MAP` in models/__init__.py is now derived**

Run:
```bash
uv run python -c "
from chardet.models import _SINGLE_LANG_MAP
print(f'Single-language encodings: {len(_SINGLE_LANG_MAP)}')
# Verify gb2312 special case
print(f'gb2312 -> {_SINGLE_LANG_MAP.get(\"gb2312\")}')
# Verify a few others
print(f'shift_jis -> {_SINGLE_LANG_MAP.get(\"shift_jis\")}')
print(f'cp273 -> {_SINGLE_LANG_MAP.get(\"cp273\")}')
"
```

Expected: gb2312 → zh, shift_jis → ja, cp273 → de
