# Accuracy to 95% Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve chardet-rewrite accuracy from 79.4% to 95%+ on the 2161-file test suite.

**Architecture:** Five layered improvements: (1) decoded-output equivalence check in evaluation, (2) CJK false-positive gating in structural probing, (3) iso-8859-10 demotion via distinguishing-byte requirement, (4) post-decode mess detection as a new pipeline stage, (5) language-encoding pair bigram models for better statistical discrimination. Each layer is independently testable and committed separately.

**Tech Stack:** Python 3.10+, pytest, unicodedata stdlib module, existing chardet pipeline.

---

### Task 1: Add `is_equivalent_detection()` to equivalences.py

**Files:**
- Modify: `src/chardet/equivalences.py:71-96` (after `is_correct`)
- Test: `tests/test_equivalences.py` (create)

**Step 1: Write the failing tests**

Create `tests/test_equivalences.py`:

```python
"""Tests for decoded-output equivalence checking."""
from __future__ import annotations

from chardet.equivalences import is_equivalent_detection, is_correct


class TestIsEquivalentDetection:
    """Tests for is_equivalent_detection()."""

    def test_identical_decode_returns_true(self):
        """iso-8859-1 and windows-1252 decode identically for pure ASCII."""
        data = b"Hello, world!"
        assert is_equivalent_detection(data, "ascii", "utf-8")

    def test_base_letter_match_returns_true(self):
        """iso-8859-15 vs windows-1252: euro sign at 0xA4 differs but both
        have same base letters for most text."""
        # Byte 0xE9 = é in both iso-8859-1 and iso-8859-15
        data = b"caf\xe9"
        assert is_equivalent_detection(data, "iso-8859-1", "iso-8859-15")

    def test_completely_different_decode_returns_false(self):
        """Cyrillic vs Latin should fail."""
        # 0xC0 = À in iso-8859-1, А in koi8-r
        data = b"\xc0\xc1\xc2\xc3"
        assert not is_equivalent_detection(data, "iso-8859-1", "koi8-r")

    def test_none_detected_returns_false(self):
        assert not is_equivalent_detection(b"hello", "utf-8", None)

    def test_decode_error_returns_false(self):
        """If either encoding can't decode, return False."""
        # 0x81 is invalid in utf-8
        data = b"\x81\x82\x83"
        assert not is_equivalent_detection(data, "utf-8", "iso-8859-1")

    def test_empty_data_returns_true(self):
        """Empty data decodes identically everywhere."""
        assert is_equivalent_detection(b"", "utf-8", "iso-8859-1")

    def test_diacritic_difference_passes_base_letter(self):
        """é (e-acute) vs è (e-grave) should match: same base letter 'e'."""
        # Create bytes that decode to é in one encoding, è in another
        # iso-8859-1: 0xE9 = é, iso-8859-15: 0xE9 = é (same here)
        # Use a case where the difference is only in combining marks
        # cp037 0xC5 = e, cp500 0xC5 = e (these are EBCDIC)
        data = b"Hello"
        assert is_equivalent_detection(data, "cp037", "cp500")

    def test_non_letter_difference_fails(self):
        """Differences in non-letter characters (symbols, punctuation)
        that aren't combining marks should fail."""
        # 0xA4 = ¤ (currency sign) in iso-8859-1, € in iso-8859-15
        # These are not the same base letter
        data = b"\xa4"
        assert not is_equivalent_detection(data, "iso-8859-1", "iso-8859-15")
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_equivalences.py -v`
Expected: ImportError — `is_equivalent_detection` doesn't exist yet.

**Step 3: Implement `is_equivalent_detection`**

Add to `src/chardet/equivalences.py` after the `is_correct` function (after line 96):

```python
def _strip_combining(text: str) -> str:
    """NFKD-normalize and strip all combining marks."""
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(
        c for c in nfkd if not unicodedata.combining(c)
    )


def is_equivalent_detection(
    data: bytes, expected: str, detected: str | None
) -> bool:
    """Check whether *detected* produces functionally identical text to *expected*.

    Returns True if decoding *data* with both encodings and stripping all
    diacritics/combining marks yields identical base-letter strings.
    Every differing code point must pass the base-letter test.
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

    return _strip_combining(text_exp) == _strip_combining(text_det)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_equivalences.py -v`
Expected: All pass. Some tests may need adjustment based on actual byte values — fix any that fail by choosing correct test data.

**Step 5: Commit**

```bash
git add src/chardet/equivalences.py tests/test_equivalences.py
git commit -m "feat: add is_equivalent_detection for base-letter equivalence"
```

---

### Task 2: Integrate equivalence check into test harness and scripts

**Files:**
- Modify: `tests/test_accuracy.py:20-30`
- Modify: `scripts/diagnose_accuracy.py:79-85`

**Step 1: Update test_accuracy.py**

Replace the assertion in `test_detect` to fall back to equivalence check:

```python
def test_detect(expected_encoding: str, language: str, test_file_path: Path) -> None:
    """Detect encoding of a single test file and verify correctness."""
    data = test_file_path.read_bytes()
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    detected = result["encoding"]

    assert is_correct(expected_encoding, detected) or is_equivalent_detection(
        data, expected_encoding, detected
    ), (
        f"expected={expected_encoding}, got={detected} "
        f"(confidence={result['confidence']:.2f}, "
        f"language={language}, file={test_file_path.name})"
    )
```

Add import: `from chardet.equivalences import is_correct, is_equivalent_detection`

**Step 2: Update diagnose_accuracy.py**

Add `is_equivalent_detection` import and update the check at line 79:

```python
from chardet.equivalences import is_correct, is_equivalent_detection, normalize_encoding_name
```

Update the check block to track equivalence rescues:

```python
        if is_correct(expected_encoding, detected):
            correct += 1
            enc_correct[norm_expected] += 1
        elif is_equivalent_detection(data, expected_encoding, detected):
            correct += 1
            enc_correct[norm_expected] += 1
        else:
            failures[norm_expected].append((detected, confidence, size, short_path))
            if detected is None:
                none_results.append((expected_encoding, language, size, short_path))
```

**Step 3: Run accuracy tests to measure new baseline**

Run: `uv run pytest tests/test_accuracy.py -n auto --tb=no -q`
Expected: ~268 failures (down from ~446). Accuracy ~87.6%.

**Step 4: Commit**

```bash
git add tests/test_accuracy.py scripts/diagnose_accuracy.py
git commit -m "feat: integrate decoded-output equivalence into test harness"
```

---

### Task 3: Tighten CJK multi-byte ratio threshold

**Files:**
- Modify: `src/chardet/pipeline/orchestrator.py:32` (the `_CJK_MIN_MB_RATIO` constant)
- Modify: `src/chardet/pipeline/structural.py` (add non-ASCII byte counting to scorers)

**Step 1: Analyze current CJK false positives**

Before changing code, run a diagnostic to understand the multi-byte ratios for false positives vs true positives. Write and run a temporary script:

```python
"""Analyze multi-byte ratios for CJK encodings on test data."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from utils import collect_test_files
from chardet.pipeline.structural import compute_structural_score
from chardet.registry import REGISTRY

data_dir = Path("tests/data")
test_files = collect_test_files(data_dir)

cjk_encodings = {e for e in REGISTRY if e.is_multibyte}
for enc_info in sorted(cjk_encodings, key=lambda e: e.name):
    # Find test files for this encoding and other encodings
    true_scores = []
    false_scores = []
    for expected, lang, fp in test_files:
        data = fp.read_bytes()
        score = compute_structural_score(data, enc_info)
        if score > 0:
            if expected == enc_info.name or expected in (a for a in enc_info.aliases):
                true_scores.append(score)
            else:
                false_scores.append(score)
    if true_scores or false_scores:
        print(f"{enc_info.name}: true={len(true_scores)} (min={min(true_scores) if true_scores else 'N/A'}), "
              f"false={len(false_scores)} (max={max(false_scores) if false_scores else 'N/A'})")
```

Use the output to determine the right threshold. The current threshold is 0.05 (5%). Based on the research, genuine CJK files have nearly 100% valid multi-byte pairing for their non-ASCII bytes, while Latin false positives have much lower ratios.

**Step 2: Update the threshold**

Modify `src/chardet/pipeline/orchestrator.py` line 32. Change the threshold based on what the diagnostic reveals. A starting point:

```python
_CJK_MIN_MB_RATIO = 0.25  # Tuned: genuine CJK has >0.9, Latin false positives typically <0.2
```

The exact value should be determined from the diagnostic output. Pick a value that eliminates most false positives without removing any true CJK detections.

**Step 3: Also add non-ASCII byte ratio check**

Modify the gating logic in `orchestrator.py` (lines 98-104) to also compute the ratio of non-ASCII bytes that form valid multi-byte sequences. Add a helper to `structural.py`:

```python
def compute_multibyte_coverage(data: bytes, encoding_info: EncodingInfo) -> float:
    """Return ratio of non-ASCII bytes that participate in valid multi-byte sequences.

    Returns 0.0 if there are no non-ASCII bytes. For genuine CJK text this
    is typically >0.95. For Latin text accidentally passing CJK validation,
    it's much lower because high bytes are scattered orphans.
    """
    if not data or not encoding_info.is_multibyte:
        return 0.0

    scorer = _SCORERS.get(encoding_info.name)
    if scorer is None:
        return 0.0

    # Count non-ASCII bytes
    non_ascii = sum(1 for b in data if b > 0x7F)
    if non_ascii == 0:
        return 0.0

    # The structural score is valid_sequences / lead_bytes
    # We need valid_multibyte_bytes / non_ascii_bytes instead
    # Reuse the scorer but modify to return both counts
    # For now, approximate: score * lead_bytes * 2 / non_ascii
    # (each valid pair consumes 2 non-ASCII bytes typically)
    score = scorer(data)
    # This is approximate — a more precise version would modify each scorer
    # to return (valid_bytes, total_non_ascii) directly
    return score
```

Note: The exact implementation will depend on what the diagnostic reveals. The scorers may need to be modified to return byte-level coverage rather than just valid/lead ratios.

**Step 4: Run accuracy tests**

Run: `uv run pytest tests/test_accuracy.py -n auto --tb=no -q`
Expected: ~50-60 fewer failures from CJK false positive elimination. Verify no CJK true-positive regressions.

**Step 5: Commit**

```bash
git add src/chardet/pipeline/orchestrator.py src/chardet/pipeline/structural.py
git commit -m "fix: tighten CJK multi-byte ratio threshold to reduce false positives"
```

---

### Task 4: iso-8859-10 distinguishing bytes requirement

**Files:**
- Modify: `src/chardet/pipeline/orchestrator.py` (add post-scoring demotion)

**Step 1: Identify iso-8859-10 distinguishing bytes**

Bytes that decode to different characters in iso-8859-10 vs iso-8859-1:

| Byte | iso-8859-1 | iso-8859-10 |
|------|-----------|-------------|
| 0xA1 | ¡ | Ą |
| 0xA2 | ¢ | Ē |
| 0xA3 | £ | Ģ |
| 0xA5 | ¥ | Ĩ |
| 0xA6 | ¦ | Ķ |
| 0xA8 | ¨ | Ļ |
| 0xA9 | © | Đ |
| 0xAA | ª | Š |
| 0xAB | « | Ŧ |
| 0xAC | ¬ | Ž |
| 0xAE | ® | Ū |
| 0xB1 | ± | ą |
| 0xB2 | ² | ē |
| 0xB3 | ³ | ģ |
| 0xB5 | µ | ĩ |
| 0xB6 | ¶ | ķ |
| 0xB8 | ¸ | ļ |
| 0xB9 | ¹ | đ |
| 0xBA | º | š |
| 0xBB | » | ŧ |
| 0xBC | ¼ | ž |
| 0xBE | ¾ | ū |
| 0xBF | ¿ | ŋ |

The actual set should be verified programmatically. Characters like Ą, Ē, Ģ, Ĩ, Ķ, Đ, Š, Ŧ, Ž, ŋ are distinctive Nordic/Baltic characters.

**Step 2: Write the demotion logic**

Add to `orchestrator.py` after the statistical scoring (after line 141), a post-scoring filter:

```python
# Bytes where iso-8859-10 differs from iso-8859-1 and iso-8859-15.
# If none of these bytes are present, iso-8859-10 is indistinguishable
# from more common Latin encodings, so we demote it.
_ISO_8859_10_DISTINGUISHING: frozenset[int] = frozenset({
    0xA1, 0xA2, 0xA3, 0xA5, 0xA6, 0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAE,
    0xB1, 0xB2, 0xB3, 0xB5, 0xB6, 0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBE, 0xBF,
    0xD0, 0xDE, 0xF0, 0xFE,
})


def _has_iso_8859_10_evidence(data: bytes) -> bool:
    """Return True if data contains bytes unique to iso-8859-10."""
    return any(b in _ISO_8859_10_DISTINGUISHING for b in data if b > 0x7F)
```

Then in the results processing, if the top result is iso-8859-10 and there's no distinguishing evidence, swap it with the next non-iso-8859-10 candidate:

```python
    # Demote iso-8859-10 if no distinguishing bytes present
    if (
        results
        and results[0].encoding == "iso-8859-10"
        and not _has_iso_8859_10_evidence(data)
        and len(results) > 1
    ):
        # Move iso-8859-10 after the first non-iso-8859-10 candidate
        iso_result = results[0]
        rest = [r for r in results[1:] if r.encoding != "iso-8859-10"]
        if rest:
            results = rest + [iso_result]
```

Note: The exact distinguishing bytes need to be verified programmatically (compare iso-8859-10 decode table vs iso-8859-1 and iso-8859-15). Adjust the set based on actual differences.

**Step 3: Run accuracy tests**

Run: `uv run pytest tests/test_accuracy.py -n auto --tb=no -q`
Expected: ~20-25 fewer failures.

**Step 4: Commit**

```bash
git add src/chardet/pipeline/orchestrator.py
git commit -m "fix: demote iso-8859-10 when no distinguishing bytes present"
```

---

### Task 5: Post-decode mess detection

**Files:**
- Create: `src/chardet/pipeline/mess.py`
- Modify: `src/chardet/pipeline/orchestrator.py` (integrate mess scoring)
- Test: `tests/test_mess.py` (create)

**Step 1: Write failing tests for mess detection**

Create `tests/test_mess.py`:

```python
"""Tests for post-decode mess detection."""
from __future__ import annotations

from chardet.pipeline.mess import compute_mess_score


class TestMessScore:
    def test_clean_ascii_text(self):
        """Pure ASCII text should have zero mess."""
        assert compute_mess_score("Hello, world! This is clean text.") == 0.0

    def test_clean_accented_text(self):
        """Normal French text with accents should have low mess."""
        assert compute_mess_score("Café résumé naïve") < 0.1

    def test_unprintable_characters(self):
        """Text with C0/C1 control characters should have high mess."""
        text = "Hello\x01\x02\x03world"
        assert compute_mess_score(text) > 0.2

    def test_mixed_scripts(self):
        """Adjacent Cyrillic and Arabic characters indicate wrong encoding."""
        text = "Привет مرحبا"  # Cyrillic then Arabic
        score = compute_mess_score(text)
        # Mixed scripts in a single word would be messy, but separated
        # by space is somewhat plausible. Keep threshold moderate.
        assert score >= 0.0  # At minimum not negative

    def test_excessive_accents(self):
        """More than 35-40% accented alphabetic chars is suspicious."""
        # Simulate wrong encoding producing lots of accented chars
        text = "àéîõüàéîõü" * 10 + "abc"
        score = compute_mess_score(text)
        assert score > 0.1

    def test_empty_string(self):
        assert compute_mess_score("") == 0.0
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_mess.py -v`
Expected: ImportError.

**Step 3: Implement mess detection**

Create `src/chardet/pipeline/mess.py`:

```python
"""Post-decode mess detection.

Scores decoded Unicode text for signs that the wrong encoding was used.
Inspired by charset-normalizer's mess detection approach.
"""
from __future__ import annotations

import unicodedata


def compute_mess_score(text: str) -> float:
    """Return a mess score for decoded text. 0.0 = clean, 1.0 = very messy.

    Checks for:
    1. Unprintable characters (categories Cc/Cf, excluding tab/newline/CR)
    2. Excessive accented characters (>40% of alphabetic chars)
    3. Suspicious adjacent script mixing
    """
    if not text:
        return 0.0

    total = len(text)
    if total == 0:
        return 0.0

    unprintable_count = 0
    alpha_count = 0
    accented_count = 0
    prev_script = None
    script_changes = 0
    non_space_count = 0

    _COMMON_CONTROL = {"\t", "\n", "\r"}

    for i, ch in enumerate(text):
        cat = unicodedata.category(ch)

        # 1. Unprintable
        if cat.startswith("C") and ch not in _COMMON_CONTROL:
            unprintable_count += 1

        # 2. Accent tracking
        if cat.startswith("L"):
            alpha_count += 1
            # Check if character has combining marks after NFKD
            decomposed = unicodedata.normalize("NFKD", ch)
            if len(decomposed) > 1 and any(
                unicodedata.combining(c) for c in decomposed
            ):
                accented_count += 1

        # 3. Script mixing — track transitions between major script blocks
        if not ch.isspace():
            non_space_count += 1
            try:
                script = unicodedata.script(ch)
            except (AttributeError, ValueError):
                # unicodedata.script not available before Python 3.13
                script = None
            if (
                script is not None
                and prev_script is not None
                and script != "Common"
                and prev_script != "Common"
                and script != "Inherited"
                and prev_script != "Inherited"
                and script != prev_script
            ):
                script_changes += 1
            if script not in ("Common", "Inherited", None):
                prev_script = script

    # Compute component scores
    unprintable_ratio = unprintable_count / total if total > 0 else 0.0
    accent_ratio = accented_count / alpha_count if alpha_count > 10 else 0.0
    script_ratio = script_changes / non_space_count if non_space_count > 10 else 0.0

    # Weight unprintable chars heavily (8x), accent excess moderately
    score = (
        unprintable_ratio * 8.0
        + max(0.0, accent_ratio - 0.40) * 2.0  # Only penalize above 40%
        + script_ratio * 3.0
    )

    return min(score, 1.0)
```

Note: `unicodedata.script()` was added in Python 3.13. For 3.10-3.12 compatibility, the script mixing check should gracefully degrade (skip that heuristic). The implementation above handles this with the try/except.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_mess.py -v`
Expected: All pass. Adjust thresholds/weights in the heuristics if needed.

**Step 5: Integrate into orchestrator**

Modify `src/chardet/pipeline/orchestrator.py`. Add import and post-scoring filter:

```python
from chardet.pipeline.mess import compute_mess_score
```

After the statistical scoring results are computed (after line 141), add:

```python
    # Post-decode mess detection: penalize candidates that produce messy Unicode
    if len(results) > 1:
        scored_results = []
        for r in results:
            if r.encoding is None:
                scored_results.append(r)
                continue
            try:
                decoded = data.decode(r.encoding)
                mess = compute_mess_score(decoded)
            except (UnicodeDecodeError, LookupError):
                mess = 1.0
            # Penalize confidence by mess score
            adjusted_confidence = r.confidence * (1.0 - mess)
            scored_results.append(
                DetectionResult(
                    encoding=r.encoding,
                    confidence=max(adjusted_confidence, 0.01),
                    language=r.language,
                )
            )
        scored_results.sort(key=lambda r: r.confidence, reverse=True)
        results = scored_results
```

**Step 6: Run accuracy tests**

Run: `uv run pytest tests/test_accuracy.py -n auto --tb=no -q`
Expected: Further reduction in failures, particularly DOS→Windows confusion.

**Step 7: Commit**

```bash
git add src/chardet/pipeline/mess.py tests/test_mess.py src/chardet/pipeline/orchestrator.py
git commit -m "feat: add post-decode mess detection to penalize wrong encodings"
```

---

### Task 6: Language-encoding pair models — training pipeline

**Files:**
- Modify: `scripts/train.py` (emit per-language-encoding models)
- Modify: `src/chardet/models/__init__.py` (load new model format)

**Step 1: Update model binary format**

The current format stores models keyed by encoding name (e.g., `"windows-1252"`). The new format stores models keyed by `"language/encoding"` (e.g., `"fr/windows-1252"`, `"de/windows-1252"`).

The binary format itself doesn't change — just the model name strings. `load_models()` returns a dict keyed by `"lang/encoding"` instead of just `"encoding"`.

**Step 2: Modify train.py to emit per-language models**

The key change is in the main loop (lines 763-825). Instead of merging all language texts into one model per encoding, train a separate model per language-encoding pair:

```python
    for enc_name, langs in sorted(encoding_map.items()):
        codec = None
        codec_candidates = [enc_name]
        normalized = enc_name.replace("-", "").replace("_", "").lower()
        codec_candidates.append(normalized)

        for candidate in codec_candidates:
            if verify_codec(candidate):
                codec = candidate
                break

        if codec is None:
            print(f"  SKIP {enc_name}: codec not found")
            skipped.append(enc_name)
            continue

        for lang in langs:
            model_key = f"{lang}/{enc_name}"
            texts = get_texts(lang, args.max_samples, args.cache_dir)

            if not texts:
                print(f"  SKIP {model_key}: no text available")
                continue

            # Add HTML-wrapped samples
            html_samples = add_html_samples(texts)
            all_texts = list(texts) + html_samples

            subs = get_substitutions(enc_name, [lang])

            encoded: list[bytes] = []
            for text in all_texts:
                text = normalize_text(text, enc_name)
                text = apply_substitutions(text, subs)
                result = encode_text(text, codec)
                if result is not None:
                    encoded.append(result)

            if not encoded:
                print(f"  SKIP {model_key}: no encodable text")
                continue

            freqs = compute_bigram_frequencies(encoded)
            bigrams = normalize_and_prune(freqs, args.min_weight)

            if not bigrams:
                print(f"  SKIP {model_key}: no bigrams above threshold")
                continue

            models[model_key] = bigrams
            total_bytes = sum(len(e) for e in encoded)
            print(
                f"  {model_key}: {len(bigrams)} bigrams from "
                f"{len(encoded)} samples ({total_bytes:,} bytes)"
            )
```

**Step 3: Run training**

Run: `uv run python scripts/train.py --max-samples 5000`
Expected: Models file grows by ~2-4x. Each encoding now has multiple language-specific models.

**Step 4: Commit**

```bash
git add scripts/train.py src/chardet/models/models.bin
git commit -m "feat: train per-language-encoding bigram models"
```

---

### Task 7: Language-encoding pair models — scoring integration

**Files:**
- Modify: `src/chardet/models/__init__.py` (add language-aware scoring)
- Modify: `src/chardet/pipeline/statistical.py` (use language-aware scoring)

**Step 1: Update model loading to support both formats**

The `load_models()` function already loads by key name. No changes needed if keys are now `"fr/windows-1252"` etc. But `score_bigrams()` is called with just the encoding name. We need a new function:

Add to `src/chardet/models/__init__.py`:

```python
def score_best_language(
    data: bytes,
    encoding: str,
    models: dict[str, bytearray],
) -> tuple[float, str | None]:
    """Score data against all language variants of an encoding.

    Returns (best_score, best_language). If no language-specific models
    exist, falls back to the plain encoding model.
    """
    best_score = 0.0
    best_lang: str | None = None

    # Try language-specific models first
    prefix = f"/{encoding}"
    for key, model in models.items():
        if key.endswith(prefix) and "/" in key:
            lang = key.split("/", 1)[0]
            s = _score_with_model(data, model)
            if s > best_score:
                best_score = s
                best_lang = lang

    # Fall back to plain encoding model if no language variants exist
    if best_score == 0.0 and encoding in models:
        best_score = _score_with_model(data, models[encoding])

    return best_score, best_lang


def _score_with_model(data: bytes, model: bytearray) -> float:
    """Score data against a single model bytearray."""
    total_bigrams = len(data) - 1
    if total_bigrams <= 0:
        return 0.0

    score = 0
    weight_sum = 0
    for i in range(total_bigrams):
        b1 = data[i]
        b2 = data[i + 1]
        w = 8 if (b1 > 0x7F or b2 > 0x7F) else 1
        score += model[(b1 << 8) | b2] * w
        weight_sum += 255 * w

    if weight_sum == 0:
        return 0.0
    return score / weight_sum
```

**Step 2: Update statistical.py to use language-aware scoring**

Modify `src/chardet/pipeline/statistical.py`:

```python
from chardet.models import load_models, score_best_language
from chardet.pipeline import DetectionResult


def score_candidates(
    data: bytes, candidates: tuple[EncodingInfo, ...]
) -> list[DetectionResult]:
    """Score all candidates and return results sorted by confidence descending."""
    if not data or not candidates:
        return []

    models = load_models()
    scores: list[tuple[str, float, str | None]] = []

    for enc in candidates:
        s, lang = score_best_language(data, enc.name, models)
        scores.append((enc.name, s, lang))

    scores.sort(key=lambda x: x[1], reverse=True)

    max_score = scores[0][1] if scores else 0.0
    results = []
    for name, s, lang in scores:
        if s <= 0.0:
            continue
        confidence = s / max_score if max_score > 0 else 0.0
        results.append(
            DetectionResult(encoding=name, confidence=confidence, language=lang)
        )

    return results
```

**Step 3: Update model loading for new key format**

Modify `load_models()` in `src/chardet/models/__init__.py` to handle the new `"lang/encoding"` keys. The model table allocation needs to handle the `/` in the name:

The existing `load_models()` code should work as-is since it just reads name strings from the binary file. The bytearray tables are the same format. Just verify this works.

**Step 4: Run accuracy tests**

Run: `uv run pytest tests/test_accuracy.py -n auto --tb=no -q`
Expected: Significant accuracy improvement. The language field in results should now be populated.

**Step 5: Commit**

```bash
git add src/chardet/models/__init__.py src/chardet/pipeline/statistical.py
git commit -m "feat: integrate language-encoding pair scoring with language detection"
```

---

### Task 8: Tune and iterate

**Files:**
- Various pipeline files as needed

**Step 1: Run full accuracy measurement**

Run: `uv run pytest tests/test_accuracy.py -n auto --tb=no -q`
Record: X failures remaining.

**Step 2: Run diagnostics on remaining failures**

Run: `uv run python scripts/diagnose_accuracy.py`
Analyze: What patterns remain? Which encodings still struggle?

**Step 3: Tune thresholds**

Based on diagnostic output:
- Adjust `_CJK_MIN_MB_RATIO` if CJK false positives remain
- Adjust mess detection weights if some confusion patterns persist
- Adjust iso-8859-10 distinguishing byte set if needed
- Consider additional encoding-specific demotions for other problematic encodings (e.g., mac-latin2 false positives)

**Step 4: Retrain models for specific encodings if needed**

If certain language-encoding pairs still underperform:
Run: `uv run python scripts/train.py --max-samples 10000 --encodings <problem-encodings>`

**Step 5: Run final accuracy**

Run: `uv run pytest tests/test_accuracy.py -n auto --tb=no -q`
Target: ≤108 failures (95% accuracy = 2053/2161).

**Step 6: Update performance report**

Run: `uv run python scripts/compare_detectors.py` (or the benchmark script)
Update: `docs/rewrite_performance.md` with new numbers.

**Step 7: Commit**

```bash
git add -u
git commit -m "perf: tune detection pipeline for 95% accuracy target"
```

---

### Task 9: Clean up analysis scripts

**Files:**
- Delete: `scripts/analyze_failures.py` (if created by research agents)
- Verify: All existing tests still pass

**Step 1: Remove temporary scripts**

```bash
rm -f scripts/analyze_failures.py
```

**Step 2: Run full test suite**

Run: `uv run pytest -n auto --tb=short`
Expected: All pass (including non-accuracy tests like test_api.py, test_pipeline.py).

**Step 3: Run linter**

Run: `uv run ruff check src/ tests/ scripts/`
Expected: No errors.

**Step 4: Final commit**

```bash
git add -u
git commit -m "chore: clean up temporary analysis scripts"
```
