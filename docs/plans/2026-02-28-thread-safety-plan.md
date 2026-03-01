# Thread-Safety Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make chardet safe under concurrent `detect()` calls by eliminating module-level mutable per-run state and adding double-checked locking to load-once caches.

**Architecture:** Two complementary mechanisms — (1) a `PipelineContext` dataclass carries per-run mutable state through the call chain instead of module globals, and (2) five load-once caches get `threading.Lock` with double-checked locking for safe lazy initialization.

**Tech Stack:** Python 3.10+, dataclasses, threading.Lock, mypyc (structural.py is compiled)

**Reference:** `docs/plans/2026-02-28-thread-safety-design.md`

---

### Task 1: Add `PipelineContext` dataclass to `pipeline/__init__.py`

**Why:** This is the per-run state container that replaces module-level `_analysis_cache`. It must exist before any consumer can use it.

**Files:**
- Modify: `src/chardet/pipeline/__init__.py`
- Create: `tests/test_pipeline_types.py` (append new test)

**Step 1: Write the failing test**

Append to `tests/test_pipeline_types.py`:

```python
from chardet.pipeline import PipelineContext


def test_pipeline_context_defaults():
    ctx = PipelineContext()
    assert ctx.analysis_cache == {}
    assert ctx.non_ascii_count == -1
    assert ctx.mb_scores == {}


def test_pipeline_context_is_mutable():
    ctx = PipelineContext()
    ctx.analysis_cache[(123, 5, "utf-8")] = (0.9, 10, 5)
    ctx.non_ascii_count = 42
    ctx.mb_scores["shift_jis"] = 0.85
    assert ctx.analysis_cache[(123, 5, "utf-8")] == (0.9, 10, 5)
    assert ctx.non_ascii_count == 42
    assert ctx.mb_scores["shift_jis"] == 0.85
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_pipeline_types.py::test_pipeline_context_defaults tests/test_pipeline_types.py::test_pipeline_context_is_mutable -v`
Expected: FAIL with `ImportError: cannot import name 'PipelineContext'`

**Step 3: Write minimal implementation**

In `src/chardet/pipeline/__init__.py`, add after the existing `DetectionResult` class:

```python
from dataclasses import field


@dataclasses.dataclass(slots=True)
class PipelineContext:
    """Per-run mutable state for a single pipeline invocation.

    Created once at the start of ``run_pipeline()`` and threaded through
    the call chain via function parameters.  Each concurrent ``detect()``
    call gets its own context, eliminating the need for module-level
    mutable caches.
    """

    analysis_cache: dict[tuple[int, int, str], tuple[float, int, int]] = field(
        default_factory=dict
    )
    non_ascii_count: int = -1
    mb_scores: dict[str, float] = field(default_factory=dict)
```

Note: This file uses `from __future__ import annotations` (it is NOT mypyc-compiled), so string annotations are fine.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pipeline_types.py -v`
Expected: PASS

**Step 5: Commit**

```
feat: add PipelineContext dataclass for per-run pipeline state
```

---

### Task 2: Thread `PipelineContext` through `structural.py`

**Why:** Replace the module-level `_analysis_cache` dict and `clear_analysis_cache()` with a `ctx` parameter on all functions that read/write the cache. This is the core change that makes per-run state safe.

**Files:**
- Modify: `src/chardet/pipeline/structural.py:310-334,341,357,393` — remove module global, add `ctx` param
- Modify: `tests/test_structural.py` — pass `PipelineContext()` to all calls

**IMPORTANT:** `structural.py` is mypyc-compiled. It does NOT use `from __future__ import annotations`. The `PipelineContext` import is from a non-compiled module, so mypyc treats it as an opaque Python object. Attribute access works via Python fallback.

**Step 1: Update `structural.py`**

1. Add import at top (after existing imports):
   ```python
   from chardet.pipeline import PipelineContext
   ```

2. Delete lines 299-333 (the `_analysis_cache` global, `_get_analysis()`, and `clear_analysis_cache()`).

3. Replace `_get_analysis()` with a version that takes `ctx`:
   ```python
   def _get_analysis(
       data: bytes, name: str, ctx: PipelineContext
   ) -> tuple[float, int, int] | None:
       """Return cached analysis or compute and cache it."""
       key = (id(data), len(data), name)
       cached = ctx.analysis_cache.get(key)
       if cached is not None:
           return cached
       analyzer = _ANALYZERS.get(name)
       if analyzer is None:
           return None
       result = analyzer(data)
       ctx.analysis_cache[key] = result
       return result
   ```

4. Update `compute_structural_score()` signature and body:
   ```python
   def compute_structural_score(
       data: bytes, encoding_info: EncodingInfo, ctx: PipelineContext
   ) -> float:
   ```
   Change the `_get_analysis(data, encoding_info.name)` call to `_get_analysis(data, encoding_info.name, ctx)`.

5. Update `compute_multibyte_byte_coverage()` signature and body:
   ```python
   def compute_multibyte_byte_coverage(
       data: bytes,
       encoding_info: EncodingInfo,
       ctx: PipelineContext,
       non_ascii_count: int = -1,
   ) -> float:
   ```
   Change the `_get_analysis(data, encoding_info.name)` call to `_get_analysis(data, encoding_info.name, ctx)`.

6. Update `compute_lead_byte_diversity()` signature and body:
   ```python
   def compute_lead_byte_diversity(
       data: bytes, encoding_info: EncodingInfo, ctx: PipelineContext
   ) -> int:
   ```
   Change the `_get_analysis(data, encoding_info.name)` call to `_get_analysis(data, encoding_info.name, ctx)`.

**Step 2: Update `tests/test_structural.py`**

Add import and pass `PipelineContext()` to every `compute_structural_score` call:

```python
from chardet.pipeline import PipelineContext
from chardet.pipeline.structural import compute_structural_score
from chardet.registry import REGISTRY


def _get_encoding(name: str):
    return next(e for e in REGISTRY if e.name == name)


def test_shift_jis_scores_high_on_shift_jis_data():
    data = "こんにちは世界".encode("shift_jis")
    score = compute_structural_score(data, _get_encoding("shift_jis"), PipelineContext())
    assert score > 0.7


def test_euc_jp_scores_high_on_euc_jp_data():
    data = "こんにちは世界".encode("euc-jp")
    score = compute_structural_score(data, _get_encoding("euc-jp"), PipelineContext())
    assert score > 0.7


def test_shift_jis_scores_low_on_euc_jp_data():
    ctx = PipelineContext()
    data = "こんにちは世界".encode("euc-jp")
    euc_score = compute_structural_score(data, _get_encoding("euc-jp"), ctx)
    sjis_score = compute_structural_score(data, _get_encoding("shift_jis"), ctx)
    assert euc_score > sjis_score


def test_euc_kr_scores_high_on_korean_data():
    data = "안녕하세요".encode("euc-kr")
    score = compute_structural_score(data, _get_encoding("euc-kr"), PipelineContext())
    assert score > 0.7


def test_gb18030_scores_high_on_chinese_data():
    data = "你好世界".encode("gb18030")
    score = compute_structural_score(data, _get_encoding("gb18030"), PipelineContext())
    assert score > 0.7


def test_big5_scores_high_on_big5_data():
    data = "你好世界".encode("big5")
    score = compute_structural_score(data, _get_encoding("big5"), PipelineContext())
    assert score > 0.7


def test_single_byte_encoding_returns_zero():
    data = b"Hello world"
    enc = _get_encoding("iso-8859-1")
    score = compute_structural_score(data, enc, PipelineContext())
    assert score == 0.0


def test_empty_data_returns_zero():
    score = compute_structural_score(b"", _get_encoding("shift_jis"), PipelineContext())
    assert score == 0.0
```

**Step 3: Run tests to verify**

Run: `uv run pytest tests/test_structural.py -v`
Expected: PASS

**Step 4: Commit**

```
refactor: thread PipelineContext through structural.py, remove module-level cache
```

---

### Task 3: Thread `PipelineContext` through `orchestrator.py`

**Why:** The orchestrator creates the `PipelineContext` and passes it to all structural scoring functions. This also deletes the `clear_analysis_cache()` import and call, and updates `_gate_cjk_candidates()` to write to the context.

**Files:**
- Modify: `src/chardet/pipeline/orchestrator.py`

**Step 1: Update imports**

Replace:
```python
from chardet.pipeline import DetectionResult
```
with:
```python
from chardet.pipeline import DetectionResult, PipelineContext
```

Remove from the structural imports:
```python
    clear_analysis_cache,
```

So the structural import becomes:
```python
from chardet.pipeline.structural import (
    compute_lead_byte_diversity,
    compute_multibyte_byte_coverage,
    compute_structural_score,
)
```

**Step 2: Update `_gate_cjk_candidates()` signature**

Change signature from:
```python
def _gate_cjk_candidates(
    data: bytes,
    valid_candidates: tuple[EncodingInfo, ...],
) -> tuple[tuple[EncodingInfo, ...], dict[str, float]]:
```
to:
```python
def _gate_cjk_candidates(
    data: bytes,
    valid_candidates: tuple[EncodingInfo, ...],
    ctx: PipelineContext,
) -> tuple[EncodingInfo, ...]:
```

**Step 3: Update `_gate_cjk_candidates()` body**

- Remove the local `non_ascii_count = -1` and `mb_scores: dict[str, float] = {}` lines.
- Replace `mb_scores[enc.name] = mb_score` with `ctx.mb_scores[enc.name] = mb_score`.
- Replace `non_ascii_count` reads/writes with `ctx.non_ascii_count`.
- Pass `ctx` to all `compute_structural_score()`, `compute_multibyte_byte_coverage()`, and `compute_lead_byte_diversity()` calls.
- Change return from `return tuple(gated), mb_scores` to `return tuple(gated)`.

Updated body:
```python
    gated: list[EncodingInfo] = []
    for enc in valid_candidates:
        if enc.is_multibyte:
            mb_score = compute_structural_score(data, enc, ctx)
            ctx.mb_scores[enc.name] = mb_score
            if mb_score < _CJK_MIN_MB_RATIO:
                continue
            if ctx.non_ascii_count < 0:
                ctx.non_ascii_count = len(data) - len(
                    data.translate(None, _HIGH_BYTES)
                )
            if ctx.non_ascii_count < _CJK_MIN_NON_ASCII:
                continue
            byte_coverage = compute_multibyte_byte_coverage(
                data, enc, ctx, non_ascii_count=ctx.non_ascii_count
            )
            if byte_coverage < _CJK_MIN_BYTE_COVERAGE:
                continue
            if ctx.non_ascii_count >= _CJK_DIVERSITY_MIN_NON_ASCII:
                lead_diversity = compute_lead_byte_diversity(data, enc, ctx)
                if lead_diversity < _CJK_MIN_LEAD_DIVERSITY:
                    continue
        gated.append(enc)
    return tuple(gated)
```

**Step 4: Update `_run_pipeline_core()`**

Replace:
```python
    clear_analysis_cache()
    data = data[:max_bytes]
```
with:
```python
    ctx = PipelineContext()
    data = data[:max_bytes]
```

Replace:
```python
    valid_candidates, mb_scores = _gate_cjk_candidates(data, valid_candidates)
```
with:
```python
    valid_candidates = _gate_cjk_candidates(data, valid_candidates, ctx)
```

Replace:
```python
            score = mb_scores.get(enc.name)
```
with:
```python
            score = ctx.mb_scores.get(enc.name)
```

Replace:
```python
                score = compute_structural_score(data, enc)
```
with:
```python
                score = compute_structural_score(data, enc, ctx)
```

**Step 5: Run all tests to verify**

Run: `uv run pytest tests/ -q --tb=short --ignore=tests/test_accuracy.py`
Expected: All tests pass (277 passed).

**Step 6: Commit**

```
refactor: create PipelineContext in orchestrator, thread through call chain
```

---

### Task 4: Add double-checked locking to `models/__init__.py`

**Why:** Three load-once caches (`_MODEL_CACHE`, `_ENC_INDEX`, `_MODEL_NORMS`) are populated on first use and never modified again, but are not thread-safe during initial population.

**Files:**
- Modify: `src/chardet/models/__init__.py:1-161`

**IMPORTANT:** This file is mypyc-compiled and does NOT use `from __future__ import annotations`. `threading.Lock` is a standard Python object — mypyc calls through the C API.

**Step 1: Add threading import**

After `import struct`, add:
```python
import threading
```

**Step 2: Add locks after each cache declaration**

After line 12 (`_MODEL_CACHE`), add:
```python
_MODEL_CACHE_LOCK = threading.Lock()
```

After line 14 (`_ENC_INDEX`), add:
```python
_ENC_INDEX_LOCK = threading.Lock()
```

After line 16 (`_MODEL_NORMS`), add:
```python
_MODEL_NORMS_LOCK = threading.Lock()
```

**Step 3: Update `load_models()`**

```python
def load_models() -> dict[str, bytearray]:
    global _MODEL_CACHE  # noqa: PLW0603
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    with _MODEL_CACHE_LOCK:
        if _MODEL_CACHE is not None:
            return _MODEL_CACHE

        models: dict[str, bytearray] = {}
        ref = importlib.resources.files("chardet.models").joinpath("models.bin")
        data = ref.read_bytes()

        if not data:
            _MODEL_CACHE = models
            return models

        try:
            offset = 0
            (num_encodings,) = struct.unpack_from("!I", data, offset)
            offset += 4

            if num_encodings > 10_000:
                msg = f"corrupt models.bin: num_encodings={num_encodings} exceeds limit"
                raise ValueError(msg)

            for _ in range(num_encodings):
                (name_len,) = struct.unpack_from("!I", data, offset)
                offset += 4
                name = data[offset : offset + name_len].decode("utf-8")
                offset += name_len
                (num_entries,) = struct.unpack_from("!I", data, offset)
                offset += 4

                table = bytearray(65536)
                for _ in range(num_entries):
                    b1, b2, weight = struct.unpack_from("!BBB", data, offset)
                    offset += 3
                    table[(b1 << 8) | b2] = weight
                models[name] = table
        except (struct.error, UnicodeDecodeError) as e:
            msg = f"corrupt models.bin: {e}"
            raise ValueError(msg) from e

        _MODEL_CACHE = models
        return models
```

**Step 4: Update `_get_enc_index()`**

```python
def _get_enc_index() -> dict[str, list[tuple[str | None, bytearray]]]:
    global _ENC_INDEX  # noqa: PLW0603
    if _ENC_INDEX is not None:
        return _ENC_INDEX
    with _ENC_INDEX_LOCK:
        if _ENC_INDEX is not None:
            return _ENC_INDEX
        models = load_models()
        index: dict[str, list[tuple[str | None, bytearray]]] = {}
        for key, model in models.items():
            if "/" in key:
                lang, enc = key.split("/", 1)
                index.setdefault(enc, []).append((lang, model))
            else:
                index.setdefault(key, []).append((None, model))
        _ENC_INDEX = index
        return index
```

**Step 5: Update `_get_model_norms()`**

```python
def _get_model_norms() -> dict[int, float]:
    global _MODEL_NORMS  # noqa: PLW0603
    if _MODEL_NORMS is not None:
        return _MODEL_NORMS
    with _MODEL_NORMS_LOCK:
        if _MODEL_NORMS is not None:
            return _MODEL_NORMS
        models = load_models()
        norms: dict[int, float] = {}
        for model in models.values():
            mid = id(model)
            if mid not in norms:
                sq_sum = 0
                for i in range(65536):
                    v = model[i]
                    if v:
                        sq_sum += v * v
                norms[mid] = math.sqrt(sq_sum)
        _MODEL_NORMS = norms
        return norms
```

**Step 6: Run tests**

Run: `uv run pytest tests/test_models.py tests/test_statistical.py -q --tb=short`
Expected: PASS

**Step 7: Commit**

```
fix: add double-checked locking to model caches for thread safety
```

---

### Task 5: Add double-checked locking to `confusion.py` and `registry.py`

**Why:** Two more load-once caches need the same treatment: `_CONFUSION_CACHE` in confusion.py and `_CANDIDATES_CACHE` in registry.py.

**Files:**
- Modify: `src/chardet/pipeline/confusion.py:60,99-112`
- Modify: `src/chardet/registry.py:21,24-31`

**Step 1: Update `confusion.py`**

Add `import threading` at the top of the file (after existing imports like `import struct`).

After line 60 (`_CONFUSION_CACHE: DistinguishingMaps | None = None`), add:
```python
_CONFUSION_CACHE_LOCK = threading.Lock()
```

Update `load_confusion_data()`:
```python
def load_confusion_data() -> DistinguishingMaps:
    """Load confusion group data from the bundled confusion.bin file."""
    global _CONFUSION_CACHE  # noqa: PLW0603
    if _CONFUSION_CACHE is not None:
        return _CONFUSION_CACHE
    with _CONFUSION_CACHE_LOCK:
        if _CONFUSION_CACHE is not None:
            return _CONFUSION_CACHE
        import importlib.resources

        ref = importlib.resources.files("chardet.models").joinpath("confusion.bin")
        raw = ref.read_bytes()
        if not raw:
            _CONFUSION_CACHE = {}
            return _CONFUSION_CACHE
        _CONFUSION_CACHE = deserialize_confusion_data_from_bytes(raw)
        return _CONFUSION_CACHE
```

**Step 2: Update `registry.py`**

Add `import threading` after existing imports.

After line 21 (`_CANDIDATES_CACHE: dict[int, tuple[EncodingInfo, ...]] = {}`), add:
```python
_CANDIDATES_CACHE_LOCK = threading.Lock()
```

Update `get_candidates()`:
```python
def get_candidates(era: EncodingEra) -> tuple[EncodingInfo, ...]:
    """Return registry entries matching the given era filter."""
    key = int(era)
    result = _CANDIDATES_CACHE.get(key)
    if result is not None:
        return result
    with _CANDIDATES_CACHE_LOCK:
        result = _CANDIDATES_CACHE.get(key)
        if result is not None:
            return result
        result = tuple(enc for enc in REGISTRY if enc.era & era)
        _CANDIDATES_CACHE[key] = result
        return result
```

Note: `_CANDIDATES_CACHE` is a dict (not `None | dict`), so the double-check uses `.get(key)` instead of `is not None`. This cache stores per-era results, so multiple keys can be populated.

**Step 3: Run tests**

Run: `uv run pytest tests/test_confusion.py tests/test_registry.py tests/test_api.py -q --tb=short`
Expected: PASS

**Step 4: Commit**

```
fix: add double-checked locking to confusion and registry caches
```

---

### Task 6: Add thread-safety integration test

**Why:** Verify that concurrent `detect()` calls don't corrupt results.

**Files:**
- Create: `tests/test_thread_safety.py`

**Step 1: Write the test**

```python
"""Thread-safety integration tests for concurrent detect() calls."""

from __future__ import annotations

import threading

from chardet import detect
from chardet.enums import EncodingEra


def test_concurrent_detect_no_corruption():
    """Multiple threads calling detect() simultaneously must not corrupt results."""
    japanese = "これはテストです。日本語のテキスト。".encode("shift_jis")
    german = "Ä Ö Ü ä ö ü ß — deutsche Umlaute und Sonderzeichen".encode("windows-1252")
    chinese = "这是中文测试文本，用于并发检测。".encode("gb18030")
    samples = [japanese, german, chinese]

    errors: list[str] = []
    barrier = threading.Barrier(len(samples) * 3)

    def worker(data: bytes, expected_encodings: frozenset[str]) -> None:
        barrier.wait()
        for _ in range(20):
            result = detect(data, encoding_era=EncodingEra.ALL)
            enc = result["encoding"]
            if enc is not None:
                enc = enc.lower()
            if enc not in expected_encodings:
                errors.append(
                    f"Expected one of {expected_encodings}, got {enc!r}"
                )

    threads = []
    expectations = [
        frozenset({"shift_jis", "cp932"}),
        frozenset({"windows-1252", "iso-8859-1", "iso-8859-15", "iso-8859-9", "windows-1254"}),
        frozenset({"gb18030", "gb2312"}),
    ]
    for _ in range(3):
        for data, expected in zip(samples, expectations, strict=True):
            t = threading.Thread(target=worker, args=(data, expected))
            threads.append(t)
            t.start()

    for t in threads:
        t.join()

    assert not errors, f"Thread-safety violations:\n" + "\n".join(errors[:10])
```

**Step 2: Run the test**

Run: `uv run pytest tests/test_thread_safety.py -v`
Expected: PASS

**Step 3: Commit**

```
test: add thread-safety integration test for concurrent detect()
```

---

### Task 7: Final verification

**Step 1: Run full test suite**

```bash
uv run pytest tests/ -q --tb=short --ignore=tests/test_accuracy.py
```
Expected: All tests pass.

**Step 2: Run accuracy tests**

```bash
uv run pytest tests/test_accuracy.py -q --tb=no 2>&1 | tail -3
```
Expected: Same 78 failures, 174 language warnings as before.

**Step 3: Run linter**

```bash
uv run ruff check src/chardet/
```
Expected: No errors.

**Step 4: Build and test with mypyc**

```bash
HATCH_BUILD_HOOK_ENABLE_MYPYC=true uv build
uv pip install dist/chardet-*.whl --force-reinstall
uv run --no-project python -c "import chardet; print(chardet.detect(b'Hello world'))"
uv run --no-project python -c "from chardet.pipeline.structural import compute_structural_score; print('OK')"
```
Expected: Both commands succeed. The first prints a detection result, the second prints `OK`.

**Step 5: Run thread-safety test against mypyc build**

```bash
uv run --no-project python -m pytest tests/test_thread_safety.py -v
```
Expected: PASS

**Step 6: Commit (if any fixups needed)**

If any fixes were needed in this step, commit them as:
```
fix: address verification issues from thread-safety implementation
```
