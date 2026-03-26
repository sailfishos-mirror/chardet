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

Also update `docs/index.rst`, `docs/faq.rst`, and `README.md` with derived numbers.

## Step 1: Run Benchmarks

Run these sequentially (not in parallel — concurrent builds cause `/dev/null` permission errors):

```bash
# 1a. Main comparison (accuracy, speed, memory) — chardet + charset-normalizer + cchardet
uv run python scripts/compare_detectors.py --memory --cn --cchardet --mypyc

# 1b. chardet 6.0.0 comparison (accuracy, speed only — memory is very slow for 6.0.0)
uv run python scripts/compare_detectors.py -c 6.0.0 --mypyc

# 1c. charset-normalizer dataset subset
uv run python scripts/compare_detectors.py --cn-dataset --cn --mypyc

# 1d. Cross-version mypyc (CPython only — PyPy can't do mypyc)
uv run python scripts/compare_detectors.py --python 3.10 --python 3.11 --python 3.12 --python 3.13 --python 3.14 --mypyc

# 1e. Cross-version pure (all interpreters)
uv run python scripts/compare_detectors.py --python 3.10 --python 3.11 --python 3.12 --python 3.13 --python 3.14 --python pypy3.10 --python pypy3.11 --pure

# 1f. Thread safety (wall-clock times — use detection: field, not sum of per-file times)
for py in 3.13 3.14 3.13t 3.14t; do
  for build in "--pure" "--mypyc"; do
    for threads in 1 2 4 8; do
      echo "=== $py $build threads=$threads ==="
      uv run python scripts/compare_detectors.py --python "$py" $build --threads "$threads" 2>&1 | grep 'detection:'
    done
  done
done
```

Memory benchmarks are off by default (pass `--memory` to include them). Step 1a includes `--memory` for chardet, charset-normalizer, and cchardet. Step 1b runs chardet 6.0.0 without memory because its memory benchmark is extremely slow. If you need chardet 6.0.0 memory numbers, add `--memory` to step 1b.

## Step 2: Extract Key Numbers

From the main comparisons (1a + 1b), extract:
- **Accuracy**: `X/2521 = XX.X%` for each detector
- **Speed**: total, mean, median, p90, p95 for each detector
- **Files/s**: `2521 / total_seconds`
- **Memory**: import time, import mem, peak mem, RSS
- **Language**: `X/2513 = XX.X%` for each detector

From thread safety (1f), extract **wall-clock** detection time (the `(detection: X.XXs)` field), NOT the sum-of-per-file-times in the timing distribution.

## Step 3: Update Docs

### docs/performance.rst
Update all tables and derived comparison text:
- Accuracy & Speed tables: numbers from steps 1a + 1b
- Memory table: numbers from step 1a (skip if unchanged)
- Language Detection table: numbers from steps 1a + 1b
- charset-normalizer's Test Set table: numbers from step 1c
- Thread Safety table: wall-clock times from step 1f
- Optional mypyc Compilation table: use the current default CPython (e.g., 3.14) pure and mypyc numbers from steps 1d/1e. Speedup = mypyc_files_per_sec / pure_files_per_sec
- Performance Across Python Versions table: all numbers from steps 1d/1e
- Derived text: "Xx faster than chardet 6.0.0" = chardet_6_mean / chardet_7_mean, "+X.Xpp" accuracy differences, "CPython X.XX + mypyc is the fastest" = highest files/s, PyPy reaches "XX-XX% of mypyc" = pypy_fps / min_mypyc_fps and pypy_fps / max_mypyc_fps

### docs/index.rst
- Accuracy percentage and file count
- Speed comparison multipliers (vs 6.0.0, vs charset-normalizer)

### docs/faq.rst
- charset-normalizer comparison numbers (accuracy, speed, memory, language)
- cchardet comparison numbers

### README.md
- "Why chardet 7.0?" section: accuracy, speed multipliers, file count
- Comparison table: accuracy, speed (files/s), language accuracy, peak memory for chardet (mypyc + pure), chardet 6.0.0, charset-normalizer
- Example output dicts (add `mime_type` key if missing)
- "What's New in 7.0" section: speed/accuracy claims

## Step 4: Verify and Commit

```bash
uv run sphinx-build -W docs docs/_build
git add docs/performance.rst docs/index.rst docs/faq.rst README.md
git commit -m "docs: update benchmark numbers for 7.X.0"
git push
```

## Notes

- `compare_detectors.py` caches results in `.benchmark_results/`. Cache keys include the detector version, Python version, build type (pure/mypyc), thread count, and a content hash of the benchmark scripts (`benchmark_time.py`, `benchmark_memory.py`, `utils.py`), equivalence rules (`equivalences.py`), and the test-data submodule commit. Results auto-invalidate when any of these change. The chardet version includes the git commit hash (e.g., `7.2.1.dev25+g3680cc1ad`), so any chardet commit invalidates the local chardet cache, and any test-data change invalidates all caches. The `--cn-dataset` flag doesn't need its own cache key because the benchmark subprocess always runs on all files; the subset filter is applied when aggregating results. Only use `--no-cache` if you need to re-benchmark an unchanged version (e.g., to reduce measurement noise).
- Memory benchmarks are off by default. Pass `--memory` to include them. Only step 1a needs memory.
- PyPy can't use `--mypyc` (mypyc is CPython-only). Always use `--pure` for PyPy.
- `--python` is repeatable: `--python 3.12 --python 3.13` runs both sequentially.
- The test file count (currently 2,521) may change when test-data is updated.
