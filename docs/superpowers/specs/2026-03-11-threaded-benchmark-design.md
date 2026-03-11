# Threaded Benchmark Design

**Date:** 2026-03-11
**Goal:** Measure how chardet detection performance scales with threads on free-threaded vs GIL Python.

## Background

chardet's `detect()` is thread-safe: each call creates its own `PipelineContext`, and model loading uses `functools.cache` (thread-safe). This makes it a good candidate for free-threaded Python (3.13t, 3.14t) scaling benchmarks.

The existing `benchmark_time.py` runs detection single-threaded. We need to measure throughput and per-file latency under concurrent load to compare GIL vs free-threaded behavior.

## Approach

Add a `--threads N` option to `benchmark_time.py` (default 1). When N=1, the current single-threaded code path runs unchanged. When N>1, a `ThreadPoolExecutor` distributes detect() calls across threads. `compare_detectors.py` passes the flag through and includes thread count in cache keys.

## Changes to `benchmark_time.py`

**New argument:** `--threads N` (default 1), added directly in `main()` (not in `build_benchmark_parser()` since `benchmark_memory.py` shares that parser and threading doesn't apply to memory benchmarks).

**Import:** `concurrent.futures` is imported unconditionally at the top of the file.

**Single-threaded path (threads=1):** Exactly the current code. No executor, no overhead.

**Input validation:** `--threads` must be >= 1. Use `type=int` with argparse.

**Multi-threaded path (threads>1):**

- Create `ThreadPoolExecutor(max_workers=threads)`.
- Submit all `detect(data)` calls as futures.
- Buffer all results and print JSON lines after all futures complete, preserving original file order.
- Each file still gets an individual `elapsed` measurement (wall-clock start/end of that file's detect call).
- Total elapsed (`__timing__`) is wall-clock time from first submit to last result collected — same as current behavior, just the loop is concurrent.

**Warm-up call:** Stays single-threaded regardless of `--threads`. Measures lazy initialization cost, not threading overhead.

**JSON output (`--json-only`):**

- Per-file lines: unchanged format, each includes `elapsed`.
- Summary `__timing__` line: adds `"threads": N`.

**Human-readable output:** Adds `Threads: N` line to the header.

**Per-file timing rationale:** On GIL Python, per-file `elapsed` under concurrent load shows contention overhead (times get worse). On free-threaded Python, per-file times should stay similar to single-threaded. This contrast is a useful signal.

## Changes to `compare_detectors.py`

**New argument:** `--threads N` (default 1).

**Passthrough:** The thread count is passed through `_run_timing_subprocess()` → `_run_timing_with_median()` → subprocess command line as `--threads N`. Both functions gain a `threads: int = 1` parameter. `_run_timing_subprocess` appends `["--threads", str(threads)]` to the subprocess command.

**Cache filename:** Thread count is included in the cache key only when threads > 1, to preserve backward compatibility with existing caches. Format: `chardet_7.0.1_a1b2c3_cpython3.11_pure_4threads_time.json`. When threads=1, no threads segment — filename is identical to today. The `_cache_filename()` function gains an optional `threads: int = 1` parameter.

**Report header:** Display thread count when > 1.

## Files modified

| File | Change |
|------|--------|
| `scripts/benchmark_time.py` | Add `--threads` argument, conditional ThreadPoolExecutor path |
| `scripts/compare_detectors.py` | Add `--threads` argument, passthrough to subprocesses, update cache filename |

## Files not modified

| File | Reason |
|------|--------|
| `scripts/utils.py` | `build_benchmark_parser()` is shared with memory benchmarks; `--threads` is timing-specific |
| `scripts/benchmark_memory.py` | Threading not relevant to memory measurement |
| `src/chardet/` | No detection code changes needed; `detect()` is already thread-safe |
