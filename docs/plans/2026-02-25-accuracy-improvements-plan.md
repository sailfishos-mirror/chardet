# Accuracy Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Match or exceed charset-normalizer's 76.0% accuracy (strict directional equivalence classes) and eliminate None results for non-binary text.

**Architecture:** Six changes layered on the existing pipeline: (1) fix the test framework's equivalence classes, (2) gate CJK multi-byte encodings on structural evidence, (3) add era-based tiebreaking to Stage 3 output, (4) retrain models for specific encodings, (5) add windows-1252 fallback for non-binary text, (6) update diagnostic scripts for directional equivalences.

**Tech Stack:** Python 3.10+, pytest, uv, ruff. Training: Hugging Face `datasets` (CulturaX).

---

### Task 1: Fix test framework — directional equivalence classes

Replace the bidirectional equivalence groups in `tests/test_accuracy.py` with directional superset relationships. Detecting a superset encoding when the expected encoding is a subset is OK; detecting a subset is not.

**Files:**
- Modify: `tests/test_accuracy.py`

**Step 1: Write the updated equivalence logic in test_accuracy.py**

Replace the entire equivalence section (lines 28-66) with directional logic:

```python
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

# Build lookup: normalized name -> set of normalized names in same group
_BIDIRECTIONAL_MAP: dict[str, set[str]] = {}
for _group in _BIDIRECTIONAL_GROUPS:
    _norms = {_normalize_encoding_name(n) for n in _group}
    for _n in _norms:
        _BIDIRECTIONAL_MAP[_n] = _norms

# Build superset lookup using normalized names
_SUPERSET_MAP: dict[str, frozenset[str]] = {}
for _expected, _supers in _SUPERSETS.items():
    _SUPERSET_MAP[_normalize_encoding_name(_expected)] = frozenset(
        _normalize_encoding_name(s) for s in _supers
    )


def _is_correct(expected: str, detected: str | None) -> bool:
    """Check if detected encoding is acceptable for the expected encoding."""
    if detected is None:
        return False
    norm_expected = _normalize_encoding_name(expected)
    norm_detected = _normalize_encoding_name(detected)

    # Exact match
    if norm_expected == norm_detected:
        return True

    # Bidirectional (byte-order variants)
    if norm_expected in _BIDIRECTIONAL_MAP:
        if norm_detected in _BIDIRECTIONAL_MAP[norm_expected]:
            return True

    # Superset is acceptable
    if norm_expected in _SUPERSET_MAP:
        if norm_detected in _SUPERSET_MAP[norm_expected]:
            return True

    return False
```

Then update the test function to use `_is_correct()` instead of the old `_canonical_name()` comparison. Remove `_EQUIVALENT_GROUPS`, `_ENCODING_EQUIVALENCES`, and `_canonical_name()`.

In `test_overall_accuracy`, replace:
```python
        expected_canonical = _canonical_name(expected_encoding)
        detected_canonical = _canonical_name(detected) if detected else ""

        if expected_canonical == detected_canonical:
```
with:
```python
        if _is_correct(expected_encoding, detected):
```

**Step 2: Run tests to verify the framework change works**

Run: `uv run pytest tests/test_accuracy.py -v`

Expected: test_overall_accuracy fails because the accuracy threshold (0.79) is now too high for the stricter directional equivalence classes. The actual accuracy should be around ~75%.

**Step 3: Lower the accuracy threshold to match the new baseline**

Change `_MIN_OVERALL_ACCURACY` from `0.79` to `0.74` temporarily. We'll raise it as we make accuracy improvements.

**Step 4: Run tests again**

Run: `uv run pytest tests/test_accuracy.py -v`
Expected: PASS

**Step 5: Run full test suite to verify no regressions**

Run: `uv run pytest tests/ --deselect tests/test_benchmark.py -v`
Expected: All tests pass.

**Step 6: Commit**

```bash
git add tests/test_accuracy.py
git commit -m "test: replace bidirectional equivalences with directional superset classes"
```

---

### Task 2: Fallback behavior — binary confidence and windows-1252 fallback

Modify the orchestrator to:
1. Return confidence 0.95 for binary detections (instead of 0.0).
2. Return windows-1252 with confidence 0.10 for empty input and non-binary text that gets no result.

**Files:**
- Modify: `src/chardet/pipeline/orchestrator.py`
- Modify: `tests/test_orchestrator.py`
- Modify: `tests/test_api.py`

**Step 1: Write failing tests**

In `tests/test_orchestrator.py`, add:

```python
def test_empty_input_returns_fallback():
    """Empty input should return windows-1252 fallback, not None."""
    result = run_pipeline(b"", EncodingEra.MODERN_WEB)
    assert result[0].encoding == "windows-1252"
    assert result[0].confidence == 0.10


def test_binary_content_confidence():
    """Binary content should return None encoding with high confidence."""
    data = b"\x00\x01\x02\x03\x04\x05" * 100
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding is None
    assert result[0].confidence == 0.95


def test_single_high_byte_returns_fallback():
    """A single high byte (non-binary, non-ASCII) should return windows-1252 fallback."""
    result = run_pipeline(b"\xe4", EncodingEra.MODERN_WEB)
    assert result[0].encoding is not None
```

In `tests/test_api.py`, update `test_detect_empty`:

```python
def test_detect_empty():
    result = chardet.detect(b"")
    assert result["encoding"] == "windows-1252"
    assert result["confidence"] == 0.10
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_orchestrator.py::test_empty_input_returns_fallback tests/test_orchestrator.py::test_binary_content_confidence tests/test_api.py::test_detect_empty -v`
Expected: FAIL

**Step 3: Implement the changes in orchestrator.py**

In `src/chardet/pipeline/orchestrator.py`:

1. Replace `_NONE_RESULT` with two constants:
```python
_BINARY_RESULT = DetectionResult(encoding=None, confidence=0.95, language=None)
_FALLBACK_RESULT = DetectionResult(encoding="windows-1252", confidence=0.10, language=None)
```

2. Change the empty-data return (line 36):
```python
    if not data:
        return [_FALLBACK_RESULT]
```

3. Change the binary detection return (line 60):
```python
    if is_binary(data, max_bytes=max_bytes):
        return [_BINARY_RESULT]
```

4. Change the no-candidates return (line 84):
```python
    if not valid_candidates:
        return [_FALLBACK_RESULT]
```

5. Change the no-results return (line 114-115):
```python
    if not results:
        return [_FALLBACK_RESULT]
```

**Step 4: Run tests**

Run: `uv run pytest tests/test_orchestrator.py tests/test_api.py -v`
Expected: PASS (some old tests may need updating if they asserted `encoding is None` for empty input or `confidence == 0.0` for binary).

Fix any assertion failures in existing tests that relied on the old behavior:
- `test_empty_input` in test_orchestrator.py: update to expect `windows-1252` with confidence 0.10
- `test_binary_content` in test_orchestrator.py: update to expect confidence 0.95
- Any detector tests that test empty/binary behavior

**Step 5: Run full test suite**

Run: `uv run pytest tests/ --deselect tests/test_benchmark.py -v`
Expected: All pass.

**Step 6: Commit**

```bash
git add src/chardet/pipeline/orchestrator.py tests/test_orchestrator.py tests/test_api.py
git commit -m "feat: add windows-1252 fallback and binary confidence to pipeline"
```

---

### Task 3: CJK gating — require multi-byte structural evidence

Add a gate after Stage 2a that eliminates CJK multi-byte candidates (gb18030, cp932, big5, euc-jp, euc-kr, johab) unless the data contains actual multi-byte sequences. This prevents these permissive encodings from winning as false positives for single-byte data.

**Files:**
- Modify: `src/chardet/pipeline/orchestrator.py`
- Create: `tests/test_cjk_gating.py`

**Step 1: Write failing tests**

Create `tests/test_cjk_gating.py`:

```python
"""Tests for CJK multi-byte gating in the pipeline."""

from chardet.enums import EncodingEra
from chardet.pipeline.orchestrator import run_pipeline


def test_ebcdic_not_detected_as_gb18030():
    """EBCDIC text (cp037) should not be misdetected as gb18030."""
    # "Hello World" in cp037 (EBCDIC)
    data = "Hello World, this is a test of EBCDIC encoding.".encode("cp037")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding != "gb18030"


def test_latin_text_not_detected_as_cp932():
    """Western European text should not be misdetected as cp932/Shift_JIS."""
    data = "Héllo wörld, tëst dàta wïth äccénts.".encode("iso-8859-1")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding != "cp932"


def test_real_cjk_still_detected():
    """Real CJK text should still be detected as a CJK encoding."""
    data = "これはテストです。日本語のテキストです。".encode("shift_jis")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding in {"shift_jis", "cp932"}


def test_real_chinese_still_detected():
    """Real Chinese text should still be detected as gb18030."""
    data = "这是一个测试。中文文本应该被正确检测。".encode("gb18030")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "gb18030"


def test_real_korean_still_detected():
    """Real Korean text should still be detected as euc-kr or cp949."""
    data = "이것은 테스트입니다. 한국어 텍스트입니다.".encode("euc-kr")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding in {"euc-kr", "cp949"}
```

**Step 2: Run tests to verify some fail**

Run: `uv run pytest tests/test_cjk_gating.py -v`
Expected: `test_ebcdic_not_detected_as_gb18030` and `test_latin_text_not_detected_as_cp932` likely FAIL (they detect as CJK). The real CJK tests should PASS already.

**Step 3: Implement CJK gating in orchestrator.py**

In `src/chardet/pipeline/orchestrator.py`, after Stage 2a (the `filter_by_validity` call on line 81), add a CJK evidence gate:

```python
    # Gate: eliminate CJK multi-byte candidates unless the data contains
    # actual multi-byte sequences (≥5% of bytes in valid sequences).
    _CJK_MIN_MB_RATIO = 0.05
    gated_candidates = []
    for enc in valid_candidates:
        if enc.is_multibyte:
            mb_score = compute_structural_score(data, enc)
            if mb_score < _CJK_MIN_MB_RATIO:
                continue  # No multi-byte structure → eliminate
        gated_candidates.append(enc)

    if not gated_candidates:
        return [_FALLBACK_RESULT]

    valid_candidates = gated_candidates
```

Insert this between the `filter_by_validity` call (line 81) and the Stage 2b structural probing (line 87). The structural probing stage below will then only see candidates that passed the gate.

**Step 4: Run the CJK gating tests**

Run: `uv run pytest tests/test_cjk_gating.py -v`
Expected: All PASS.

**Step 5: Run full test suite**

Run: `uv run pytest tests/ --deselect tests/test_benchmark.py -v`
Expected: All pass. If any existing tests break (e.g., a test that expected a CJK result for non-CJK data), investigate and fix.

**Step 6: Run diagnostic script to measure accuracy improvement**

Run: `uv run python scripts/diagnose_accuracy.py`
Expected: Noticeable improvement — EBCDIC, johab, and other false-positive CJK detections should be fixed. Note the new accuracy number.

**Step 7: Update accuracy threshold if improved**

If accuracy has improved, raise `_MIN_OVERALL_ACCURACY` in `tests/test_accuracy.py` to lock in the gain (set it 1% below the measured accuracy to allow for minor variance).

**Step 8: Commit**

```bash
git add src/chardet/pipeline/orchestrator.py tests/test_cjk_gating.py tests/test_accuracy.py
git commit -m "feat: gate CJK multi-byte candidates on structural evidence"
```

---

### Task 4: Era-based tiebreaking

When statistical scores are close (within 10% relative), prefer encodings from the requested `encoding_era`. This is implemented as a post-processing step on Stage 3 results.

**Files:**
- Modify: `src/chardet/pipeline/orchestrator.py`
- Modify: `src/chardet/enums.py` (add era priority)
- Create: `tests/test_era_tiebreak.py`

**Step 1: Write failing tests**

Create `tests/test_era_tiebreak.py`:

```python
"""Tests for era-based tiebreaking."""

from chardet.enums import EncodingEra
from chardet.pipeline.orchestrator import run_pipeline


def test_modern_web_preferred_over_mac():
    """When scores are close, MODERN_WEB encodings should beat LEGACY_MAC."""
    # Central European text that could match both iso-8859-2 and mac-latin2
    data = "Příliš žluťoučký kůň úpěl ďábelské ódy.".encode("iso-8859-2")
    result = run_pipeline(data, EncodingEra.ALL)
    # With MODERN_WEB era preference and close scores, iso-8859-2 should win
    # over mac-latin2 (which is LEGACY_MAC era)
    if result[0].encoding == "mac-latin2":
        # This test documents the problem; should be fixed by era tiebreaking
        assert False, f"Expected iso-8859-2 or windows-1250, got {result[0].encoding}"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_era_tiebreak.py -v`
Expected: Likely FAIL (mac-latin2 wins currently).

**Step 3: Add era priority to EncodingEra**

In `src/chardet/enums.py`, add a mapping for era priority order. This can be a module-level dict — no need to modify the enum class itself:

```python
# Priority order for tiebreaking: lower number = higher priority.
ERA_PRIORITY: dict[EncodingEra, int] = {
    EncodingEra.MODERN_WEB: 0,
    EncodingEra.LEGACY_ISO: 1,
    EncodingEra.LEGACY_REGIONAL: 2,
    EncodingEra.DOS: 3,
    EncodingEra.LEGACY_MAC: 4,
    EncodingEra.MAINFRAME: 5,
}
```

**Step 4: Implement tiebreaking in orchestrator.py**

Add a helper function and call it on Stage 3 results. Import `ERA_PRIORITY` from enums and look up each candidate's era from the registry.

```python
from chardet.enums import ERA_PRIORITY, EncodingEra

_TIEBREAK_MARGIN = 0.10  # 10% relative margin

def _apply_era_tiebreak(
    results: list[DetectionResult],
    candidates: tuple[EncodingInfo, ...],
    encoding_era: EncodingEra,
) -> list[DetectionResult]:
    """Reorder results to prefer encodings from the requested era when scores are close."""
    if len(results) < 2:
        return results

    # Build name -> era lookup
    era_lookup = {enc.name: enc.era for enc in candidates}

    best_conf = results[0].confidence
    if best_conf <= 0:
        return results

    # Find the threshold for "close" scores
    threshold = best_conf * (1 - _TIEBREAK_MARGIN)

    # Among top candidates within the margin, find the one with the best era priority
    best_idx = 0
    best_priority = ERA_PRIORITY.get(era_lookup.get(results[0].encoding, EncodingEra.ALL), 99)

    for i, r in enumerate(results[1:], 1):
        if r.confidence < threshold:
            break
        era = era_lookup.get(r.encoding, EncodingEra.ALL)
        priority = ERA_PRIORITY.get(era, 99)
        if priority < best_priority:
            best_priority = priority
            best_idx = i

    if best_idx != 0:
        # Swap the best-era candidate to position 0
        results = list(results)
        results[0], results[best_idx] = results[best_idx], results[0]

    return results
```

Call `_apply_era_tiebreak` on the results from Stage 3 (line 112) and also on the structural+single-byte results (line 108), before returning.

**Step 5: Run tests**

Run: `uv run pytest tests/test_era_tiebreak.py tests/test_orchestrator.py -v`
Expected: PASS.

**Step 6: Run full test suite and diagnostics**

Run: `uv run pytest tests/ --deselect tests/test_benchmark.py -v`
Run: `uv run python scripts/diagnose_accuracy.py`
Expected: Improvement in mac-latin2 → iso-8859-2 corrections. Note the new accuracy.

**Step 7: Update accuracy threshold**

Raise `_MIN_OVERALL_ACCURACY` in `tests/test_accuracy.py` to lock in gains.

**Step 8: Commit**

```bash
git add src/chardet/pipeline/orchestrator.py src/chardet/enums.py tests/test_era_tiebreak.py tests/test_accuracy.py
git commit -m "feat: add era-based tiebreaking for close statistical scores"
```

---

### Task 5: Improve training — koi8-r/koi8-u Cyrillic discrimination

Update the training script so koi8-r is trained only on Russian text (no Ukrainian) and koi8-u only on Ukrainian text. This creates distinct bigram models that can discriminate between the two similar encodings.

**Files:**
- Modify: `scripts/train.py` (line 73 and line 79)

**Step 1: Update the ENCODING_LANG_MAP in train.py**

Change koi8-r from training on `["ru", "bg", "uk", "sr", "mk", "be"]` to `["ru"]` only:

```python
    "koi8-r": ["ru"],
```

Keep koi8-u as `["uk"]` (already correct).

Also update cp866 to remove Ukrainian and add it to cp1125:

```python
    "cp866": ["ru", "bg", "sr", "mk", "be"],
```

(cp1125 is already `["uk"]` — that's correct.)

**Step 2: Retrain models**

Run: `uv run python scripts/train.py --max-samples 15000`
Expected: Training completes successfully. koi8-r model should now have distinct patterns from koi8-u.

Note: This step takes significant time (minutes to hours depending on download speed).

**Step 3: Run accuracy diagnostics**

Run: `uv run python scripts/diagnose_accuracy.py`
Expected: koi8-r accuracy should improve (currently 69.2%, should approach 90%+).

**Step 4: Run full test suite**

Run: `uv run pytest tests/ --deselect tests/test_benchmark.py -v`
Expected: All pass.

**Step 5: Update accuracy threshold**

Raise `_MIN_OVERALL_ACCURACY` in `tests/test_accuracy.py` to lock in gains.

**Step 6: Commit**

```bash
git add scripts/train.py src/chardet/models/models.bin tests/test_accuracy.py
git commit -m "feat: retrain koi8-r/cp866 on Russian-only to improve Cyrillic discrimination"
```

---

### Task 6: Update diagnostic scripts for directional equivalences

Update the diagnostic and comparison scripts to use the same directional equivalence logic as the test framework.

**Files:**
- Modify: `scripts/diagnose_accuracy.py`
- Modify: `scripts/compare_strict.py`
- Modify: `scripts/compare_detectors.py`

**Step 1: Update all three scripts**

Replace the `_EQUIVALENT_GROUPS` / `_ENCODING_EQUIVALENCES` / `_canonical_name()` pattern in each script with the same `_SUPERSETS` / `_BIDIRECTIONAL_GROUPS` / `_is_correct()` pattern from Task 1.

The key change in each script: wherever they compare `expected_canonical == detected_canonical`, replace with a call to `_is_correct(expected, detected)`.

**Step 2: Run each script to verify it works**

Run: `uv run python scripts/diagnose_accuracy.py`
Run: `uv run python scripts/compare_strict.py`
Expected: Both run without errors and produce updated accuracy numbers.

**Step 3: Commit**

```bash
git add scripts/diagnose_accuracy.py scripts/compare_strict.py scripts/compare_detectors.py
git commit -m "refactor: update diagnostic scripts to use directional equivalences"
```

---

### Task 7: Accuracy checkpoint — measure and assess

This is a measurement-only task. Run full diagnostics to see where we stand after Tasks 1-6.

**Step 1: Run the strict comparison**

Run: `uv run python scripts/compare_strict.py`
Expected: Our accuracy should be well above charset-normalizer's 76.0%.

**Step 2: Run the per-encoding diagnosis**

Run: `uv run python scripts/diagnose_accuracy.py`
Expected: Review per-encoding results. Identify any remaining problem areas.

**Step 3: Run full test suite**

Run: `uv run pytest tests/ --deselect tests/test_benchmark.py -v`
Expected: All pass.

**Step 4: Raise accuracy threshold to final value**

Set `_MIN_OVERALL_ACCURACY` in `tests/test_accuracy.py` to 1% below the measured accuracy to lock in all gains.

**Step 5: Commit**

```bash
git add tests/test_accuracy.py
git commit -m "test: raise accuracy threshold to reflect improvements"
```

---

### Task 8 (if needed): Additional training improvements

Only proceed with this task if the accuracy checkpoint (Task 7) shows we haven't exceeded 76.0%.

**8a. Train johab model:** Johab is already in `ENCODING_LANG_MAP` (line 47: `"johab": ["ko"]`). Verify the model exists in `models.bin` after training. If johab is being eliminated by CJK gating (Task 3), check that the gating threshold isn't too aggressive.

**8b. Improve Western European models:** Add more languages to iso-8859-1/windows-1252 training:

```python
    "iso-8859-1": ["fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms"],
    "windows-1252": ["fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms"],
```

**8c. Improve EBCDIC:** Narrow cp037 and cp500 to distinct language sets so their models differ where the byte mappings differ.

After any training changes, retrain and re-run diagnostics:

```bash
uv run python scripts/train.py --max-samples 15000
uv run python scripts/diagnose_accuracy.py
uv run pytest tests/ --deselect tests/test_benchmark.py -v
```

Commit: `git commit -m "feat: retrain models with improved language coverage"`
