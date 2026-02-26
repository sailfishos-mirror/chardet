# Test Parallelism, Performance, and Accuracy Improvements

**Date:** 2026-02-26
**Status:** Approved

## Context

The chardet rewrite has a working detection pipeline at 76.8% accuracy
(1660/2161 test files) with a serial test run time of ~169 seconds. The
feedback loop for accuracy work is too slow, and there is significant room
to improve detection quality.

This design covers four related changes that together enable faster iteration
and push accuracy to 90%.

## 1. Parallel Tests with pytest-xdist

**Problem:** `test_accuracy.py` runs 2161 files sequentially through
`chardet.detect()` in a single test function with an aggregate threshold
check. Slow feedback, no per-file visibility.

**Design:**
- Add `pytest-xdist` as a dev dependency.
- Refactor `test_accuracy.py` to parametrize each test file as its own
  test case. Test IDs like `test_detect[utf-8-english/file.txt]`.
- Each test: read file, call `chardet.detect(data, encoding_era=ALL)`,
  assert `is_correct(expected, detected)`.
- Remove the aggregate `_MIN_OVERALL_ACCURACY` threshold. Per-file
  pass/fail replaces it.
- Hard failures (no xfail). Current failures show as FAILED. Use
  `pytest --lf -n auto` for fast re-runs of just the failures.
- `_collect_test_files` moves to a shared utility (see section 2).

**Rationale:** Individual test cases give per-file regression tracking.
xdist distributes them across CPU cores automatically. `--lf` means
re-running only failures takes seconds instead of minutes.

## 2. Consolidate Compare Scripts

**Problem:** `compare_detectors.py` and `compare_strict.py` duplicate
90% of the same logic. Both compare chardet-rewrite vs charset-normalizer.
`compare_strict.py` has richer output; `compare_detectors.py` has
short-input edge cases.

**Design:**
- Delete both scripts.
- Create a new `scripts/compare_detectors.py` that merges:
  - Directional-equivalence comparison with per-encoding table, winner
    column, and win/loss summaries (from `compare_strict.py`).
  - Short-input edge cases (from old `compare_detectors.py`).
  - Thai encoding deep-dive (from `compare_strict.py`).
- Extract `_collect_test_files` into `scripts/utils.py`. Import from
  there in `compare_detectors.py`, `diagnose_accuracy.py`, and
  `tests/conftest.py` (or a test helper).

**Rationale:** One script to maintain instead of two. Shared utility
eliminates the 4x copy-paste of `_collect_test_files`.

## 3. Performance Optimization

**Problem:** Serial detection of 2161 files takes 169 seconds. Even with
xdist parallelism, per-file detection speed matters for the iteration
loop.

**Design:**
- Profile the full pipeline on the 2161-file suite using `cProfile`
  or `py-spy` to identify actual bottlenecks.
- Likely hotspots (based on code inspection):
  - `score_bigrams`: Python dict lookups per byte pair, O(n) per
    encoding per candidate.
  - `ProcessPoolExecutor` in `statistical.py`: process spawn + model
    reload overhead may dominate for typical inputs.
  - Structural probing: pure Python byte-by-byte loops.
- Apply targeted optimizations after profiling confirms. Stay pure
  Python, PyPy-friendly, zero runtime dependencies.
- Re-profile to verify improvements.

**Constraints:** No C extensions. No new runtime dependencies. Must
work on CPython 3.10+ and PyPy.

## 4. Accuracy Iteration to 90%

**Problem:** Current accuracy is 76.8%. Target is 90% (1945/2161).
Need to fix ~285 more files.

**Design:**
- Use `scripts/diagnose_accuracy.py` to identify worst-performing
  encodings and common confusion patterns.
- Fix highest-impact encodings first by:
  - Retraining bigram models (via `scripts/train.py --encodings ...`).
  - Adding or refining encoding equivalences.
  - Tuning pipeline logic (e.g., structural score thresholds, CJK
    gating, validity filtering).
- Iteration loop:
  1. `pytest tests/test_accuracy.py --lf -n auto` — see current failures.
  2. `uv run scripts/diagnose_accuracy.py` — identify worst encodings.
  3. Fix the highest-impact encoding.
  4. Re-run `--lf` to verify improvement without regressions.
  5. Repeat until 90%.

**Target:** 90% overall accuracy on the chardet test suite (2161 files).

## Execution Order

Steps 1-3 are independent and can be done in any order (or in parallel).
Step 4 depends on 1-3 being complete for the fast feedback loop.

Recommended order: 1 → 2 → 3 → 4 (tests first so the feedback loop is
available during profiling and accuracy work).
