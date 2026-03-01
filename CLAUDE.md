# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MIT-licensed, ground-up rewrite of chardet (the Python character encoding detector). Drop-in replacement for chardet 6.x — same package name, same public API. Version 6.1.0+. Zero runtime dependencies, Python 3.10+, must work on PyPy.

## Commands

### Development Setup
```bash
uv sync                    # install dependencies
prek install               # set up pre-commit hooks (ruff lint+format, trailing whitespace, etc.)
```

### Testing
```bash
uv run python -m pytest                              # run all tests (excludes benchmarks)
uv run python -m pytest tests/test_api.py            # run a specific test file
uv run python -m pytest tests/test_api.py::test_detect_empty  # run a single test
uv run python -m pytest -m benchmark                 # run benchmark tests only
uv run python -m pytest -x                           # stop on first failure
```

Test data is auto-cloned from `chardet/test-data` GitHub repo on first run (cached in `tests/data/`, gitignored). Accuracy tests are dynamically parametrized from this data via `conftest.py`.

### Linting & Formatting
```bash
uv run ruff check .        # lint
uv run ruff check --fix .  # lint with auto-fix
uv run ruff format .       # format
```

### Training Models
```bash
uv run python scripts/train.py   # retrain bigram models from Wikipedia/HTML data
```

Training data is cached in `data/` (gitignored). Models are saved to `src/chardet/models/models.bin`.

### Benchmarks & Diagnostics
```bash
uv run python scripts/benchmark_time.py     # latency benchmarks
uv run python scripts/benchmark_memory.py   # memory usage benchmarks
uv run python scripts/diagnose_accuracy.py  # detailed accuracy diagnostics
uv run python scripts/compare_detectors.py  # compare against original chardet
```

### Documentation
```bash
uv sync --group docs                          # install Sphinx, Furo, etc.
uv run sphinx-build docs docs/_build          # build HTML docs
uv run sphinx-build -W docs docs/_build       # build with warnings as errors
uv run python scripts/generate_encoding_table.py > docs/supported-encodings.rst  # regenerate encoding table
```

Docs use Sphinx with Furo theme. API reference is auto-generated from source docstrings via autodoc. Published to ReadTheDocs on tag push (`.readthedocs.yaml`). Source files are in `docs/`; `docs/plans/` is excluded from the build.

### Building with mypyc (optional)
```bash
HATCH_BUILD_HOOK_ENABLE_MYPYC=true uv build  # compile hot-path modules
```

Only three modules are compiled: `models/__init__.py`, `pipeline/structural.py`, `pipeline/validity.py`, `pipeline/statistical.py`.

## Architecture

### Detection Pipeline (`src/chardet/pipeline/orchestrator.py`)

All detection flows through `run_pipeline()`, which runs stages in order — each stage either returns a definitive result or passes to the next:

1. **BOM** (`bom.py`) — byte order mark → confidence 1.0
2. **UTF-16/32 patterns** (`utf1632.py`) — null-byte patterns for BOM-less Unicode
3. **Escape sequences** (`escape.py`) — ISO-2022-JP/KR, HZ-GB-2312
4. **Binary detection** (`binary.py`) — null bytes / control chars → encoding=None
5. **Markup charset** (`markup.py`) — `<meta charset>` / `<?xml encoding>` extraction
6. **ASCII** (`ascii.py`) — pure 7-bit check
7. **UTF-8** (`utf8.py`) — structural multi-byte validation
8. **Byte validity** (`validity.py`) — eliminate encodings that can't decode the data
9. **CJK gating** (in orchestrator) — eliminate CJK candidates lacking multi-byte structure
10. **Structural probing** (`structural.py`) — score multi-byte encoding fit
11. **Statistical scoring** (`statistical.py`) — bigram frequency models for final ranking

### Key Types

- **`DetectionResult`** (`pipeline/__init__.py`) — frozen dataclass: `encoding`, `confidence`, `language`
- **`EncodingInfo`** (`registry.py`) — frozen dataclass: `name`, `aliases`, `era`, `is_multibyte`, `python_codec`
- **`EncodingEra`** (`enums.py`) — IntFlag for filtering candidates: `MODERN_WEB`, `LEGACY_ISO`, `LEGACY_MAC`, `LEGACY_REGIONAL`, `DOS`, `MAINFRAME`, `ALL`
- **`BigramProfile`** (`models/__init__.py`) — pre-computed weighted bigram frequencies, computed once and reused across all candidate models

### Model Format

Binary file `src/chardet/models/models.bin` — sparse bigram tables loaded via `struct.unpack`. Each model is a 65536-byte lookup table indexed by `(b1 << 8) | b2`. Model keys use `language/encoding` format (e.g., `French/windows-1252`). Loaded lazily on first `detect()` call and cached.

### Public API (`src/chardet/__init__.py`)

- `detect(data, max_bytes, chunk_size, encoding_era)` → `{"encoding": ..., "confidence": ..., "language": ...}`
- `detect_all(...)` → list of result dicts
- `UniversalDetector` (`detector.py`) — streaming interface with `feed()`/`close()`/`reset()`

### Encoding Equivalences (`equivalences.py`)

Defines acceptable detection mismatches for accuracy testing: directional supersets (e.g., utf-8 is acceptable when ascii is expected) and bidirectional equivalents (UTF-16/32 endian variants). Used by `tests/test_accuracy.py` and diagnostic scripts.

### Scripts

`scripts/` directory contains training, benchmarking, and diagnostic tools. `scripts/utils.py` provides shared utilities (e.g., `collect_test_files()`) imported by both tests and scripts.

## Conventions

- Ruff with `select = ["ALL"]` and targeted ignores — check `pyproject.toml` for the full ignore list
- `from __future__ import annotations` in all source files
- Frozen dataclasses with `slots=True` for data types
- Era assignments in `registry.py` match chardet 6.0.0
- Training data (Wikipedia/HTML) is never the same as evaluation data (chardet test suite)
