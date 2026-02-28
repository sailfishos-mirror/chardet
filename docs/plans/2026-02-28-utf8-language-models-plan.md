# UTF-8 Language Models Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable language detection for UTF-8/16/32 files by training UTF-8 byte bigram models and adding a decode-to-UTF-8 fallback in `_fill_language`.

**Architecture:** Train 48 UTF-8 byte bigram language models (one per language already in the training data). Add a Tier 3 to `_fill_language` that decodes any remaining `language=None` result to UTF-8 and scores against these models. UTF-8's variable-length encoding makes byte bigrams naturally discriminative across language families.

**Tech Stack:** Python, existing bigram training pipeline (`scripts/train.py`), existing scoring infrastructure (`chardet.models.BigramProfile`, `score_best_language`).

---

### Task 1: Add UTF-8 to training configuration

**Files:**
- Modify: `scripts/train.py:50-189` (the `ENCODING_LANG_MAP` dict)

**Step 1: Add UTF-8 entry to ENCODING_LANG_MAP**

In `scripts/train.py`, collect all unique languages from the existing map and add a UTF-8 entry. Add it after the existing `_WESTERN_EUROPEAN_LANGS` definition and before `ENCODING_LANG_MAP`:

```python
_ALL_LANGS = [
    "ar", "be", "bg", "br", "cs", "cy", "da", "de", "el", "eo",
    "es", "et", "fa", "fi", "fr", "ga", "gd", "he", "hr", "hu",
    "id", "is", "it", "ja", "kk", "ko", "lt", "lv", "mk", "ms",
    "mt", "nl", "no", "pl", "pt", "ro", "ru", "sk", "sl", "sr",
    "sv", "tg", "th", "tr", "uk", "ur", "vi", "zh",
]
```

Then add this entry to `ENCODING_LANG_MAP`:

```python
    # Universal Unicode encoding — trained on all languages for language detection
    "utf-8": _ALL_LANGS,
```

Place it at the end of the dict, before the closing `}`.

**Step 2: Retrain models**

Run:
```bash
uv run python scripts/train.py --encodings utf-8
```

This downloads CulturaX text for all 48 languages (most already cached from prior training), encodes each as UTF-8, builds byte bigram tables, and merges the 48 new models into `models.bin`.

Expected: 48 new models added (e.g. `ar/utf-8`, `fr/utf-8`, `ja/utf-8`, etc.). File size increases by ~100-150KB.

**Step 3: Verify models loaded correctly**

Run:
```bash
uv run python -c "
from chardet.models import load_models, _get_enc_index
index = _get_enc_index()
variants = index.get('utf-8', [])
print(f'UTF-8 language variants: {len(variants)}')
for lang, _ in sorted(variants):
    print(f'  {lang}')
"
```

Expected: 48 language variants listed.

**Step 4: Run existing tests to verify no regressions**

Run:
```bash
uv run pytest tests/ -q --tb=short --ignore=tests/test_accuracy.py
```

Expected: All pass (the new models don't affect detection since `_fill_language` tier 2 only fires for encodings with existing model variants, and tier 3 doesn't exist yet).

**Step 5: Commit**

```bash
git add scripts/train.py src/chardet/models/models.bin
git commit -m "feat: train UTF-8 byte bigram models for all 48 languages"
```

---

### Task 2: Add Tier 3 decode-to-UTF-8 fallback

**Files:**
- Modify: `src/chardet/pipeline/orchestrator.py:356-385` (the `_fill_language` function)

**Step 1: Update `_fill_language` with Tier 3**

Replace the current `_fill_language` function with:

```python
def _fill_language(
    data: bytes, results: list[DetectionResult]
) -> list[DetectionResult]:
    """Fill in language for results missing it.

    Tier 1: single-language encodings via hardcoded map (instant).
    Tier 2: multi-language encodings via statistical bigram scoring (lazy).
    Tier 3: decode to UTF-8, score against UTF-8 language models (universal fallback).
    """
    filled: list[DetectionResult] = []
    profile: BigramProfile | None = None
    utf8_profile: BigramProfile | None = None
    for result in results:
        if result.language is None and result.encoding is not None:
            # Tier 1: single-language encoding
            lang = infer_language(result.encoding)
            # Tier 2: statistical scoring for multi-language encodings
            if lang is None and data and has_model_variants(result.encoding):
                if profile is None:
                    profile = BigramProfile(data)
                _, lang = score_best_language(data, result.encoding, profile=profile)
            # Tier 3: decode to UTF-8, score against UTF-8 language models
            if lang is None and data and has_model_variants("utf-8"):
                utf8_data = _to_utf8(data, result.encoding)
                if utf8_data:
                    if utf8_profile is None or result.encoding != "utf-8":
                        utf8_profile = BigramProfile(utf8_data)
                    _, lang = score_best_language(
                        utf8_data, "utf-8", profile=utf8_profile
                    )
            if lang is not None:
                filled.append(
                    DetectionResult(
                        encoding=result.encoding,
                        confidence=result.confidence,
                        language=lang,
                    )
                )
                continue
        filled.append(result)
    return filled
```

**Step 2: Add `_to_utf8` helper**

Add this helper above `_fill_language`:

```python
def _to_utf8(data: bytes, encoding: str) -> bytes | None:
    """Decode data from encoding and re-encode as UTF-8 for language scoring.

    Returns None if decoding fails. For UTF-8, returns data as-is.
    """
    if encoding == "utf-8":
        return data
    try:
        return data.decode(encoding, errors="ignore").encode("utf-8")
    except (LookupError, UnicodeDecodeError):
        return None
```

**Step 3: Lint check**

Run:
```bash
uv run ruff check src/chardet/pipeline/orchestrator.py
```

Expected: All checks passed.

**Step 4: Run non-accuracy tests**

Run:
```bash
uv run pytest tests/ -q --tb=short --ignore=tests/test_accuracy.py
```

Expected: All pass.

**Step 5: Commit**

```bash
git add src/chardet/pipeline/orchestrator.py
git commit -m "feat: add Tier 3 decode-to-UTF-8 language fallback in _fill_language"
```

---

### Task 3: Verify accuracy and performance

**Step 1: Run accuracy tests and count language warnings**

Run:
```bash
uv run pytest tests/test_accuracy.py -q --tb=no 2>&1 | tail -1
uv run pytest tests/test_accuracy.py -q --tb=no 2>&1 | grep -c "Language mismatch"
uv run pytest tests/test_accuracy.py -q --tb=no 2>&1 | grep -c "Language mismatch.*got=None"
```

Expected:
- Same 78 encoding failures (no regressions)
- Language mismatches significantly reduced from 1153
- `got=None` count should drop from 1087 to ~14 (just ASCII files)

**Step 2: Benchmark performance**

Run (3 times, take median):
```bash
uv run python scripts/benchmark_time.py --pure
```

Expected: Baseline was ~5180ms. Acceptable if under ~5500ms (~6% overhead).
If above, investigate whether the `has_model_variants("utf-8")` guard is
working and the profile is built lazily.

**Step 3: Spot-check language detection**

Run:
```bash
uv run python -c "
import chardet
# UTF-8 Japanese
r = chardet.detect(open('tests/data/utf-8-japanese/culturax_mC4_63486.txt', 'rb').read())
print(f'UTF-8 Japanese: {r}')
# UTF-16 Russian (BOM)
import glob
f = glob.glob('tests/data/utf-16*/russian/*')[0]
r = chardet.detect(open(f, 'rb').read())
print(f'UTF-16 Russian: {r}')
"
```

Expected: Both should return the correct language.

**Step 4: Update performance doc**

Update `docs/rewrite_performance.md` Language Detection Accuracy section
with the new numbers.

**Step 5: Commit**

```bash
git add docs/rewrite_performance.md
git commit -m "docs: update language detection accuracy after UTF-8 models"
```
