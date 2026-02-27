# Chardet Rewrite Design

## Overview

A ground-up, MIT-licensed rewrite of chardet that is API-compatible with chardet
6.x. This replaces the original LGPL chardet with independently trained
statistical models and clean-room detection algorithms. No GPL/LGPL code is used.

## Requirements

1. API-compatible with chardet 6.x public API (`detect()`, `detect_all()`,
   `UniversalDetector`, `EncodingEra`, `chardetect` CLI)
2. Package is named `chardet` — this is a drop-in replacement
3. MIT licensed, no GPL/LGPL code
4. High encoding accuracy on the chardet test suite
5. Language detection included as a byproduct of encoding detection (not a
   primary goal)
6. High performance: optimize for detection speed, lower memory usage
7. Zero runtime dependencies (dev/training dependencies are fine)
8. Must work on PyPy, primarily optimized for CPython
9. Modern Python project setup (uv, ruff, pytest, pre-commit)
10. Python 3.10+ minimum
11. Hugging Face `datasets` library for training data access
12. Local caching of training data for fast retraining
13. Regular benchmarking during development
14. No giant dict literals for models (avoids CPython 3.12 `sys.settrace` bug)
15. Version starts at 6.1.0 or higher

## Project Structure

```
chardet/
├── pyproject.toml
├── src/
│   └── chardet/
│       ├── __init__.py          # Public API: detect(), detect_all(), version
│       ├── enums.py             # EncodingEra (IntFlag for bitwise OR)
│       ├── detector.py          # UniversalDetector class
│       ├── cli.py               # chardetect entry point
│       ├── registry.py          # Encoding metadata registry
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── binary.py        # Stage 0: Binary content detection
│       │   ├── bom.py           # Stage 1: BOM detection
│       │   ├── ascii.py         # Stage 1: Pure ASCII check
│       │   ├── utf8.py          # Stage 1: UTF-8 structural validation
│       │   ├── markup.py        # Stage 1: HTML/XML charset extraction
│       │   ├── validity.py      # Stage 2a: Byte sequence validity checking
│       │   ├── structural.py    # Stage 2b: Multi-byte structural probing
│       │   └── statistical.py   # Stage 3: Bigram frequency scoring
│       └── models/
│           ├── __init__.py      # Model loading utilities (struct.unpack)
│           └── models.bin       # Bundled sparse bigram frequency tables
├── tests/
│   ├── test_api.py              # Public API contract tests
│   ├── test_pipeline.py         # Per-stage unit tests
│   ├── test_accuracy.py         # Chardet test suite evaluation
│   └── test_benchmark.py        # Performance regression tests
├── scripts/
│   ├── train.py                 # Model training from Wikipedia + HTML data
│   └── benchmark.py             # Benchmark suite
└── docs/
    └── plans/
```

Tooling: `uv` for dependency management, `ruff` for lint/format, `pytest` for
testing, `pre-commit` for hooks. No runtime dependencies. Dev dependencies:
`pytest`, `pytest-cov`, `ruff`, `datasets` (Hugging Face), `pre-commit`.

## Public API

### `detect()` and `detect_all()`

```python
from chardet.enums import EncodingEra

def detect(
    data: bytes,
    max_bytes: int = 200_000,
    chunk_size: int = 65_536,
    encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
) -> dict:
    """Returns {'encoding': str | None, 'confidence': float, 'language': str | None}"""

def detect_all(
    data: bytes,
    max_bytes: int = 200_000,
    chunk_size: int = 65_536,
    encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
) -> list[dict]:
    """Returns list of candidates sorted by confidence descending."""
```

### `UniversalDetector`

```python
class UniversalDetector:
    def __init__(
        self,
        encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
        max_bytes: int = 200_000,
    ) -> None: ...

    def feed(self, data: bytes) -> None: ...
    def close(self) -> None: ...
    def reset(self) -> None: ...

    @property
    def done(self) -> bool: ...

    @property
    def result(self) -> dict: ...
```

### `EncodingEra`

```python
class EncodingEra(enum.IntFlag):
    MODERN_WEB = ...
    LEGACY_ISO = ...
    LEGACY_MAC = ...
    LEGACY_REGIONAL = ...
    DOS = ...
    MAINFRAME = ...
    ALL = ...  # Combination of all flags
```

### `chardetect` CLI

Entry point registered in `pyproject.toml`. Accepts file paths, `--minimal`,
`--legacy`, `-e/--encoding-era`, `--version`. Reads stdin if no files given.

### `language` field

Populated as a byproduct when training data associates an encoding+frequency
profile with a language. Returns `None` when language can't be determined with
confidence.

## Detection Pipeline

### Stage 0 — Binary Detection

Scan input (up to `max_bytes`) for binary content indicators:

- High concentration of null bytes (>1% suggests binary)
- Control characters outside common text range (0x00-0x08, 0x0E-0x1F excluding
  tab/newline/carriage return)

If the ratio of binary indicator bytes exceeds a threshold, return
`{'encoding': None, 'confidence': 0.0, 'language': None}` immediately.

### Stage 1 — Deterministic Checks (no models, instant)

Each check returns a confident result or `None` to pass to the next stage:

1. **BOM detection** (`bom.py`): Check first 2-4 bytes for UTF-8 BOM, UTF-16
   LE/BE BOM, UTF-32 LE/BE BOM. If found, return immediately with confidence
   1.0.
2. **Pure ASCII check** (`ascii.py`): If all bytes are in 0x00-0x7F range,
   return `ascii` with confidence 1.0.
3. **UTF-8 structural validation** (`utf8.py`): Validate byte sequence as UTF-8
   by checking multi-byte sequence structure. If valid and contains multi-byte
   sequences, return `utf-8` with high confidence.
4. **Markup charset extraction** (`markup.py`): Scan for
   `<?xml ... encoding="..."?>`, `<meta charset="...">`,
   `<meta http-equiv="Content-Type" content="...; charset=...">`. Validate
   the claim against byte validity. Return with high confidence (not 1.0 —
   markup declarations can lie).

### Stage 2a — Byte Validity Filtering

For each candidate encoding (filtered by `EncodingEra`), test whether the input
bytes form valid sequences using `data.decode(encoding, errors='strict')`.
Encodings that raise `UnicodeDecodeError` are eliminated.

Single-threaded — these are essentially C-level decode calls. Typically
eliminates 70-80% of candidates.

### Stage 2b — Structural Probing for Multi-Byte Encodings

For multi-byte encodings surviving Stage 2a, compute a structural conformance
score based on how well the data fits the encoding's expected byte structure
(lead byte ranges, trail byte ranges, state transitions).

These are simple state machines per encoding based on public encoding
specifications — no trained models, no LGPL code. Provides confidence scores
that can resolve most CJK ambiguity without reaching Stage 3.

### Stage 3 — Statistical Scoring

Surviving candidates scored using byte bigram frequency models:

1. Compute bigram frequency distribution of the input (single pass, stored as a
   `BigramProfile` with separate low-byte and high-byte frequency dicts)
2. For each candidate, dot-product the profile against its trained model.
   High-byte bigrams (either byte > 0x7F) are weighted 8x to emphasise the
   non-ASCII signal that distinguishes encodings
3. Normalize scores to confidence values, return ranked results

The bigram profile is computed once and reused across all candidate models,
reducing per-model cost from O(n) to O(distinct_bigrams).

## Performance

Scoring is single-threaded. `ProcessPoolExecutor` was evaluated during
development but removed: the overhead of process creation and data
serialization exceeded the scoring cost for typical inputs. The single-pass
`BigramProfile` optimisation makes sequential scoring fast enough for all
practical use cases.

**PyPy compatibility:** No CPython-specific C extensions. All model loading
uses `struct` module.

## Model Training & Storage

### Training Pipeline (`scripts/train.py`)

1. Fetch Wikipedia articles across target languages via Hugging Face `datasets`
2. Fetch web crawl / HTML content to ensure models handle markup well
3. For each target encoding, encode source text from UTF-8 into that encoding
4. Compute byte bigram frequency distributions per encoding
5. Cache all downloaded data locally (`data/`, gitignored) for fast retraining
6. Serialize to sparse binary format

**Training/test split discipline:**

- Training: Wikipedia + HTML/web crawl data (via Hugging Face datasets)
- Evaluation: chardet test suite only (NEVER trained on)

### Storage Format

Sparse bigram representation to keep wheel size reasonable:

- Only significant (non-zero) bigrams stored per encoding
- Each entry: `(byte1: uint8, byte2: uint8, weight: uint8)` — 3 bytes
- All encodings bundled into a single `models.bin` with a header index
- Actual size target determined empirically by measuring accuracy vs size

No giant dict literals — avoids the CPython 3.12 `sys.settrace` performance bug.

### Model Loading

Lazy-loading module-level cache. First `detect()` call loads all models via
`struct.unpack`. Subsequent calls reuse cached data.

## Encoding Registry

Central registry mapping each encoding to its metadata:

```python
@dataclasses.dataclass(frozen=True, slots=True)
class EncodingInfo:
    name: str                    # Canonical name (e.g., "iso-8859-1")
    aliases: frozenset[str]      # Alternative names
    era: EncodingEra             # Which era(s) this encoding belongs to
    is_multibyte: bool           # Whether structural probing applies
    python_codec: str            # Name for codecs.lookup() / bytes.decode()
```

Registry stored as a plain tuple of `EncodingInfo` (immutable, no dict literal
issues).

**Era assignments match chardet 6.0.0** (`chardet/metadata/charsets.py`):

- **MODERN_WEB:** ASCII, BIG5, CP874, CP932, CP949, EUC-JP, EUC-KR, GB18030,
  HZ-GB-2312, ISO-2022-JP, ISO-2022-KR, KOI8-R, KOI8-U, SHIFT-JIS, TIS-620,
  UTF-8, UTF-8-SIG, UTF-16/BE/LE, UTF-32/BE/LE, WINDOWS-1250 through 1258
- **LEGACY_ISO:** ISO-8859-{1-16}, JOHAB
- **LEGACY_MAC:** MacCyrillic, MacGreek, MacIceland, MacLatin2, MacRoman,
  MacTurkish
- **LEGACY_REGIONAL:** CP720, CP1006, CP1125, KOI8-T, KZ1048, PTCP154
- **DOS:** CP437, CP737, CP775, CP850, CP852, CP855-CP869
- **MAINFRAME:** CP037, CP424, CP500, CP875, CP1026

## Error Handling & Edge Cases

### Input Edge Cases

- **Empty input:** Return `{'encoding': 'utf-8', 'confidence': 0.10, 'language': None}`
- **Binary content:** Detected in Stage 0, return `None` encoding
- **Single byte:** ASCII check may succeed, otherwise low-confidence result
- **`max_bytes` truncation:** Slice input before entering pipeline

### Pipeline Edge Cases

- **No candidates survive Stage 2:** Return `None` encoding
- **Unsupported encoding in markup declaration:** Ignore, continue to later
  stages
- **Markup charset contradicts byte structure:** Trust byte structure. Only
  return declaration result with reduced confidence if bytes are also valid
- **Tied scores in Stage 3:** Prefer encoding earlier in registry (ordered by
  commonality within era)

### `UniversalDetector` Edge Cases

- **`result` before `close()`:** Return best result so far
- **`feed()` after `close()` without `reset()`:** Raise `ValueError`
- **`feed()` after `done` is `True`:** Silently ignore

## Testing

### Test Layers

1. **Unit tests (`test_pipeline.py`):** Each pipeline stage in isolation
2. **API contract tests (`test_api.py`):** Public API matches chardet behavior,
   `EncodingEra` filtering, CLI output format, edge cases
3. **Accuracy tests (`test_accuracy.py`):** Detection accuracy against chardet
   test suite, per-encoding and overall accuracy reporting, minimum threshold
4. **Performance tests (`test_benchmark.py`):** Latency and throughput
   measurement, gated behind `--benchmark` marker

### Test Data Resolution

1. Check for `tests/data/` in repo (post-merge scenario) — use directly
2. If absent, download from chardet GitHub repo and cache locally in
   `tests/data/` (gitignored until merge)

### Benchmarking (`scripts/benchmark.py`)

- Per-file detection latency (p50, p95, p99) across chardet test suite
- Throughput (files/second) for batch detection
- Comparison against current chardet as baseline
- Memory usage via `tracemalloc`
