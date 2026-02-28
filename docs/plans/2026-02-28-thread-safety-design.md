# Thread-Safety Design: PipelineContext + Load-Once Cache Locking

## Problem

chardet has 6 module-level mutable caches. Five are "load-once" caches
(populated on first use, never modified again) and one is a "per-run" cache
(cleared and rebuilt each `run_pipeline()` call). Neither category is safe
under concurrent `detect()` calls, and the per-run cache (`_analysis_cache`)
actively corrupts when two pipelines run simultaneously.

### Caches inventory

| Cache | File | Type | Pattern |
|-------|------|------|---------|
| `_MODEL_CACHE` | models/__init__.py | dict \| None | Load-once |
| `_ENC_INDEX` | models/__init__.py | dict \| None | Load-once |
| `_MODEL_NORMS` | models/__init__.py | dict \| None | Load-once |
| `_CONFUSION_CACHE` | pipeline/confusion.py | dict \| None | Load-once |
| `_CANDIDATES_CACHE` | registry.py | dict | Load-once |
| `_analysis_cache` | pipeline/structural.py | dict | Per-run |

## Solution

Two complementary mechanisms:

### 1. PipelineContext dataclass (per-run state)

A non-frozen dataclass in `pipeline/__init__.py` carrying all per-run mutable
state. Created once at the start of `run_pipeline()` and threaded through the
call chain via function parameters.

```python
@dataclasses.dataclass(slots=True)
class PipelineContext:
    """Per-run state for a single pipeline invocation."""
    analysis_cache: dict[tuple[int, int, str], tuple[float, int, int]] = field(default_factory=dict)
    non_ascii_count: int = -1  # -1 = not yet computed
    mb_scores: dict[str, float] = field(default_factory=dict)
```

Fields:

- **`analysis_cache`**: Replaces the module-level `_analysis_cache` in
  structural.py. Keyed by `(id(data), len(data), encoding_name)`. Shared
  across `compute_structural_score()`, `compute_multibyte_byte_coverage()`,
  and `compute_lead_byte_diversity()` within a single run.

- **`non_ascii_count`**: Count of bytes >= 0x80. Computed once in
  `_gate_cjk_candidates()` via `bytes.translate`, stored on context for
  reuse by any stage that needs it. `-1` means not yet computed.

- **`mb_scores`**: Maps encoding name to structural score (float). Computed
  during CJK gating, reused in Stage 2b structural scoring to avoid
  redundant analysis.

### 2. Double-checked locking (load-once caches)

Each of the 5 load-once caches gets a `threading.Lock` with the standard
double-checked locking pattern:

```python
_LOCK = threading.Lock()
_CACHE: T | None = None

def load_cache() -> T:
    global _CACHE
    if _CACHE is not None:          # fast path, no lock
        return _CACHE
    with _LOCK:
        if _CACHE is not None:      # re-check under lock
            return _CACHE
        _CACHE = ...build...
        return _CACHE
```

The lock is only contended on the very first call. After initialization,
every subsequent call takes the fast path with zero synchronization overhead.

Applied to:
- `load_models()` / `_MODEL_CACHE`
- `_get_enc_index()` / `_ENC_INDEX`
- `_get_model_norms()` / `_MODEL_NORMS`
- `load_confusion_data()` / `_CONFUSION_CACHE`
- `get_candidates()` / `_CANDIDATES_CACHE`

## Call chain changes

### Functions gaining a `ctx: PipelineContext` parameter

- `_run_pipeline_core()` — creates the context
- `_gate_cjk_candidates()` — writes `ctx.non_ascii_count`, `ctx.mb_scores`
- `compute_structural_score()` — reads/writes `ctx.analysis_cache`
- `compute_multibyte_byte_coverage()` — reads `ctx.analysis_cache`
- `compute_lead_byte_diversity()` — reads `ctx.analysis_cache`
- `_get_analysis()` (internal) — reads/writes `ctx.analysis_cache`

### What gets deleted

- `_analysis_cache` module global in structural.py
- `clear_analysis_cache()` function in structural.py
- `clear_analysis_cache()` call in `_run_pipeline_core()`
- The import of `clear_analysis_cache` in orchestrator.py

### What stays unchanged

- `run_pipeline()` public signature (no context parameter exposed)
- `UniversalDetector` — calls `run_pipeline()` which creates its own context
- `detect()` / `detect_all()` public API
- All load-once cache function signatures (locks are internal)

## mypyc considerations

- `structural.py` is mypyc-compiled. The `PipelineContext` dataclass lives in
  `pipeline/__init__.py` (not compiled). mypyc handles external class instances
  as opaque objects — attribute access works via the Python fallback. The hot
  inner loops in the analyzer functions work on local variables, not context
  attributes, so the performance impact is negligible.

- `models/__init__.py` is mypyc-compiled. `threading.Lock` is a standard
  Python object — mypyc calls through the C API. The lock is never touched
  on the hot path (fast-path check returns before reaching the lock).
  **Important:** mypyc type-narrows `Optional` globals after a `None` check,
  so the standard double-checked locking re-check inside the lock hits a
  `TypeError` at runtime. The inner re-check is omitted in mypyc-compiled
  modules; worst case two threads both build on first call (idempotent).

- `registry.py` is not mypyc-compiled. No constraints.

## Thread-safety guarantees after this change

- **Concurrent `detect()` calls**: Safe. Each creates its own `PipelineContext`.
- **Load-once caches**: Safe under free-threaded Python (PEP 703). Worst case
  on first call: two threads both enter the lock, one waits, both get the
  same result.
- **`UniversalDetector`**: Individual instances are not thread-safe (mutable
  buffer state), but separate instances in separate threads are safe.
