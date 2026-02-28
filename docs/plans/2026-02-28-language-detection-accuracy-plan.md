# Language Detection Accuracy Tracking — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Track language detection accuracy as a parallel, non-blocking metric alongside encoding accuracy in compare_detectors.py and test_accuracy.py.

**Architecture:** Extend benchmark_time.py's JSON protocol with a `detected_language` field. compare_detectors.py tracks language stats independently of encoding stats, adding overall accuracy, per-encoding language table, and language failures sections. test_accuracy.py emits `warnings.warn()` on language mismatches without failing tests.

**Tech Stack:** Python stdlib (warnings, json, argparse), pytest

---

### Task 1: Extend benchmark_time.py to output detected language

**Files:**
- Modify: `scripts/benchmark_time.py:85-124` (detect closures)
- Modify: `scripts/benchmark_time.py:128-145` (detection loop + JSON output)

**Step 1: Change detect() closures to return (encoding, language) tuples**

In `scripts/benchmark_time.py`, replace the four `detect()` closure definitions (lines 85-123) so they return `tuple[str | None, str | None]` instead of `str | None`:

```python
    # Import detector and build detect function — timed with perf_counter only
    if args.detector == "chardet" and args.encoding_era != "none":
        t0 = time.perf_counter()
        import chardet
        from chardet.enums import EncodingEra

        import_time = time.perf_counter() - t0
        era = EncodingEra.ALL if args.encoding_era == "all" else EncodingEra.MODERN_WEB

        def detect(data: bytes) -> tuple[str | None, str | None]:
            r = chardet.detect(data, encoding_era=era)
            return r["encoding"], r["language"]

    elif args.detector == "chardet":
        t0 = time.perf_counter()
        import chardet

        import_time = time.perf_counter() - t0

        def detect(data: bytes) -> tuple[str | None, str | None]:
            r = chardet.detect(data)
            return r["encoding"], r["language"]

    elif args.detector == "cchardet":
        t0 = time.perf_counter()
        import cchardet

        import_time = time.perf_counter() - t0

        def detect(data: bytes) -> tuple[str | None, str | None]:
            return cchardet.detect(data)["encoding"], None

    else:
        t0 = time.perf_counter()
        from charset_normalizer import from_bytes

        import_time = time.perf_counter() - t0

        def detect(data: bytes) -> tuple[str | None, str | None]:
            r = from_bytes(data)
            best = r.best()
            return (best.encoding if best else None), None
```

**Step 2: Update detection loop to unpack tuple and add detected_language to JSON**

Replace the detection loop (lines 128-145):

```python
    # Run detection over all files, collect per-file times + results
    file_times: list[float] = []
    t_total_start = time.perf_counter()
    for enc, lang, fp, data in all_data:
        ft0 = time.perf_counter()
        detected, detected_language = detect(data)
        file_elapsed = time.perf_counter() - ft0
        file_times.append(file_elapsed)

        if args.json_only:
            print(
                json.dumps(
                    {
                        "expected": enc,
                        "language": lang,
                        "path": str(fp),
                        "detected": detected,
                        "detected_language": detected_language,
                        "elapsed": file_elapsed,
                    }
                )
            )
    total_elapsed = time.perf_counter() - t_total_start
```

**Step 3: Run benchmark_time.py to verify JSON output includes detected_language**

Run: `uv run python scripts/benchmark_time.py --pure --json-only 2>/dev/null | head -3`

Expected: each JSON line now has a `"detected_language"` field (string or null).

**Step 4: Run benchmark_time.py human-readable mode to verify it still works**

Run: `uv run python scripts/benchmark_time.py --pure`

Expected: same output as before (human-readable mode doesn't show language).

**Step 5: Commit**

```
feat: add detected_language to benchmark_time.py JSON output
```

---

### Task 2: Extend compare_detectors.py to parse and track language accuracy

**Files:**
- Modify: `scripts/compare_detectors.py:106` (return type annotation)
- Modify: `scripts/compare_detectors.py:122-128` (docstring)
- Modify: `scripts/compare_detectors.py:153` (results list type)
- Modify: `scripts/compare_detectors.py:164-168` (JSON parsing)
- Modify: `scripts/compare_detectors.py:218-237` (`_record_result`)
- Modify: `scripts/compare_detectors.py:284-294` (stats initialization)
- Modify: `scripts/compare_detectors.py:312-313` (results unpacking loop)

**Step 1: Update `_run_timing_subprocess` return type and JSON parsing**

Change the return type annotation on line 106 from:
```python
) -> tuple[list[tuple[str, str, str, str | None]], float, list[float], float]:
```
to:
```python
) -> tuple[list[tuple[str, str, str, str | None, str | None]], float, list[float], float]:
```

Update the docstring (line 126) to note the 5th element:
```
        list of ``(expected_encoding, expected_language, filepath_str,
        detected_encoding, detected_language)`` tuples, ...
```

Change the results type on line 153 from:
```python
    results: list[tuple[str, str, str, str | None]] = []
```
to:
```python
    results: list[tuple[str, str, str, str | None, str | None]] = []
```

Change the append on lines 165-168 to include `detected_language`:
```python
            results.append(
                (
                    obj["expected"],
                    obj["language"],
                    obj["path"],
                    obj["detected"],
                    obj.get("detected_language"),
                )
            )
```

Note: use `obj.get("detected_language")` so that old chardet versions (< 6.0) whose benchmark_time.py doesn't emit this field gracefully return `None`.

**Step 2: Extend `_record_result` with language tracking**

Replace `_record_result` (lines 218-237) with:

```python
def _record_result(
    detector_stats: dict,
    expected_encoding: str,
    expected_language: str,
    filepath: Path,
    detected: str | None,
    detected_language: str | None,
) -> None:
    """Update a detector's stats dict with one detection result."""
    detector_stats["total"] += 1
    detector_stats["per_enc"][expected_encoding]["total"] += 1
    if is_correct(expected_encoding, detected) or (
        detected is not None
        and is_equivalent_detection(filepath.read_bytes(), expected_encoding, detected)
    ):
        detector_stats["correct"] += 1
        detector_stats["per_enc"][expected_encoding]["correct"] += 1
    else:
        detector_stats["failures"].append(
            f"  {filepath.parent.name}/{filepath.name}: "
            f"expected={expected_encoding}, got={detected}"
        )

    # Language tracking (independent of encoding accuracy)
    detector_stats["lang_total"] += 1
    detector_stats["per_enc"][expected_encoding]["lang_total"] += 1
    if (
        detected_language is not None
        and detected_language.lower() == expected_language.lower()
    ):
        detector_stats["lang_correct"] += 1
        detector_stats["per_enc"][expected_encoding]["lang_correct"] += 1
    else:
        detector_stats["lang_failures"].append(
            f"  {filepath.parent.name}/{filepath.name}: "
            f"expected={expected_language}, got={detected_language}"
        )
```

**Step 3: Update stats initialization**

Replace the stats initialization (lines 284-294) to include language counters:

```python
    # Initialize per-detector stats
    stats: dict[str, dict] = {}
    for label in detector_labels:
        stats[label] = {
            "correct": 0,
            "total": 0,
            "lang_correct": 0,
            "lang_total": 0,
            "per_enc": defaultdict(
                lambda: {
                    "correct": 0,
                    "total": 0,
                    "lang_correct": 0,
                    "lang_total": 0,
                }
            ),
            "failures": [],
            "lang_failures": [],
            "time": 0.0,
            "file_times": [],
        }
```

**Step 4: Update results unpacking loop**

Replace line 312:
```python
        for expected, _language, path_str, detected in results:
            _record_result(stats[label], expected, Path(path_str), detected)
```
with:
```python
        for expected, exp_lang, path_str, detected, det_lang in results:
            _record_result(
                stats[label], expected, exp_lang, Path(path_str), detected, det_lang
            )
```

**Step 5: Run linter to verify no errors**

Run: `uv run ruff check scripts/compare_detectors.py`

Expected: All checks passed.

**Step 6: Commit**

```
feat: track language detection accuracy in compare_detectors.py
```

---

### Task 3: Add language accuracy to compare_detectors.py report output

**Files:**
- Modify: `scripts/compare_detectors.py:334-346` (overall accuracy section)
- Modify: `scripts/compare_detectors.py` (add new sections after per-encoding table, before pairwise)

**Step 1: Add language line to overall accuracy section**

After the encoding accuracy line (line 345), add a language accuracy line. Replace the overall accuracy loop (lines 340-346):

```python
    for label in detector_labels:
        s = stats[label]
        enc_acc = s["correct"] / total if total else 0
        lang_acc = s["lang_correct"] / s["lang_total"] if s["lang_total"] else 0
        print(
            f"  {label + ':':<{max_label + 1}} "
            f"{s['correct']:>4}/{total} = {enc_acc:.1%} encoding  "
            f"{s['lang_correct']:>4}/{s['lang_total']} = {lang_acc:.1%} language  "
            f"({s['time']:.2f}s)"
        )
```

**Step 2: Add PER-ENCODING LANGUAGE ACCURACY table**

Add this new section after the existing per-encoding encoding accuracy table (after line 475, before the pairwise comparisons section at line 477). Insert this block:

```python
    # -- Per-encoding language accuracy --
    print()
    print("=" * 100)
    print("PER-ENCODING LANGUAGE ACCURACY")
    print("=" * 100)

    header = f"  {'Encoding':<25} {'Files':>5}"
    for label in detector_labels:
        header += f"  {label:>{col_w}}"
    print(header)
    sep = f"  {'-' * 25} {'-' * 5}"
    for _ in detector_labels:
        sep += f"  {'-' * col_w}"
    print(sep)

    for enc in all_encodings:
        t_enc = stats[ref_label]["per_enc"][enc]["lang_total"]
        if t_enc == 0:
            continue

        row = f"  {enc:<25} {t_enc:>5}"
        for label in detector_labels:
            s = stats[label]["per_enc"][enc]
            lang_t = s["lang_total"]
            lang_c = s["lang_correct"]
            acc = lang_c / lang_t if lang_t else 0
            row += f"  {lang_c:>{col_w - 12}}/{lang_t} = {acc:>6.1%} "
        print(row)
```

**Step 3: Add LANGUAGE FAILURES section**

Add this after the existing encoding failures section (after line 519). Insert:

```python
    # -- Language failure details --
    for label in detector_labels:
        failures = stats[label]["lang_failures"]
        print()
        print("=" * 100)
        print(f"{label.upper()} LANGUAGE FAILURES ({len(failures)} total)")
        print("=" * 100)
        for f in failures[:80]:
            print(f)
        if len(failures) > 80:
            print(f"  ... and {len(failures) - 80} more")
```

**Step 4: Run linter**

Run: `uv run ruff check scripts/compare_detectors.py`

Expected: All checks passed.

**Step 5: Run benchmark_time.py --pure --json-only end-to-end to verify JSON is parseable**

Run: `uv run python scripts/benchmark_time.py --pure --json-only 2>/dev/null | tail -5`

Expected: JSON lines with `detected_language` field, summary line at end.

**Step 6: Commit**

```
feat: add language accuracy reporting to compare_detectors.py output
```

---

### Task 4: Add language mismatch warnings to test_accuracy.py

**Files:**
- Modify: `tests/test_accuracy.py:1-32`

**Step 1: Add warnings import and language check**

Replace the full `tests/test_accuracy.py` content:

```python
# tests/test_accuracy.py
"""Accuracy evaluation against the chardet test suite.

Each test file is parametrized as its own test case via conftest.py's
pytest_generate_tests hook. Run with `pytest -n auto` for parallel execution.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import chardet
from chardet.enums import EncodingEra
from chardet.equivalences import is_correct, is_equivalent_detection

if TYPE_CHECKING:
    from pathlib import Path


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

    # Language accuracy: warn but don't fail
    detected_language = result["language"]
    if detected_language is None or detected_language.lower() != language.lower():
        warnings.warn(
            f"Language mismatch: expected={language}, got={detected_language} "
            f"(encoding={expected_encoding}, file={test_file_path.name})",
            stacklevel=1,
        )
```

**Step 2: Run the test suite to verify encoding tests still pass and language warnings appear**

Run: `uv run pytest tests/test_accuracy.py -x -q 2>&1 | tail -10`

Expected: tests pass, warnings summary shows language mismatches.

**Step 3: Verify warnings don't cause failures**

Run: `uv run pytest tests/test_accuracy.py -q --tb=no 2>&1 | tail -5`

Expected: all tests pass (green), warnings count shown in summary line.

**Step 4: Commit**

```
feat: add language mismatch warnings to test_accuracy.py
```

---

### Task 5: Final verification

**Step 1: Run full linter**

Run: `uv run ruff check scripts/benchmark_time.py scripts/compare_detectors.py tests/test_accuracy.py`

Expected: All checks passed.

**Step 2: Run full test suite**

Run: `uv run pytest -x -q`

Expected: all tests pass. Language warnings visible in summary.

**Step 3: Run benchmark_time.py standalone**

Run: `uv run python scripts/benchmark_time.py --pure`

Expected: human-readable output unchanged from before.

**Step 4: Run benchmark_time.py JSON mode and verify schema**

Run: `uv run python scripts/benchmark_time.py --pure --json-only 2>/dev/null | head -1 | python -m json.tool`

Expected: JSON with keys `expected`, `language`, `path`, `detected`, `detected_language`, `elapsed`.
