# Accuracy Improvements v2 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve chardet-rewrite accuracy beyond 95.0% (2052/2161) through retraining with more data, training metadata tracking, a KOI8-T heuristic, and CJK false-positive gating.

**Architecture:** Four independent workstreams: (1) training infrastructure changes in `scripts/train.py`, (2) training metadata YAML output, (3) KOI8-T promotion heuristic in `orchestrator.py`, (4) lead-byte diversity CJK gating in `orchestrator.py` + `structural.py`.

**Tech Stack:** Python 3.10+, pytest, PyYAML (dev dependency for metadata writing), CulturaX via Hugging Face datasets.

---

### Task 1: Add stdout flushing to train.py

**Files:**
- Modify: `scripts/train.py:1` (add near top of file)

**Step 1: Add unbuffered stdout at the top of train.py**

After the imports (line 25, after `import unicodedata`), add:

```python
# Ensure progress output is visible when piped through tee.
import sys
import functools
print = functools.partial(print, flush=True)  # noqa: A001
```

**Step 2: Verify the script still runs**

Run: `uv run python scripts/train.py --help`
Expected: Help text prints without errors.

**Step 3: Commit**

```
feat: add stdout flushing to train.py for tee compatibility
```

---

### Task 2: Add training metadata YAML output to train.py

**Files:**
- Modify: `scripts/train.py` (after serialization, ~line 841)

**Step 1: Write the metadata generation code**

After the `serialize_models` call (line 841), before the summary print, add code to write `training_metadata.yaml`. Use the `yaml` module if available, otherwise write YAML manually since the structure is simple. Since this is a dev script, adding PyYAML as a dev dependency is fine but not required — manual YAML string formatting works for this flat structure.

Insert after line 841 (`file_size = serialize_models(models, args.output)`):

```python
    # Write training metadata alongside models.bin
    metadata_path = Path(args.output).with_name("training_metadata.yaml")
    _write_training_metadata(metadata_path, models, args.max_samples)
    print(f"Metadata written: {metadata_path}")
```

Add the `_write_training_metadata` function before `if __name__`:

```python
def _write_training_metadata(
    path: Path,
    models: dict[str, dict[tuple[int, int], int]],
    max_samples: int,
) -> None:
    """Write training metadata as YAML alongside models.bin."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"training_date: \"{now}\"",
        f"max_samples: {max_samples}",
        "models:",
    ]
    for model_key in sorted(models):
        parts = model_key.split("/", 1)
        lang = parts[0] if len(parts) == 2 else "unknown"
        enc = parts[1] if len(parts) == 2 else model_key
        num_bigrams = len(models[model_key])
        # Count actual samples used — retrieve from cached texts
        samples = len(get_texts(lang, max_samples, _DEFAULT_CACHE_DIR))
        lines.append(f"  {model_key}:")
        lines.append(f"    language: {lang}")
        lines.append(f"    encoding: {enc}")
        lines.append(f"    samples_used: {samples}")
        lines.append(f"    bigram_entries: {num_bigrams}")
        lines.append(f"    source: culturax")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

Also add `from pathlib import Path` to the imports at the top, and store the cache dir as a module-level variable or pass it through. The simplest approach: reference `args.cache_dir` via closure, or make `_DEFAULT_CACHE_DIR` a constant. Check how `args.cache_dir` is currently defined — it's at line 673-677 of train.py. The function should accept the cache dir as a parameter:

```python
def _write_training_metadata(
    path: Path,
    models: dict[str, dict[tuple[int, int], int]],
    max_samples: int,
    cache_dir: str,
) -> None:
```

And call it as:

```python
    _write_training_metadata(metadata_path, models, args.max_samples, args.cache_dir)
```

**Step 2: Verify metadata is generated**

Run: `uv run python scripts/train.py --max-samples 100 --encodings koi8-t`
Expected: `src/chardet/models/training_metadata.yaml` is created with YAML content including `tg/koi8-t` model entry.

**Step 3: Verify YAML is well-formed**

Run: `uv run python -c "import yaml; print(yaml.safe_load(open('src/chardet/models/training_metadata.yaml'))['models']['tg/koi8-t'])"`
Expected: Prints the model dict for tg/koi8-t.

**Step 4: Commit**

```
feat: write training metadata YAML alongside models.bin
```

---

### Task 3: Bump max_samples default to 25000

**Files:**
- Modify: `scripts/train.py:689`

**Step 1: Change the default**

At line 689, change:
```python
        default=1000,
```
to:
```python
        default=25000,
```

Also update the docstring at line 9 to reflect the new default:
```python
    uv run python scripts/train.py --max-samples 25000
```

**Step 2: Commit the default change (before retraining)**

```
feat: bump max_samples default to 25000 for better model quality
```

---

### Task 4: Retrain all models at 25K samples

**Step 1: Run training**

Run: `uv run python scripts/train.py 2>&1 | tee training_output.txt`

This will:
- Download ~3 GB of additional CulturaX data (10K more per language)
- Retrain all 233 models
- Write `models.bin` and `training_metadata.yaml`

Expected: Training completes without errors. May take 15-30 minutes depending on network and CPU.

**Step 2: Verify models.bin was updated**

Run: `ls -la src/chardet/models/models.bin src/chardet/models/training_metadata.yaml`
Expected: Both files exist with recent timestamps. models.bin should be roughly the same size (700-800 KB).

**Step 3: Run accuracy tests**

Run: `uv run pytest tests/test_accuracy.py -q 2>&1 | tail -5`
Expected: Some improvement over 2052/2161 (95.0%). Record exact numbers.

**Step 4: Run full comparison**

Run: `uv run python scripts/compare_detectors.py 2>&1 | tee latest_comparison.txt`
Expected: Updated accuracy numbers for chardet-rewrite.

**Step 5: Commit retrained models and metadata**

```
feat: retrain all bigram models at 25K samples/language

Previous models used 15K samples. Bumping to 25K for improved accuracy
on underrepresented encodings.
```

---

### Task 5: KOI8-T promotion heuristic

**Files:**
- Modify: `src/chardet/pipeline/orchestrator.py`
- Test: `tests/test_accuracy.py` (existing — verify KOI8-T passes)

**Step 1: Write a test for KOI8-T promotion**

Create a focused test that verifies KOI8-T detection. Add to a new file:

Create: `tests/test_koi8t.py`

```python
"""Test KOI8-T detection heuristic."""
from __future__ import annotations

import chardet
from chardet.enums import EncodingEra


def test_koi8t_with_tajik_bytes() -> None:
    """Data with Tajik-specific bytes should detect as KOI8-T, not KOI8-R."""
    # Read an actual KOI8-T test file
    from pathlib import Path
    test_dir = Path("tests/data/koi8-t-tajik")
    if not test_dir.exists():
        import pytest
        pytest.skip("KOI8-T test data not available")
    test_file = next(test_dir.iterdir())
    data = test_file.read_bytes()
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    assert result["encoding"] == "koi8-t", (
        f"Expected koi8-t but got {result['encoding']} "
        f"(confidence={result['confidence']:.2f})"
    )


def test_russian_text_stays_koi8r() -> None:
    """Pure Russian KOI8 text (no Tajik bytes) should remain KOI8-R."""
    from pathlib import Path
    test_dir = Path("tests/data/koi8-r-russian")
    if not test_dir.exists():
        import pytest
        pytest.skip("KOI8-R test data not available")
    test_file = next(test_dir.iterdir())
    data = test_file.read_bytes()
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    # Should not be koi8-t
    assert result["encoding"] != "koi8-t", (
        f"Russian text should not detect as koi8-t"
    )
```

**Step 2: Run to verify the KOI8-T test fails**

Run: `uv run pytest tests/test_koi8t.py::test_koi8t_with_tajik_bytes -v`
Expected: FAIL (currently detects as koi8-r).

**Step 3: Implement the KOI8-T promotion heuristic**

In `src/chardet/pipeline/orchestrator.py`, add the discriminating bytes constant after the existing `_DEMOTION_CANDIDATES` dict (after line 158):

```python
# Bytes where KOI8-T maps to Tajik-specific Cyrillic letters but KOI8-R
# maps to box-drawing characters.  Presence of any of these bytes is strong
# evidence for KOI8-T over KOI8-R.
_KOI8_T_DISTINGUISHING: frozenset[int] = frozenset(
    {0x80, 0x81, 0x83, 0x8A, 0x8C, 0x8D, 0x8E, 0x90, 0xA1, 0xA2, 0xA5, 0xB5}
)
```

Add a promotion function after `_demote_niche_latin`:

```python
def _promote_koi8t(
    data: bytes,
    results: list[DetectionResult],
) -> list[DetectionResult]:
    """Promote KOI8-T over KOI8-R when Tajik-specific bytes are present.

    KOI8-T and KOI8-R share the entire 0xC0-0xFF Cyrillic letter block,
    making statistical discrimination difficult.  However, KOI8-T maps 12
    bytes in 0x80-0xBF to Tajik-specific Cyrillic letters where KOI8-R has
    box-drawing characters.  If any of these bytes appear, KOI8-T is the
    better match.
    """
    if not results or results[0].encoding != "koi8-r":
        return results
    # Check if KOI8-T is anywhere in the results
    koi8t_idx = None
    for i, r in enumerate(results):
        if r.encoding == "koi8-t":
            koi8t_idx = i
            break
    if koi8t_idx is None:
        return results
    # Check for Tajik-specific bytes
    if any(b in _KOI8_T_DISTINGUISHING for b in data if b > 0x7F):
        koi8t_result = results[koi8t_idx]
        others = [r for i, r in enumerate(results) if i != koi8t_idx]
        return [koi8t_result, *others]
    return results
```

Wire it into `run_pipeline` at line 388 — change:

```python
    return _demote_niche_latin(data, results)
```

to:

```python
    results = _demote_niche_latin(data, results)
    return _promote_koi8t(data, results)
```

**Step 4: Run the KOI8-T test**

Run: `uv run pytest tests/test_koi8t.py -v`
Expected: Both tests PASS.

**Step 5: Run full accuracy tests to verify no regressions**

Run: `uv run pytest tests/test_accuracy.py -q 2>&1 | tail -5`
Expected: KOI8-T files now pass. Overall accuracy should improve by 3 (2052 + 3 = 2055 or better if retraining already helped).

**Step 6: Commit**

```
feat: add KOI8-T promotion heuristic for Tajik text detection

KOI8-T and KOI8-R share the Cyrillic 0xC0-0xFF block identically.
When Tajik-specific bytes (0x80-0xB5 range) are present — mapping to
Tajik Cyrillic letters in KOI8-T but box-drawing chars in KOI8-R —
promote KOI8-T to the top result.
```

---

### Task 6: CJK lead byte diversity gating

**Files:**
- Modify: `src/chardet/pipeline/structural.py` (add diversity counting)
- Modify: `src/chardet/pipeline/orchestrator.py:195-235` (add 4th gating check)
- Test: existing accuracy tests + a new focused test

**Step 1: Write a focused test for CJK false positives**

Create: `tests/test_cjk_gating.py`

```python
"""Test CJK false-positive gating rejects European single-byte data."""
from __future__ import annotations

import chardet
from chardet.enums import EncodingEra


def test_european_not_detected_as_cjk() -> None:
    """Single-byte European text must not be detected as a CJK encoding."""
    cjk_encodings = {"johab", "cp932", "shift_jis", "euc-jp", "euc-kr",
                     "cp949", "gb18030", "big5", "hz-gb-2312",
                     "iso-2022-jp", "iso-2022-kr"}
    # German mac-roman text that was falsely detected as cp932
    from pathlib import Path
    test_file = Path("tests/data/macroman-german/culturax_mC4_83756.txt")
    if not test_file.exists():
        import pytest
        pytest.skip("Test data not available")
    data = test_file.read_bytes()
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    assert result["encoding"] not in cjk_encodings, (
        f"European text falsely detected as {result['encoding']}"
    )
```

**Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_cjk_gating.py -v`
Expected: FAIL (currently detects as cp932).

**Step 3: Add lead byte diversity counting to structural.py**

Add a new public function to `src/chardet/pipeline/structural.py`, after `compute_multibyte_byte_coverage` (after line ~530):

```python
def compute_lead_byte_diversity(data: bytes, encoding_info: EncodingInfo) -> int:
    """Count distinct lead byte values in valid multi-byte pairs.

    Genuine CJK text uses lead bytes from across the encoding's full
    repertoire.  European text falsely matching a CJK structural scorer
    clusters lead bytes in a narrow band (e.g. 0xC0-0xDF for accented
    Latin characters).
    """
    if not data or not encoding_info.is_multibyte:
        return 0
    counter = _LEAD_BYTE_DIVERSITY_COUNTERS.get(encoding_info.name)
    if counter is None:
        return 256  # Unknown encoding — don't gate
    return counter(data)
```

Add per-encoding diversity counters. These are similar to the existing `_score_*` functions but return a set size. The simplest approach: write generic counters that reuse the same lead/trail byte ranges. For example, for Shift-JIS/cp932:

```python
def _lead_diversity_shift_jis(data: bytes) -> int:
    """Count distinct lead bytes in valid Shift-JIS pairs."""
    leads: set[int] = set()
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC):
            if i + 1 < length:
                trail = data[i + 1]
                if (0x40 <= trail <= 0x7E) or (0x80 <= trail <= 0xFC):
                    leads.add(b)
                    i += 2
                    continue
            i += 1
        else:
            i += 1
    return len(leads)
```

Write similar functions for each CJK encoding (johab, euc-kr/cp949, gb18030, big5, euc-jp). The lead/trail ranges are already documented in the existing `_score_*` functions — reuse the same ranges.

Add a dispatch table:

```python
_LEAD_BYTE_DIVERSITY_COUNTERS: dict[str, Callable[[bytes], int]] = {
    "shift_jis": _lead_diversity_shift_jis,
    "cp932": _lead_diversity_shift_jis,
    "euc-jp": _lead_diversity_euc_jp,
    "euc-kr": _lead_diversity_euc_kr,
    "cp949": _lead_diversity_euc_kr,
    "gb18030": _lead_diversity_gb18030,
    "big5": _lead_diversity_big5,
    "johab": _lead_diversity_johab,
}
```

**Step 4: Wire the diversity check into CJK gating**

In `src/chardet/pipeline/orchestrator.py`, import the new function:

```python
from chardet.pipeline.structural import (
    compute_lead_byte_diversity,
    compute_multibyte_byte_coverage,
    compute_structural_score,
)
```

Add a constant for the minimum diversity threshold (start conservative — tune empirically):

```python
# Minimum number of distinct lead byte values for a CJK candidate to
# survive gating.  Genuine CJK text uses a wide range of lead bytes;
# European false positives cluster in a narrow band.
_CJK_MIN_LEAD_DIVERSITY = 4
```

In `_gate_cjk_candidates` (line 232), after the byte coverage check, add:

```python
            lead_diversity = compute_lead_byte_diversity(data, enc)
            if lead_diversity < _CJK_MIN_LEAD_DIVERSITY:
                continue  # Too few distinct lead bytes -> not CJK
```

**Step 5: Empirically tune the threshold**

Before committing, verify the threshold doesn't reject genuine CJK files:

Run: `uv run pytest tests/test_accuracy.py -k "euc-jp or euc-kr or cp949 or big5 or gb18030 or shift_jis or cp932 or johab" -q 2>&1 | tail -5`
Expected: All CJK tests still pass. If any fail, lower `_CJK_MIN_LEAD_DIVERSITY`.

Then verify the false positives are fixed:

Run: `uv run pytest tests/test_cjk_gating.py -v`
Expected: PASS.

**Step 6: Run full accuracy tests**

Run: `uv run pytest tests/test_accuracy.py -q 2>&1 | tail -5`
Expected: Improvement from eliminated CJK false positives (~7 more passes).

**Step 7: Commit**

```
feat: add lead byte diversity check to CJK false-positive gating

European single-byte text with scattered accented characters can
accidentally form valid CJK multibyte pairs. Add a fourth gating
check: reject CJK candidates when the number of distinct lead byte
values is below a threshold, since genuine CJK text draws from a
wide repertoire of lead bytes.
```

---

### Task 7: Final accuracy measurement and comparison

**Step 1: Run full accuracy test suite**

Run: `uv run pytest tests/test_accuracy.py -q 2>&1 | tail -10`
Record: total passed / total tests.

**Step 2: Run comparison script**

Run: `uv run python scripts/compare_detectors.py 2>&1 | tee latest_comparison.txt`
Record: accuracy percentages for all detectors.

**Step 3: Update performance report if accuracy improved**

If accuracy improved, update `docs/performance.md` with new numbers.

**Step 4: Commit any report updates**

```
docs: update performance report with accuracy improvements v2 results
```

---

### Task 8: Decide on further max_samples increase

Based on Task 7 results, decide whether to bump `max_samples` higher.

**Decision criteria:**
- If 25K showed meaningful improvement over 15K → consider 50K
- If 25K showed marginal or no improvement → stop here
- Check if KOI8-T specifically improved from retraining alone

If proceeding with 50K:
- Run: `uv run python scripts/train.py --max-samples 50000 2>&1 | tee training_50k.txt`
- Repeat accuracy measurement (Task 7 steps)
- Commit if improved
