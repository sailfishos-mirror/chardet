# Parallel Training — Design

**Date:** 2026-02-27
**Current training time:** ~79 minutes (233 models, 25K samples)
**Goal:** ~7x speedup via parallel model building

## Problem

The build phase of `train.py` processes 233 (language, encoding) pairs
sequentially. Each model is completely independent — an embarrassingly
parallel workload running on a single core.

## Architecture

The download phase (already parallelized with ThreadPoolExecutor) stays
unchanged. Serialization stays sequential (~1s, irrelevant).

Only the build phase changes:

1. Extract per-model build logic from inline `main()` loop into a
   top-level function `_build_one_model()`.
2. Dispatch all 233 work items to `ProcessPoolExecutor`.
3. Each worker lazily loads language texts from the disk cache (populated
   by the download phase) and caches them per-worker in a module-level
   dict `_worker_text_cache`.

**Key invariant:** The download phase fully completes before any build
worker starts. The disk cache is read-only during build — no
synchronization needed.

## `_build_one_model()` Function

Top-level (picklable) function:

```python
_worker_text_cache: dict[str, list[str]] = {}

def _build_one_model(
    lang: str,
    enc_name: str,
    codec: str,
    cache_dir: str,
    max_samples: int,
    min_weight: int,
) -> tuple[str, dict[tuple[int, int], int] | None, int, int]:
    """Build one bigram model. Returns (key, bigrams, sample_count, byte_count)."""
```

Encapsulates the same logic currently inline at lines 844-884:
get texts → add HTML samples → normalize/substitute/encode → compute
bigrams → normalize and prune.

The `codec` argument is resolved in the parent (one-time verification
per encoding) and passed to the worker — no need for each worker to
re-verify.

## CLI

Add `--build-workers` argument:
- Default: `os.cpu_count()`
- `--build-workers 1` falls back to sequential mode (debugging)
- Same pattern as existing `--download-workers`

## Progress Output

With parallel workers, output order is non-deterministic. Each line
already includes the model key (e.g., `fr/windows-1252: 696 bigrams`)
so this is fine. Results are collected via `as_completed()` and printed
as they finish.

## Error Handling

If a worker raises, `future.result()` re-raises in the parent. We catch
the exception, print a warning, and continue with remaining models —
same skip behavior as the current sequential code.

## Memory

Each worker lazily loads only the languages it needs from disk (~45 MB
per language at 15K samples). With `cpu_count()` workers and 48
languages, a worker loading ~6 languages uses ~270 MB. Total across 8
workers: ~2.2 GB. Acceptable on 16 GB+ machines.
