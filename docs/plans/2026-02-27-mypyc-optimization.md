# mypyc Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Compile chardet's hot-path modules with mypyc to maximize detection speed on CPython, with pure Python fallback for PyPy.

**Architecture:** Use the hatch-mypyc build plugin (same pattern as Black). Four modules are compiled: `models/__init__.py`, `pipeline/structural.py`, `pipeline/validity.py`, `pipeline/statistical.py`. The compilation is disabled by default and activated via `HATCH_BUILD_HOOKS_ENABLE=1`.

**Tech Stack:** hatch-mypyc, mypy (build-time only), cibuildwheel (future CI)

**Design doc:** `docs/plans/2026-02-27-mypyc-optimization-design.md`

---

### Task 1: Baseline benchmark

Establish a reproducible performance baseline before any changes.

**Files:**
- None (read-only)

**Step 1: Run benchmark and record baseline**

Run:
```bash
python scripts/benchmark.py --test-dir tests/data 2>&1 | tail -20
```

Record the total time, accuracy, mean, median, p90, p95 values. These are
the "before" numbers. Write them down in a comment or note for comparison
in Task 7.

**Step 2: Run existing tests to confirm green baseline**

Run:
```bash
pytest tests/ --ignore=tests/test_accuracy.py --ignore=tests/test_cjk_gating.py -q
```

Expected: All tests pass. (`test_accuracy.py` and `test_cjk_gating.py` have
pre-existing failures unrelated to this work.)

---

### Task 2: Prepare `models/__init__.py` for mypyc

Remove `from __future__ import annotations` and update type annotations to
use runtime-compatible syntax. mypyc needs real type objects at runtime, not
stringified annotations.

**Files:**
- Modify: `src/chardet/models/__init__.py`

**Step 1: Remove future annotations import**

In `src/chardet/models/__init__.py`, remove line 3:
```python
from __future__ import annotations
```

**Step 2: Update type annotations to runtime-compatible syntax**

Replace PEP 604 union syntax (`X | Y`) with `Optional`/`Union` from
`typing` for Python 3.10 compatibility under mypyc:

- Line 8: `dict[str, bytearray] | None` → `Optional[dict[str, bytearray]]`
- Line 10: `dict[str, list[tuple[str, bytearray]]] | None` →
  `Optional[dict[str, list[tuple[str, bytearray]]]]`
- Line 89: `dict[int, int] = {}` — fine as-is (no union)
- Line 90: `int = 0` — fine as-is
- Line 141: `BigramProfile | None = None` → `Optional[BigramProfile]`
- Line 142: `tuple[float, str | None]` → `Tuple[float, Optional[str]]`

Add at the top:
```python
from typing import Optional, Tuple
```

Also update the `# noqa: ARG001` comment on line 140 — it stays as-is
since mypyc doesn't care about ruff annotations.

**Step 3: Run tests**

Run:
```bash
pytest tests/test_models.py tests/test_statistical.py tests/test_api.py -q
```

Expected: All pass (pure Python, no mypyc yet).

**Step 4: Commit**

```bash
git add src/chardet/models/__init__.py
git commit -m "refactor: prepare models module for mypyc compilation"
```

---

### Task 3: Prepare `pipeline/structural.py` for mypyc

**Files:**
- Modify: `src/chardet/pipeline/structural.py`

**Step 1: Remove future annotations and fix imports**

In `src/chardet/pipeline/structural.py`:

1. Remove line 8: `from __future__ import annotations`
2. Remove the `TYPE_CHECKING` guard (lines 10-14). Replace with
   unconditional imports:
   ```python
   from collections.abc import Callable

   from chardet.registry import EncodingInfo
   ```

**Step 2: Run tests**

Run:
```bash
pytest tests/test_structural.py -q
```

Expected: All pass.

**Step 3: Commit**

```bash
git add src/chardet/pipeline/structural.py
git commit -m "refactor: prepare structural module for mypyc compilation"
```

---

### Task 4: Prepare `pipeline/validity.py` for mypyc

**Files:**
- Modify: `src/chardet/pipeline/validity.py`

**Step 1: Remove future annotations and fix imports**

In `src/chardet/pipeline/validity.py`:

1. Remove line 2: `from __future__ import annotations`
2. Remove the `TYPE_CHECKING` guard (lines 4-8). Replace with:
   ```python
   from chardet.registry import EncodingInfo
   ```

**Step 2: Run tests**

Run:
```bash
pytest tests/test_validity.py -q
```

Expected: All pass.

**Step 3: Commit**

```bash
git add src/chardet/pipeline/validity.py
git commit -m "refactor: prepare validity module for mypyc compilation"
```

---

### Task 5: Prepare `pipeline/statistical.py` for mypyc

**Files:**
- Modify: `src/chardet/pipeline/statistical.py`

**Step 1: Remove future annotations and fix imports**

In `src/chardet/pipeline/statistical.py`:

1. Remove line 2: `from __future__ import annotations`
2. Remove the `TYPE_CHECKING` guard (lines 5-6, 10-11). Replace with:
   ```python
   from chardet.registry import EncodingInfo
   ```

**Step 2: Update any PEP 604 annotations**

Check for `str | None` or similar and replace with `Optional[str]` if
present. The `score_best_language` return type `tuple[float, str | None]`
is called from this module — but since it's in `models/__init__.py`
(already updated in Task 2), no changes needed here unless ruff adds
return annotations.

**Step 3: Run tests**

Run:
```bash
pytest tests/test_statistical.py -q
```

Expected: All pass.

**Step 4: Commit**

```bash
git add src/chardet/pipeline/statistical.py
git commit -m "refactor: prepare statistical module for mypyc compilation"
```

---

### Task 6: Add hatch-mypyc build configuration

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add mypyc hook configuration to pyproject.toml**

Add the following section after the existing `[tool.hatch.build.targets.wheel]`
section:

```toml
[tool.hatch.build.targets.wheel.hooks.mypyc]
enable-by-default = false
dependencies = ["hatch-mypyc>=0.16.0", "mypy>=1.15"]
require-runtime-dependencies = false
exclude = [
    "/src/chardet/__init__.py",
    "/src/chardet/__main__.py",
    "/src/chardet/cli.py",
    "/src/chardet/detector.py",
    "/src/chardet/enums.py",
    "/src/chardet/equivalences.py",
    "/src/chardet/registry.py",
    "/src/chardet/pipeline/__init__.py",
    "/src/chardet/pipeline/ascii.py",
    "/src/chardet/pipeline/binary.py",
    "/src/chardet/pipeline/bom.py",
    "/src/chardet/pipeline/escape.py",
    "/src/chardet/pipeline/markup.py",
    "/src/chardet/pipeline/orchestrator.py",
    "/src/chardet/pipeline/utf1632.py",
    "/src/chardet/pipeline/utf8.py",
]
mypy-args = ["--ignore-missing-imports"]
options = { debug_level = "0" }
```

**Step 2: Verify pure-Python build still works**

Run:
```bash
pip install -e .
pytest tests/test_models.py tests/test_statistical.py tests/test_api.py -q
```

Expected: All pass. The mypyc hook is disabled by default, so this is a
normal pure-Python install.

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: add hatch-mypyc configuration for optional compilation"
```

---

### Task 7: Build and test mypyc-compiled wheel

**Files:**
- None (build/test only)

**Step 1: Install build dependencies**

Run:
```bash
uv pip install hatch-mypyc mypy
```

**Step 2: Build mypyc-compiled wheel**

Run:
```bash
HATCH_BUILD_HOOKS_ENABLE=1 pip install -e .
```

If this fails, the error will indicate which module or annotation is
incompatible. Fix the issue in the relevant module (refer back to Tasks
2-5) and retry.

Common mypyc issues to watch for:
- `from __future__ import annotations` not removed (Task 2-5)
- `Callable` type not imported at runtime (Task 3)
- Unsupported Python features (unlikely given the simple code)

**Step 3: Run all tests with compiled modules**

Run:
```bash
pytest tests/ --ignore=tests/test_accuracy.py --ignore=tests/test_cjk_gating.py -q
```

Expected: All pass — identical behavior to pure Python.

**Step 4: Run benchmark and compare**

Run:
```bash
python scripts/benchmark.py --test-dir tests/data 2>&1 | tail -20
```

Compare total time, mean, median, p90, p95 against the baseline from
Task 1. Expected: 2-5x speedup on total time.

**Step 5: Verify accuracy is unchanged**

Run:
```bash
python scripts/benchmark.py --test-dir tests/data 2>&1 | grep -i accur
```

Expected: 95.0% (identical to baseline).

**Step 6: Commit (if any fixes were needed)**

If you had to fix mypyc compatibility issues, commit those fixes:
```bash
git add -A
git commit -m "fix: resolve mypyc compilation issues"
```

---

### Task 8: Update performance report and design doc

**Files:**
- Modify: `docs/rewrite_performance.md`
- Modify: `docs/plans/2026-02-27-mypyc-optimization-design.md`

**Step 1: Update performance report**

Add a note to `docs/rewrite_performance.md` about the mypyc-compiled
performance numbers. Update the detection time for the rewrite if the
mypyc build is significantly faster.

**Step 2: Update design doc with actual results**

In `docs/plans/2026-02-27-mypyc-optimization-design.md`, replace the
"Expected Results" section with actual measured speedup numbers.

**Step 3: Commit**

```bash
git add docs/rewrite_performance.md docs/plans/2026-02-27-mypyc-optimization-design.md
git commit -m "docs: update performance report with mypyc benchmark results"
```
