---
name: update-benchmarks
description: Use when benchmark numbers in docs/performance.rst need refreshing, after performance changes, before releases, or when the user asks to update benchmarks.
---

# Update Benchmarks

Regenerate all benchmark data and update `docs/performance.rst`.

## What Gets Updated

1. **Accuracy & Speed table** (chardet vs chardet 6.0.0 vs charset-normalizer vs cchardet)
2. **Memory table** (chardet vs chardet 6.0.0 vs charset-normalizer vs cchardet)
3. **Language Detection table**
4. **charset-normalizer's Test Set table** (--cn-dataset subset)
5. **Thread Safety table** (3.13, 3.13t, 3.14, 3.14t, pure + mypyc, 1/2/4/8 threads)
6. **Optional mypyc Compilation table** (pure vs mypyc on current CPython)
7. **Performance Across Python Versions table** (CPython 3.10-3.14 mypyc + pure, PyPy 3.10-3.11 pure)

Also update `docs/index.rst` and `docs/faq.rst` with derived numbers.

## Step 1: Run Benchmarks

Run these sequentially (not in parallel — concurrent builds cause `/dev/null` permission errors):

```bash
# 1a. Main comparison (accuracy, speed, memory) — includes all opponents
uv run python scripts/compare_detectors.py -c 6.0.0 --cn --cchardet --mypyc

# 1b. charset-normalizer dataset subset
uv run python scripts/compare_detectors.py --cn-dataset --cn --mypyc --no-memory

# 1c. Cross-version mypyc (CPython only — PyPy can't do mypyc)
uv run python scripts/compare_detectors.py --python 3.10 --python 3.11 --python 3.12 --python 3.13 --python 3.14 --mypyc --no-memory

# 1d. Cross-version pure (all interpreters)
uv run python scripts/compare_detectors.py --python 3.10 --python 3.11 --python 3.12 --python 3.13 --python 3.14 --python pypy3.10 --python pypy3.11 --pure --no-memory

# 1e. Thread safety (wall-clock times — use detection: field, not sum of per-file times)
for py in 3.13 3.14 3.13t 3.14t; do
  for build in "--pure" "--mypyc"; do
    for threads in 1 2 4 8; do
      echo "=== $py $build threads=$threads ==="
      uv run python scripts/compare_detectors.py --python "$py" $build --no-memory --threads "$threads" 2>&1 | grep 'detection:'
    done
  done
done
```

Steps 1c-1e use `--no-memory` because memory usage doesn't vary across Python versions or thread counts. Step 1a includes memory since it compares across detectors. If memory numbers haven't changed since the last release, add `--no-memory` to 1a too.

## Step 2: Extract Key Numbers

From the main comparison (1a), extract:
- **Accuracy**: `X/2521 = XX.X%` for each detector
- **Speed**: total, mean, median, p90, p95 for each detector
- **Files/s**: `2521 / total_seconds`
- **Memory**: import time, import mem, peak mem, RSS
- **Language**: `X/2513 = XX.X%` for each detector

From thread safety (1e), extract **wall-clock** detection time (the `(detection: X.XXs)` field), NOT the sum-of-per-file-times in the timing distribution.

## Step 3: Update Docs

### docs/performance.rst
Update all tables and derived comparison text:
- "Xx faster than chardet 6.0.0" = chardet_6_mean / chardet_7_mean
- "X.Xx faster than charset-normalizer" = cn_mean / chardet_mean
- "+X.Xpp" accuracy differences
- Thread safety speedup = 1_thread_time / N_thread_time for free-threaded runs
- mypyc speedup = pure_files_per_sec / mypyc_files_per_sec
- "CPython X.XX + mypyc is the fastest" = highest files/s from cross-version table
- PyPy reaches "XX-XX% of mypyc" = pypy_fps / min_mypyc_fps and pypy_fps / max_mypyc_fps

### docs/index.rst
- Accuracy percentage and file count
- Speed comparison multipliers (vs 6.0.0, vs charset-normalizer)

### docs/faq.rst
- charset-normalizer comparison numbers (accuracy, speed, memory, language)
- cchardet comparison numbers

## Step 4: Verify and Commit

```bash
uv run sphinx-build -W docs docs/_build
git add docs/performance.rst docs/index.rst docs/faq.rst
git commit -m "docs: update benchmark numbers for 7.X.0"
git push
```

## Notes

- `compare_detectors.py` caches results in `.benchmark_results/`. Cache keys include the detector version, Python version, build type (pure/mypyc), thread count, and a content hash of the benchmark scripts (`benchmark_time.py`, `benchmark_memory.py`, `utils.py`) and equivalence rules (`equivalences.py`). Results auto-invalidate when any of these change. The chardet version includes the git commit hash (e.g., `7.2.1.dev25+g3680cc1ad`), so any commit invalidates the local chardet cache. Only use `--no-cache` if you need to re-benchmark an unchanged version (e.g., to reduce measurement noise).
- PyPy can't use `--mypyc` (mypyc is CPython-only). Always use `--pure` for PyPy.
- `--python` is repeatable: `--python 3.12 --python 3.13` runs both sequentially.
- The test file count (currently 2,521) may change when test-data is updated.
