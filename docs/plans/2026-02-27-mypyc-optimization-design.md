# mypyc Compilation for chardet-rewrite

## Goal

Compile the hot-path modules with mypyc to maximize detection speed on
CPython while keeping a pure Python fallback for PyPy and platforms without
prebuilt wheels. Zero runtime dependencies.

## Modules to Compile

| Module | Runtime share | Rationale |
|---|---|---|
| `models/__init__.py` | ~64% | `BigramProfile.__init__` + `_score_with_profile` — tight loops over bytes/dicts |
| `pipeline/structural.py` | ~5-10% | 9 byte-scanning state machines |
| `pipeline/validity.py` | ~5% | `filter_by_validity` loop with decode calls |
| `pipeline/statistical.py` | ~2% | `score_candidates` scoring orchestration |

### Excluded

- `__main__.py` — compiled modules can't run as scripts
- `cli.py` — entry point, no hot path
- `detector.py` — thin orchestration
- `pipeline/orchestrator.py` — complex control flow, minimal loop work
- Deterministic stages (bom, ascii, utf8, escape, markup, binary) — already near-instant
- `enums.py`, `equivalences.py`, `registry.py`, `pipeline/__init__.py` — no hot path

## Build System

Uses the `hatch-mypyc` plugin, following Black's proven pattern:

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

- Normal `pip install chardet` builds a pure Python wheel (hook disabled)
- `HATCH_BUILD_HOOKS_ENABLE=1 pip wheel .` builds a mypyc-compiled wheel
- `.py` files remain in the wheel for source inspection and type checking

### Wheel Publishing (future CI)

- cibuildwheel builds mypyc wheels for CPython 3.10-3.13 (Linux/macOS/Windows)
- A pure Python wheel is built separately for PyPy and exotic platforms
- Both uploaded to PyPI; pip picks the best match

## Code Changes

### Remove `from __future__ import annotations`

mypyc needs runtime type annotations, not PEP 563 stringified ones.
Remove this import from the 4 compiled modules only.

### Move `TYPE_CHECKING` imports to runtime

In `structural.py`, `validity.py`, and `statistical.py`, the `EncodingInfo`
import (and `Callable` in `structural.py`) is guarded behind
`if TYPE_CHECKING:`. mypyc needs these at runtime. Move them to
unconditional imports.

### No algorithmic changes

mypyc compiles the existing Python code to C extensions. The algorithms
remain identical — the speedup comes from native integer arithmetic,
optimized dict/bytearray operations, and elimination of interpreter overhead.

## Expected Results

- **Speedup:** 2-5x overall on CPython (scoring loop goes from interpreted
  Python to native C; structural byte-scanning loops similarly benefit)
- **Accuracy:** Identical (95.0%) — mypyc is semantically transparent
- **Pure Python fallback:** Identical behavior for PyPy and platforms
  without prebuilt wheels
- **Import time / memory:** Unchanged (mypyc doesn't affect import-time model
  loading or memory allocation patterns)

## Testing

All existing tests run unchanged against both compiled and pure Python
builds. The benchmark suite measures actual speedup. No new test files
needed.

- `pip install -e .` → pure Python (normal development)
- `HATCH_BUILD_HOOKS_ENABLE=1 pip install -e .` → compiled (performance testing)
