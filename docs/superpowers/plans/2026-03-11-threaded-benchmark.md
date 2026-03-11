# Threaded Benchmark Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `--threads N` to `benchmark_time.py` so chardet detection scaling can be measured on free-threaded vs GIL Python.

**Architecture:** Add a `--threads` argument to `benchmark_time.py` that defaults to 1 (unchanged behavior). When >1, use `ThreadPoolExecutor` to run `detect()` calls concurrently, preserving per-file timing and file order. `compare_detectors.py` passes `--threads` through to subprocesses and includes thread count in cache filenames (only when >1, preserving existing caches).

**Tech Stack:** Python stdlib only (`concurrent.futures`, `argparse`, `time`)

**Spec:** `docs/superpowers/specs/2026-03-11-threaded-benchmark-design.md`

---

## Chunk 1: benchmark_time.py — threaded detection

### Task 1: Add `--threads` argument and `concurrent.futures` import

**Files:**
- Modify: `scripts/benchmark_time.py:1-28`

- [ ] **Step 1: Add `concurrent.futures` import and `--threads` argument**

In `scripts/benchmark_time.py`, add the import at line 13 (after `import json`) and add the `--threads` argument after `parser.parse_args()`:

```python
# At line 13, add:
import concurrent.futures

# After line 28 (args = parser.parse_args()), add:
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        metavar="N",
        help="Number of detection threads (default: 1, no threading overhead)",
    )
    args = parser.parse_args()
```

Wait — the parser is created on line 25-27 and `parse_args()` is on line 28. The `--threads` argument must be added between parser creation and `parse_args()`. The full change to lines 25-29:

```python
    parser = build_benchmark_parser(
        "Benchmark a single encoding detector (timing only)."
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        metavar="N",
        help="Number of detection threads (default: 1, no threading overhead)",
    )
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("--threads must be >= 1")
```

- [ ] **Step 2: Verify script still works with default args**

Run: `uv run python scripts/benchmark_time.py --detector chardet 2>&1 | head -20`

Expected: Same output as before (Detector: chardet, timing stats). No errors.

- [ ] **Step 3: Verify `--threads` argument is accepted**

Run: `uv run python scripts/benchmark_time.py --detector chardet --threads 1 2>&1 | head -5`

Expected: Same output as step 2. No "unrecognized arguments" error.

---

### Task 2: Add multi-threaded detection path

**Files:**
- Modify: `scripts/benchmark_time.py:81-103`

The current single-threaded detection loop (lines 81-103) needs to be split into two paths. When `threads == 1`, run the existing loop unchanged. When `threads > 1`, use `ThreadPoolExecutor`.

- [ ] **Step 1: Replace detection loop with branched logic**

Replace lines 81-103 (from `# Run detection over all files` through `total_elapsed = ...`) with:

```python
    # Run detection over all files, collect per-file times + results
    file_times: list[float] = []

    if args.threads > 1:
        # Multi-threaded path: distribute detect() calls across threads
        def _detect_one(
            item: tuple[str | None, str | None, Path, bytes],
        ) -> tuple[str | None, str | None, Path, str | None, str | None, float]:
            enc, lang, fp, data = item
            ft0 = time.perf_counter()
            detected, detected_language = detect(data)
            file_elapsed = time.perf_counter() - ft0
            return enc, lang, fp, detected, detected_language, file_elapsed

        results_for_json: list[dict] = []
        t_total_start = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.threads
        ) as executor:
            for enc, lang, fp, detected, detected_language, file_elapsed in (
                executor.map(_detect_one, all_data)
            ):
                file_times.append(file_elapsed)
                if args.json_only:
                    results_for_json.append(
                        {
                            "expected": enc,
                            "language": lang,
                            "path": str(fp),
                            "detected": detected,
                            "detected_language": detected_language,
                            "elapsed": file_elapsed,
                        }
                    )
        total_elapsed = time.perf_counter() - t_total_start

        # Print buffered JSON results (preserves file order)
        for obj in results_for_json:
            print(json.dumps(obj))
    else:
        # Single-threaded path: no executor overhead
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

Note: The single-threaded `else` branch is equivalent to the existing code (lines 82-103), with `t_total_start` moved inside the branch. The multi-threaded branch uses `executor.map()` to preserve file order, buffers JSON output, and prints after all futures complete.

- [ ] **Step 2: Verify single-threaded path is unchanged**

Run: `uv run python scripts/benchmark_time.py --detector chardet --json-only 2>&1 | tail -1`

Expected: A JSON line with `__timing__`, `import_time`, `first_detect_time` keys (no `threads` key yet — that's the next task).

- [ ] **Step 3: Verify multi-threaded path works**

Run: `uv run python scripts/benchmark_time.py --detector chardet --threads 2 --json-only 2>&1 | tail -1`

Expected: Same format JSON summary line. No errors.

- [ ] **Step 4: Commit**

```bash
git add scripts/benchmark_time.py
git commit -m "feat: add --threads option to benchmark_time.py for concurrent detection"
```

---

### Task 3: Add `threads` to JSON summary and human-readable output

**Files:**
- Modify: `scripts/benchmark_time.py:105-140` (line numbers approximate after Task 2 edits)

- [ ] **Step 1: Add `threads` to `__timing__` JSON summary**

In the `if args.json_only:` block (the summary print after the detection loop), add `"threads"` to the dict:

```python
    if args.json_only:
        # Summary line (last)
        print(
            json.dumps(
                {
                    "__timing__": total_elapsed,
                    "import_time": import_time,
                    "first_detect_time": first_detect_time,
                    "threads": args.threads,
                }
            )
        )
```

- [ ] **Step 2: Add `Threads:` to human-readable output**

In the `else:` block (human-readable summary), add the threads line after the header:

```python
        print(f"Detector: {args.detector}")
        if args.detector == "chardet":
            print(f"  encoding_era: {args.encoding_era}")
        print(f"  Files:        {len(all_data)}")
        print(f"  Threads:      {args.threads}")
```

- [ ] **Step 3: Verify JSON output includes threads**

Run: `uv run python scripts/benchmark_time.py --detector chardet --threads 2 --json-only 2>&1 | tail -1`

Expected: JSON line includes `"threads": 2`.

- [ ] **Step 4: Verify human-readable output shows threads**

Run: `uv run python scripts/benchmark_time.py --detector chardet --threads 2 2>&1 | head -10`

Expected: Output includes `Threads:      2` line.

- [ ] **Step 5: Verify single-threaded human-readable output shows threads=1**

Run: `uv run python scripts/benchmark_time.py --detector chardet 2>&1 | head -10`

Expected: Output includes `Threads:      1` line.

- [ ] **Step 6: Commit**

```bash
git add scripts/benchmark_time.py
git commit -m "feat: include thread count in benchmark_time.py output"
```

---

## Chunk 2: compare_detectors.py — passthrough and cache keys

### Task 4: Add `threads` parameter to `_cache_filename` and `_has_full_cache`

**Files:**
- Modify: `scripts/compare_detectors.py:89-103,323-341`

- [ ] **Step 1: Update `_cache_filename` to accept optional `threads` parameter**

Replace the function (lines 89-103):

```python
def _cache_filename(  # noqa: PLR0913
    detector_name: str,
    detector_version: str,
    benchmark_hash: str,
    python_tag: str,
    build_tag: str,
    kind: str,
    *,
    threads: int = 1,
) -> str:
    """Build a cache filename like ``chardet_7.0.1_a1b2c3_cpython3.11_mypyc_time.json``.

    When *threads* > 1, a ``{N}threads`` segment is inserted before *kind*:
    ``chardet_7.0.1_a1b2c3_cpython3.11_mypyc_4threads_time.json``.

    *detector_name* should be the package name (e.g. ``"chardet"``,
    ``"charset-normalizer"``), **not** the display label.
    """
    safe_name = detector_name.replace(" ", "-").replace("/", "-")
    threads_seg = f"_{threads}threads" if threads > 1 else ""
    return f"{safe_name}_{detector_version}_{benchmark_hash}_{python_tag}_{build_tag}{threads_seg}_{kind}.json"
```

- [ ] **Step 2: Update `_has_full_cache` to accept and pass through `threads`**

Replace the function (lines 323-341):

```python
def _has_full_cache(  # noqa: PLR0913
    cache_dir: Path,
    detector_type: str,
    version: str,
    benchmark_hash: str,
    python_tag: str,
    build_tag: str,
    *,
    skip_memory: bool = False,
    threads: int = 1,
) -> bool:
    """Return ``True`` if all required cache files exist."""
    kinds = ("time",) if skip_memory else ("time", "memory")
    for kind in kinds:
        fname = _cache_filename(
            detector_type, version, benchmark_hash, python_tag, build_tag, kind,
            threads=threads,
        )
        if not (cache_dir / fname).is_file():
            return False
    return True
```

- [ ] **Step 3: Commit**

```bash
git add scripts/compare_detectors.py
git commit -m "feat: add threads parameter to cache filename functions"
```

---

### Task 5: Add `threads` parameter to timing subprocess functions

**Files:**
- Modify: `scripts/compare_detectors.py:409-485,493-552`

- [ ] **Step 1: Update `_run_timing_subprocess` to accept and pass `threads`**

Add `threads: int = 1` to the keyword arguments (after `pure: bool = False`) and append to the command:

```python
def _run_timing_subprocess(
    python_executable: str,
    data_dir: str,
    *,
    detector_type: str = "chardet",
    encoding_era: str = "all",
    pure: bool = False,
    threads: int = 1,
) -> _TimingResult:
```

After the existing `if pure: cmd.append("--pure")` line (line 451), add:

```python
    if threads > 1:
        cmd.extend(["--threads", str(threads)])
```

- [ ] **Step 2: Update `_run_timing_with_median` to accept and pass `threads`**

Add `threads: int = 1` to the keyword arguments (after `num_runs: int = 3`) and pass it through to `_run_timing_subprocess`:

```python
def _run_timing_with_median(  # noqa: PLR0913
    python_executable: str,
    data_dir: str,
    *,
    detector_type: str = "chardet",
    encoding_era: str = "all",
    pure: bool = False,
    num_runs: int = 3,
    threads: int = 1,
) -> _TimingResult:
```

And in the loop body (line 515-521), add `threads=threads`:

```python
        run = _run_timing_subprocess(
            python_executable,
            data_dir,
            detector_type=detector_type,
            encoding_era=encoding_era,
            pure=pure,
            threads=threads,
        )
```

- [ ] **Step 3: Commit**

```bash
git add scripts/compare_detectors.py
git commit -m "feat: pass threads through timing subprocess functions"
```

---

### Task 6: Add `threads` to `run_comparison` and the inner `_run_timing_for_detector`

**Files:**
- Modify: `scripts/compare_detectors.py:646-800`

- [ ] **Step 1: Add `threads: int = 1` to `run_comparison` signature**

Add after `no_memory: bool = False`:

```python
def run_comparison(  # noqa: PLR0913
    data_dir: Path,
    detectors: list[tuple[str, str, str, str]],
    *,
    pure: bool = False,
    detector_versions: dict[str, str] | None = None,
    python_tags: dict[str, str] | None = None,
    build_tags: dict[str, str] | None = None,
    use_cache: bool = True,
    benchmark_hash: str = "",
    no_memory: bool = False,
    threads: int = 1,
) -> None:
```

- [ ] **Step 2: Update `_run_timing_for_detector` inner function**

This inner function (lines 739-799) has three places that need `threads`:

**a) Cache load** — pass `threads=threads` to `_cache_filename` (line 748-750):
```python
            fname = _cache_filename(
                detector_type, version, benchmark_hash, py_tag, b_tag, "time",
                threads=threads,
            )
```

**b) `_run_timing_with_median` call** — pass `threads=threads` (line 773-780):
```python
        timing = _run_timing_with_median(
            python_exe,
            data_dir_str,
            detector_type=detector_type,
            encoding_era=era,
            pure=is_pure,
            num_runs=num_runs,
            threads=threads,
        )
```

**c) Cache save** — pass `threads=threads` to `_cache_filename` (line 784-786):
```python
            fname = _cache_filename(
                detector_type, version, benchmark_hash, py_tag, b_tag, "time",
                threads=threads,
            )
```

**Note:** The `_cache_filename` call sites at lines 842 and 862 (memory cache load/save) are intentionally NOT updated — they use the default `threads=1` since memory benchmarks are always single-threaded. Do not add `threads=threads` to these calls.

- [ ] **Step 3: Update report header to show threads when > 1**

After the `print(f"Detectors: {', '.join(detector_labels)}")` line (line 697), add:

```python
    if threads > 1:
        print(f"Threads: {threads}")
```

- [ ] **Step 4: Commit**

```bash
git add scripts/compare_detectors.py
git commit -m "feat: thread count flows through run_comparison to subprocess calls and cache"
```

---

### Task 7: Add `--threads` CLI argument and pass to `run_comparison`

**Files:**
- Modify: `scripts/compare_detectors.py:1144-1210,1326-1337,1427-1437`

- [ ] **Step 1: Add `--threads` argument to the CLI parser**

After the `--mypyc` argument block (line 1205), add:

```python
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        metavar="N",
        help="Number of detection threads for benchmark_time.py (default: 1)",
    )
```

- [ ] **Step 2: Pass `threads` to `_has_full_cache` call**

In the cache-check loop (lines 1326-1337), add `threads=args.threads`:

```python
        if cache_dir is not None and _has_full_cache(
            cache_dir,
            det_type,
            detector_versions[label],
            benchmark_hash,
            python_tags[label],
            build_tags[label],
            skip_memory=args.no_memory,
            threads=args.threads,
        ):
```

- [ ] **Step 3: Pass `threads` to `run_comparison` call**

In the `run_comparison()` call (lines 1427-1437), add `threads=args.threads`:

```python
        run_comparison(
            data_dir,
            detectors,
            pure=args.pure,
            detector_versions=detector_versions,
            python_tags=python_tags,
            build_tags=build_tags,
            use_cache=use_cache,
            benchmark_hash=benchmark_hash,
            no_memory=args.no_memory,
            threads=args.threads,
        )
```

- [ ] **Step 4: Commit**

```bash
git add scripts/compare_detectors.py
git commit -m "feat: add --threads CLI argument to compare_detectors.py"
```

---

### Task 8: Smoke test

- [ ] **Step 1: Run benchmark_time.py single-threaded**

Run: `uv run python scripts/benchmark_time.py --detector chardet`

Expected: Output shows `Threads:      1` and normal timing stats.

- [ ] **Step 2: Run benchmark_time.py multi-threaded**

Run: `uv run python scripts/benchmark_time.py --detector chardet --threads 4`

Expected: Output shows `Threads:      4` and timing stats. Total time should be similar or faster than single-threaded (on GIL Python, roughly the same).

- [ ] **Step 3: Run benchmark_time.py JSON mode with threads**

Run: `uv run python scripts/benchmark_time.py --detector chardet --threads 2 --json-only 2>&1 | tail -1`

Expected: JSON line with `"threads": 2` in the `__timing__` summary.

- [ ] **Step 4: Run existing test suite to confirm nothing is broken**

Run: `uv run python -m pytest -n auto tests/test_api.py tests/test_benchmark.py -v`

Expected: All tests pass.

- [ ] **Step 5: Run ruff to verify code quality**

Run: `uv run ruff check scripts/benchmark_time.py scripts/compare_detectors.py`

Expected: No lint errors.
