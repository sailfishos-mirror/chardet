# Docstrings and Type Annotations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Sphinx reST docstrings to all functions, classes, and modules in `src/chardet/`, add missing return type annotations, and enforce these via ruff by removing global rule exceptions.

**Architecture:** Remove 8 global ruff ignores (D100-D104, D107, ANN201, ANN202) and add them as per-file-ignores for tests/scripts. Then fix all resulting violations file-by-file. Public functions get full `:param:`/`:returns:` docstrings; private functions get summary-line docstrings only.

**Tech Stack:** ruff (linting), Sphinx reST docstring format, Python type annotations

---

### Task 1: Update pyproject.toml ruff rules

**Files:**
- Modify: `pyproject.toml:83-106` (global ignores), `pyproject.toml:108-125` (per-file-ignores)

**Step 1: Remove docstring and annotation ignores from global ignore list**

Edit `pyproject.toml` to remove lines 90-99 (the `D100`, `D101`, `D102`, `D103`, `D104`, `D107`, `ANN201`, `ANN202` entries and their comments) from the `[tool.ruff.lint] ignore` list.

The resulting ignore list should be:

```toml
ignore = [
    "E501",
    # Incompatible pairs
    "D203",   # incompatible with D211
    "D213",   # incompatible with D212
    # Formatter conflict
    "COM812", # trailing comma (ruff formatter handles this)
    # Encoding-detection code characteristics
    "PLR2004", # magic value comparison (byte values/thresholds)
    "C901",    # complex structure
    "PLR0911", # too many return statements
    "PLR0912", # too many branches
    "PERF203", # try-except in loop
]
```

**Step 2: Add docstring/annotation ignores to tests and scripts per-file-ignores**

Add `"D100"`, `"D101"`, `"D102"`, `"D103"`, `"D104"`, `"D107"`, `"ANN201"`, `"ANN202"` to the `"tests/**"`, `"scripts/tests/**"`, and `"scripts/**"` per-file-ignore sections.

**Step 3: Add pydocstyle convention**

Add a new section after `[tool.ruff.lint.per-file-ignores]`:

```toml
[tool.ruff.lint.pydocstyle]
convention = "pep257"
```

**Step 4: Run ruff to see violations**

Run: `uv run ruff check src/chardet/ 2>&1 | head -80`

Expected: Violations for missing docstrings (D100/D101/D102/D103/D104/D107) and missing return type annotations (ANN201/ANN202) across `src/chardet/` files. No violations in tests/ or scripts/.

**Step 5: Commit**

```
git add pyproject.toml
git commit -m "chore: enforce docstring and return-type ruff rules for src/chardet"
```

---

### Task 2: Add docstrings to `src/chardet/__init__.py`

**Files:**
- Modify: `src/chardet/__init__.py`

**Step 1: Upgrade `detect` docstring**

The existing docstring is plain text. Upgrade to Sphinx reST format:

```python
def detect(...) -> dict[str, str | float | None]:
    """Detect the encoding of the given byte string.

    Parameters match chardet 6.x for backward compatibility.
    *chunk_size* is accepted but has no effect.

    :param byte_str: The byte string to examine.
    :param should_rename_legacy: If ``True``, map legacy encoding names to their
        modern Windows/CP equivalents.  Defaults to ``True`` when *encoding_era*
        is ``MODERN_WEB``, ``False`` otherwise.
    :param encoding_era: Filter candidates to a specific era of encodings.
    :param chunk_size: Accepted for API compatibility; has no effect.
    :param max_bytes: Maximum number of bytes to process.
    :returns: A dict with ``'encoding'``, ``'confidence'``, and ``'language'`` keys.
    """
```

**Step 2: Upgrade `detect_all` docstring**

Same pattern — keep the existing descriptive text and add `:param:`/`:returns:` blocks:

```python
def detect_all(...) -> list[dict[str, str | float | None]]:
    """Detect all possible encodings of the given byte string.

    Parameters match chardet 6.x for backward compatibility.
    *chunk_size* is accepted but has no effect.

    When *ignore_threshold* is ``False`` (the default), results with confidence
    <= ``MINIMUM_THRESHOLD`` (0.20) are filtered out.  If all results are below
    the threshold, the full unfiltered list is returned as a fallback so the
    caller always receives at least one result.

    :param byte_str: The byte string to examine.
    :param ignore_threshold: If ``True``, return all results regardless of
        confidence score.
    :param should_rename_legacy: If ``True``, map legacy encoding names to their
        modern Windows/CP equivalents.
    :param encoding_era: Filter candidates to a specific era of encodings.
    :param chunk_size: Accepted for API compatibility; has no effect.
    :param max_bytes: Maximum number of bytes to process.
    :returns: A list of dicts, each with ``'encoding'``, ``'confidence'``, and
        ``'language'`` keys, sorted by confidence descending.
    """
```

**Step 3: Add docstring to `_warn_deprecated_chunk_size`**

This is private, so summary-line only:

```python
def _warn_deprecated_chunk_size(chunk_size: int, stacklevel: int = 3) -> None:
    """Emit a deprecation warning if *chunk_size* differs from the default."""
```

**Step 4: Run ruff on this file**

Run: `uv run ruff check src/chardet/__init__.py`

Expected: No D-rule or ANN-rule violations.

**Step 5: Run tests**

Run: `uv run pytest tests/test_api.py -x -q`

Expected: All pass.

**Step 6: Commit**

```
git add src/chardet/__init__.py
git commit -m "docs: add Sphinx docstrings to chardet/__init__.py"
```

---

### Task 3: Add docstrings to `src/chardet/_utils.py`

**Files:**
- Modify: `src/chardet/_utils.py`

**Step 1: Add docstrings to both private functions**

Both are private, so summary-line only:

```python
def _resolve_rename(should_rename_legacy: bool | None, encoding_era: EncodingEra) -> bool:
    """Determine whether to apply legacy encoding name remapping."""
```

```python
def _validate_max_bytes(max_bytes: int) -> None:
    """Raise ValueError if *max_bytes* is not a positive integer."""
```

**Step 2: Run ruff**

Run: `uv run ruff check src/chardet/_utils.py`

Expected: No violations.

**Step 3: Commit**

```
git add src/chardet/_utils.py
git commit -m "docs: add docstrings to chardet/_utils.py"
```

---

### Task 4: Add docstrings to `src/chardet/cli.py`

**Files:**
- Modify: `src/chardet/cli.py`

**Step 1: Add docstring to `main`**

```python
def main(argv: list[str] | None = None) -> None:
    """Run the ``chardetect`` command-line tool.

    :param argv: Command-line arguments.  Defaults to ``sys.argv[1:]``.
    """
```

**Step 2: Run ruff**

Run: `uv run ruff check src/chardet/cli.py`

Expected: No violations.

**Step 3: Commit**

```
git add src/chardet/cli.py
git commit -m "docs: add docstrings to chardet/cli.py"
```

---

### Task 5: Add docstrings to `src/chardet/detector.py`

**Files:**
- Modify: `src/chardet/detector.py`

This file has the most missing docstrings. The `UniversalDetector` class, its `__init__`, and all public methods/properties lack docstrings.

**Step 1: Add class docstring**

```python
class UniversalDetector:
    """Streaming character encoding detector.

    Implements a feed/close pattern for incremental detection of character
    encoding from byte streams.  Compatible with the chardet 6.x API.
    """
```

**Step 2: Add `__init__` docstring**

```python
def __init__(
    self,
    lang_filter: LanguageFilter = LanguageFilter.ALL,
    should_rename_legacy: bool | None = None,
    encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
    max_bytes: int = 200_000,
) -> None:
    """Initialize the detector.

    :param lang_filter: Accepted for API compatibility; has no effect.
    :param should_rename_legacy: If ``True``, map legacy encoding names to
        their modern Windows/CP equivalents.
    :param encoding_era: Filter candidates to a specific era of encodings.
    :param max_bytes: Maximum number of bytes to buffer before running detection.
    """
```

**Step 3: Add `feed` docstring**

```python
def feed(self, byte_str: bytes | bytearray) -> None:
    """Feed a chunk of data to the detector.

    :param byte_str: A chunk of the byte stream to analyze.
    """
```

**Step 4: Add `close` docstring**

```python
def close(self) -> dict[str, str | float | None]:
    """Finalize detection and return the best result.

    :returns: A dict with ``'encoding'``, ``'confidence'``, and ``'language'`` keys.
    """
```

**Step 5: Add `reset` docstring**

```python
def reset(self) -> None:
    """Reset the detector to its initial state for reuse."""
```

**Step 6: Add `done` property docstring**

```python
@property
def done(self) -> bool:
    """Whether detection is complete and no more data is needed."""
```

**Step 7: Add `result` property docstring**

```python
@property
def result(self) -> dict[str, str | float | None]:
    """The current best detection result."""
```

**Step 8: Run ruff**

Run: `uv run ruff check src/chardet/detector.py`

Expected: No D-rule or ANN-rule violations.

**Step 9: Run tests**

Run: `uv run pytest tests/test_api.py -x -q`

Expected: All pass.

**Step 10: Commit**

```
git add src/chardet/detector.py
git commit -m "docs: add Sphinx docstrings to chardet/detector.py"
```

---

### Task 6: Add docstrings to `src/chardet/enums.py`

**Files:**
- Modify: `src/chardet/enums.py`

The classes already have docstrings. Check if there's a missing module docstring (currently `"Enumerations for chardet."`) — that should satisfy D100. Run ruff to verify.

**Step 1: Run ruff to check**

Run: `uv run ruff check src/chardet/enums.py`

If no violations, skip to commit. If violations remain, fix them.

**Step 2: Commit (if changes made)**

```
git add src/chardet/enums.py
git commit -m "docs: add docstrings to chardet/enums.py"
```

---

### Task 7: Upgrade docstrings in `src/chardet/equivalences.py`

**Files:**
- Modify: `src/chardet/equivalences.py`

Most functions already have docstrings. Upgrade public functions to include `:param:`/`:returns:`. Private functions already have docstrings — leave as-is (they're already summary or descriptive style).

**Step 1: Upgrade `normalize_encoding_name`**

```python
def normalize_encoding_name(name: str) -> str:
    """Normalize an encoding name for comparison.

    :param name: The encoding name to normalize.
    :returns: The lowercased, hyphen-normalized name.
    """
```

**Step 2: Upgrade `apply_legacy_rename`**

```python
def apply_legacy_rename(result: dict[str, str | float | None]) -> dict[str, str | float | None]:
    """Replace the encoding name with its preferred Windows/CP superset.

    Modifies the ``"encoding"`` value in *result* in-place and returns it.

    :param result: A detection result dict to modify.
    :returns: The same dict with the encoding name replaced, if applicable.
    """
```

**Step 3: Upgrade `is_correct`**

```python
def is_correct(expected: str, detected: str | None) -> bool:
    """Check whether *detected* is an acceptable answer for *expected*.

    Acceptable means:

    1. Exact match (after normalization), OR
    2. Both belong to the same bidirectional byte-order group, OR
    3. *detected* is a known superset of *expected*.

    :param expected: The ground-truth encoding name.
    :param detected: The encoding name returned by the detector.
    :returns: ``True`` if *detected* is an acceptable match.
    """
```

**Step 4: Upgrade `is_equivalent_detection`**

```python
def is_equivalent_detection(data: bytes, expected: str, detected: str | None) -> bool:
    """Check whether *detected* produces functionally identical text to *expected*.

    Returns ``True`` when:

    1. *detected* is not ``None`` and both encoding names normalize to the
       same codec, OR
    2. Decoding *data* with both encodings yields identical strings, OR
    3. Every differing character pair is functionally equivalent: same base
       letter after stripping combining marks, or an explicitly listed symbol
       equivalence (e.g. curren sign vs. euro sign).

    :param data: The raw byte data to decode under both encodings.
    :param expected: The ground-truth encoding name.
    :param detected: The encoding name returned by the detector.
    :returns: ``True`` if both encodings produce functionally identical text.
    """
```

**Step 5: Add docstring to `_build_bidir_index` (private, summary only)**

```python
def _build_bidir_index() -> dict[str, frozenset[str]]:
    """Build the bidirectional equivalence lookup index."""
```

**Step 6: Run ruff**

Run: `uv run ruff check src/chardet/equivalences.py`

Expected: No violations.

**Step 7: Commit**

```
git add src/chardet/equivalences.py
git commit -m "docs: upgrade docstrings in chardet/equivalences.py to Sphinx reST"
```

---

### Task 8: Upgrade docstrings in `src/chardet/registry.py`

**Files:**
- Modify: `src/chardet/registry.py`

**Step 1: Upgrade `get_candidates`**

```python
def get_candidates(era: EncodingEra) -> tuple[EncodingInfo, ...]:
    """Return registry entries matching the given era filter.

    :param era: Bit flags specifying which encoding eras to include.
    :returns: A tuple of matching :class:`EncodingInfo` entries.
    """
```

**Step 2: Run ruff**

Run: `uv run ruff check src/chardet/registry.py`

Expected: No violations.

**Step 3: Commit**

```
git add src/chardet/registry.py
git commit -m "docs: upgrade docstrings in chardet/registry.py to Sphinx reST"
```

---

### Task 9: Upgrade docstrings in `src/chardet/models/__init__.py`

**Files:**
- Modify: `src/chardet/models/__init__.py`

**Step 1: Upgrade public function docstrings**

Upgrade `load_models`, `infer_language`, `has_model_variants`, `score_best_language` to include `:param:`/`:returns:`.

`load_models` (no params):

```python
def load_models() -> dict[str, bytearray]:
    """Load all bigram models from the bundled ``models.bin`` file.

    Each model is a :class:`bytearray` of length 65536 (256 x 256).
    Index: ``(b1 << 8) | b2`` maps to a weight (0--255).

    :returns: A dict mapping ``"language/encoding"`` keys to model bytearrays.
    """
```

`infer_language`:

```python
def infer_language(encoding: str) -> str | None:
    """Return the language for a single-language encoding, or ``None``.

    :param encoding: The encoding name to look up.
    :returns: The language name, or ``None`` if the encoding has multiple
        language variants.
    """
```

`has_model_variants`:

```python
def has_model_variants(encoding: str) -> bool:
    """Return ``True`` if the encoding has language variants in the model index.

    :param encoding: The encoding name to check.
    :returns: ``True`` if multiple language models exist for this encoding.
    """
```

`score_best_language`:

```python
def score_best_language(
    data: bytes, encoding: str, profile: BigramProfile | None = None
) -> tuple[float, str | None]:
    """Score data against all language variants of an encoding.

    Uses a pre-grouped index for O(L) lookup where L is the number of
    language variants for the encoding.

    :param data: The raw byte data to score.
    :param encoding: The encoding name whose language variants to test.
    :param profile: A pre-computed bigram profile to reuse, or ``None``
        to compute one from *data*.
    :returns: A ``(best_score, best_language)`` tuple.
    """
```

**Step 2: Add `BigramProfile.__init__` docstring**

```python
def __init__(self, data: bytes) -> None:
    """Compute the bigram frequency distribution for *data*.

    :param data: The raw byte data to profile.
    """
```

**Step 3: Upgrade `from_weighted_freq` docstring**

```python
@classmethod
def from_weighted_freq(
    cls, weighted_freq: dict[int, int], weight_sum: int
) -> "BigramProfile":
    """Create a :class:`BigramProfile` from pre-computed weighted frequencies.

    :param weighted_freq: Mapping of bigram index to weighted count.
    :param weight_sum: The total weight sum for normalization.
    :returns: A new :class:`BigramProfile` instance.
    """
```

**Step 4: Run ruff**

Run: `uv run ruff check src/chardet/models/__init__.py`

Expected: No violations.

**Step 5: Commit**

```
git add src/chardet/models/__init__.py
git commit -m "docs: upgrade docstrings in chardet/models/__init__.py to Sphinx reST"
```

---

### Task 10: Add docstrings to `src/chardet/pipeline/__init__.py`

**Files:**
- Modify: `src/chardet/pipeline/__init__.py`

**Step 1: Add class docstring to `DetectionResult`**

```python
@dataclass(frozen=True, slots=True)
class DetectionResult:
    """A single encoding detection result.

    Frozen dataclass holding the encoding name, confidence score, and
    optional language identifier returned by the detection pipeline.
    """
```

**Step 2: Add `to_dict` docstring**

```python
def to_dict(self) -> dict[str, str | float | None]:
    """Convert this result to a plain dict.

    :returns: A dict with ``'encoding'``, ``'confidence'``, and ``'language'`` keys.
    """
```

**Step 3: Run ruff**

Run: `uv run ruff check src/chardet/pipeline/__init__.py`

Expected: No violations.

**Step 4: Commit**

```
git add src/chardet/pipeline/__init__.py
git commit -m "docs: add docstrings to chardet/pipeline/__init__.py"
```

---

### Task 11: Upgrade docstrings in `src/chardet/pipeline/orchestrator.py`

**Files:**
- Modify: `src/chardet/pipeline/orchestrator.py`

**Step 1: Upgrade `run_pipeline` (public)**

```python
def run_pipeline(
    data: bytes,
    encoding_era: EncodingEra,
    max_bytes: int = 200_000,
) -> list[DetectionResult]:
    """Run the full detection pipeline.

    :param data: The raw byte data to analyze.
    :param encoding_era: Filter candidates to a specific era of encodings.
    :param max_bytes: Maximum number of bytes to process.
    :returns: A list of :class:`DetectionResult` sorted by confidence descending.
    """
```

**Step 2: Ensure all private functions have at least a summary-line docstring**

All private functions (`_should_demote`, `_gate_cjk_candidates`, `_score_structural_candidates`, `_demote_niche_latin`, `_promote_koi8t`, `_to_utf8`, `_fill_language`, `_run_pipeline_core`) already have docstrings. Verify they satisfy the D103 rule (they won't trigger it since they're private — D103 is for public functions only). Verify D102 (public method) and D100 (module) are also satisfied.

**Step 3: Run ruff**

Run: `uv run ruff check src/chardet/pipeline/orchestrator.py`

Expected: No violations.

**Step 4: Commit (if changes made)**

```
git add src/chardet/pipeline/orchestrator.py
git commit -m "docs: upgrade docstrings in chardet/pipeline/orchestrator.py"
```

---

### Task 12: Upgrade docstrings in pipeline stage modules

**Files:**
- Modify: `src/chardet/pipeline/ascii.py`
- Modify: `src/chardet/pipeline/bom.py`
- Modify: `src/chardet/pipeline/binary.py`
- Modify: `src/chardet/pipeline/utf8.py`
- Modify: `src/chardet/pipeline/validity.py`
- Modify: `src/chardet/pipeline/statistical.py`

These are all small single-function modules. Upgrade their public function docstrings to include `:param:`/`:returns:`.

**Step 1: Upgrade `detect_ascii`**

```python
def detect_ascii(data: bytes) -> DetectionResult | None:
    """Return an ASCII result if all bytes are printable ASCII plus common whitespace.

    :param data: The raw byte data to examine.
    :returns: A :class:`DetectionResult` for ASCII, or ``None``.
    """
```

**Step 2: Upgrade `detect_bom`**

```python
def detect_bom(data: bytes) -> DetectionResult | None:
    """Check for a byte order mark at the start of *data*.

    :param data: The raw byte data to examine.
    :returns: A :class:`DetectionResult` with confidence 1.0, or ``None``.
    """
```

**Step 3: Upgrade `is_binary`**

```python
def is_binary(data: bytes, max_bytes: int = 200_000) -> bool:
    """Return ``True`` if *data* appears to be binary (not text) content.

    :param data: The raw byte data to examine.
    :param max_bytes: Maximum number of bytes to scan.
    :returns: ``True`` if the data is classified as binary.
    """
```

**Step 4: Upgrade `detect_utf8`**

```python
def detect_utf8(data: bytes) -> DetectionResult | None:
    """Validate UTF-8 byte structure.

    Returns a result only if multi-byte sequences are found (pure ASCII
    is handled by the ASCII stage).

    :param data: The raw byte data to examine.
    :returns: A :class:`DetectionResult` for UTF-8, or ``None``.
    """
```

**Step 5: Upgrade `filter_by_validity`**

```python
def filter_by_validity(
    data: bytes, candidates: tuple[EncodingInfo, ...]
) -> tuple[EncodingInfo, ...]:
    """Filter candidates to only those where *data* decodes without errors.

    :param data: The raw byte data to test.
    :param candidates: Encoding candidates to validate.
    :returns: The subset of *candidates* that can decode *data*.
    """
```

**Step 6: Upgrade `score_candidates`**

```python
def score_candidates(
    data: bytes, candidates: tuple[EncodingInfo, ...]
) -> list[DetectionResult]:
    """Score all candidates and return results sorted by confidence descending.

    :param data: The raw byte data to score.
    :param candidates: Encoding candidates to evaluate.
    :returns: A list of :class:`DetectionResult` sorted by confidence.
    """
```

**Step 7: Run ruff on all modified files**

Run: `uv run ruff check src/chardet/pipeline/ascii.py src/chardet/pipeline/bom.py src/chardet/pipeline/binary.py src/chardet/pipeline/utf8.py src/chardet/pipeline/validity.py src/chardet/pipeline/statistical.py`

Expected: No violations.

**Step 8: Commit**

```
git add src/chardet/pipeline/ascii.py src/chardet/pipeline/bom.py src/chardet/pipeline/binary.py src/chardet/pipeline/utf8.py src/chardet/pipeline/validity.py src/chardet/pipeline/statistical.py
git commit -m "docs: upgrade docstrings in single-function pipeline stages"
```

---

### Task 13: Upgrade docstrings in `src/chardet/pipeline/utf1632.py`

**Files:**
- Modify: `src/chardet/pipeline/utf1632.py`

**Step 1: Upgrade `detect_utf1632_patterns` (public)**

```python
def detect_utf1632_patterns(data: bytes) -> DetectionResult | None:
    """Detect UTF-32 or UTF-16 encoding from null-byte patterns.

    UTF-32 is checked before UTF-16 since UTF-32 patterns are more specific.

    :param data: The raw byte data to examine.
    :returns: A :class:`DetectionResult` if a strong pattern is found, or ``None``.
    """
```

**Step 2: Verify private functions have docstrings**

`_check_utf32`, `_check_utf16`, `_looks_like_text`, `_text_quality` all already have docstrings. No changes needed.

**Step 3: Run ruff**

Run: `uv run ruff check src/chardet/pipeline/utf1632.py`

Expected: No violations.

**Step 4: Commit**

```
git add src/chardet/pipeline/utf1632.py
git commit -m "docs: upgrade docstrings in chardet/pipeline/utf1632.py"
```

---

### Task 14: Upgrade docstrings in `src/chardet/pipeline/escape.py`

**Files:**
- Modify: `src/chardet/pipeline/escape.py`

**Step 1: Upgrade `detect_escape_encoding` (public)**

```python
def detect_escape_encoding(data: bytes) -> DetectionResult | None:
    """Detect ISO-2022 and HZ-GB-2312 from escape/tilde sequences.

    :param data: The raw byte data to examine.
    :returns: A :class:`DetectionResult` if an escape encoding is found, or ``None``.
    """
```

**Step 2: Verify `_has_valid_hz_regions` has a docstring (it does)**

**Step 3: Run ruff**

Run: `uv run ruff check src/chardet/pipeline/escape.py`

Expected: No violations.

**Step 4: Commit**

```
git add src/chardet/pipeline/escape.py
git commit -m "docs: upgrade docstrings in chardet/pipeline/escape.py"
```

---

### Task 15: Upgrade docstrings in `src/chardet/pipeline/markup.py`

**Files:**
- Modify: `src/chardet/pipeline/markup.py`

**Step 1: Upgrade `detect_markup_charset` (public)**

```python
def detect_markup_charset(data: bytes) -> DetectionResult | None:
    """Scan the first bytes of *data* for an HTML/XML charset declaration.

    Checks for:

    1. ``<?xml ... encoding="..."?>``
    2. ``<meta charset="...">``
    3. ``<meta http-equiv="Content-Type" content="...; charset=...">``

    :param data: The raw byte data to scan.
    :returns: A :class:`DetectionResult` with confidence 0.95, or ``None``.
    """
```

**Step 2: Verify private functions have docstrings (they do)**

**Step 3: Run ruff**

Run: `uv run ruff check src/chardet/pipeline/markup.py`

Expected: No violations.

**Step 4: Commit**

```
git add src/chardet/pipeline/markup.py
git commit -m "docs: upgrade docstrings in chardet/pipeline/markup.py"
```

---

### Task 16: Upgrade docstrings in `src/chardet/pipeline/structural.py`

**Files:**
- Modify: `src/chardet/pipeline/structural.py`

**Step 1: Upgrade public function docstrings**

`compute_structural_score`:

```python
def compute_structural_score(
    data: bytes, encoding_info: EncodingInfo, ctx: PipelineContext
) -> float:
    """Return 0.0--1.0 indicating how well *data* matches the encoding's structure.

    For single-byte encodings, always returns 0.0.  For empty data, always
    returns 0.0.

    :param data: The raw byte data to analyze.
    :param encoding_info: Metadata for the encoding to probe.
    :param ctx: Pipeline context for caching analysis results.
    :returns: A structural fit score between 0.0 and 1.0.
    """
```

`compute_multibyte_byte_coverage`:

```python
def compute_multibyte_byte_coverage(
    data: bytes,
    encoding_info: EncodingInfo,
    ctx: PipelineContext,
    non_ascii_count: int = -1,
) -> float:
    """Ratio of non-ASCII bytes that participate in valid multi-byte sequences.

    Genuine CJK text has nearly all non-ASCII bytes paired into valid
    multi-byte sequences (coverage close to 1.0), while Latin text with
    scattered high bytes has many orphan bytes (coverage well below 1.0).

    :param data: The raw byte data to analyze.
    :param encoding_info: Metadata for the encoding to probe.
    :param ctx: Pipeline context for caching analysis results.
    :param non_ascii_count: Pre-computed count of non-ASCII bytes, or ``-1``
        to compute from *data*.
    :returns: A coverage ratio between 0.0 and 1.0.
    """
```

`compute_lead_byte_diversity`:

```python
def compute_lead_byte_diversity(
    data: bytes, encoding_info: EncodingInfo, ctx: PipelineContext
) -> int:
    """Count distinct lead byte values in valid multi-byte pairs.

    Genuine CJK text uses lead bytes from across the encoding's full
    repertoire.  European text falsely matching a CJK structural scorer
    clusters lead bytes in a narrow band.

    :param data: The raw byte data to analyze.
    :param encoding_info: Metadata for the encoding to probe.
    :param ctx: Pipeline context for caching analysis results.
    :returns: The number of distinct lead byte values found.
    """
```

**Step 2: Verify private functions have docstrings (they all do)**

**Step 3: Run ruff**

Run: `uv run ruff check src/chardet/pipeline/structural.py`

Expected: No violations.

**Step 4: Commit**

```
git add src/chardet/pipeline/structural.py
git commit -m "docs: upgrade docstrings in chardet/pipeline/structural.py"
```

---

### Task 17: Upgrade docstrings in `src/chardet/pipeline/confusion.py`

**Files:**
- Modify: `src/chardet/pipeline/confusion.py`

**Step 1: Upgrade public function docstrings**

`deserialize_confusion_data_from_bytes`:

```python
def deserialize_confusion_data_from_bytes(data: bytes) -> DistinguishingMaps:
    """Load confusion group data from raw bytes.

    :param data: The serialized confusion data.
    :returns: A dict mapping encoding pairs to their distinguishing byte info.
    """
```

`load_confusion_data`:

```python
def load_confusion_data() -> DistinguishingMaps:
    """Load confusion group data from the bundled ``confusion.bin`` file.

    :returns: A dict mapping encoding pairs to their distinguishing byte info.
    """
```

`resolve_by_category_voting`:

```python
def resolve_by_category_voting(
    data: bytes,
    enc_a: str,
    enc_b: str,
    diff_bytes: frozenset[int],
    categories: dict[int, tuple[str, str]],
) -> str | None:
    """Resolve between two encodings using Unicode category voting.

    For each distinguishing byte present in the data, compare the Unicode
    general category under each encoding.  The encoding whose interpretation
    has the higher category preference score gets a vote.

    :param data: The raw byte data being analyzed.
    :param enc_a: The first encoding name.
    :param enc_b: The second encoding name.
    :param diff_bytes: Byte values that differ between the two encodings.
    :param categories: Mapping of byte value to ``(cat_a, cat_b)`` category pairs.
    :returns: The winning encoding name, or ``None`` if tied.
    """
```

`resolve_by_bigram_rescore`:

```python
def resolve_by_bigram_rescore(
    data: bytes, enc_a: str, enc_b: str, diff_bytes: frozenset[int]
) -> str | None:
    """Resolve between two encodings by re-scoring only distinguishing bigrams.

    Builds a focused bigram profile containing only bigrams where at least one
    byte is a distinguishing byte, then scores both encodings against their
    best language model.

    :param data: The raw byte data being analyzed.
    :param enc_a: The first encoding name.
    :param enc_b: The second encoding name.
    :param diff_bytes: Byte values that differ between the two encodings.
    :returns: The winning encoding name, or ``None`` if tied.
    """
```

`resolve_confusion_groups`:

```python
def resolve_confusion_groups(
    data: bytes,
    results: list[DetectionResult],
    strategy: str = "hybrid",
) -> list[DetectionResult]:
    """Resolve confusion between similar encodings in the top results.

    Compares the top two results.  If they form a known confusion pair,
    applies the specified resolution strategy to determine the winner.

    Strategies:

    - ``"category"``: Unicode category voting only
    - ``"bigram"``: Distinguishing-bigram re-scoring only
    - ``"hybrid"``: Both strategies; bigram wins on disagreement
    - ``"none"``: No resolution (passthrough)

    :param data: The raw byte data being analyzed.
    :param results: Detection results to resolve, sorted by confidence.
    :param strategy: The resolution strategy to apply.
    :returns: The results list with the top two potentially reordered.
    """
```

**Step 2: Run ruff**

Run: `uv run ruff check src/chardet/pipeline/confusion.py`

Expected: No violations.

**Step 3: Commit**

```
git add src/chardet/pipeline/confusion.py
git commit -m "docs: upgrade docstrings in chardet/pipeline/confusion.py"
```

---

### Task 18: Final verification

**Step 1: Run full ruff check on src/chardet/**

Run: `uv run ruff check src/chardet/`

Expected: No D-rule or ANN-rule violations. Zero violations total (or only pre-existing non-docstring ones).

**Step 2: Run full test suite**

Run: `uv run pytest -x -q`

Expected: All tests pass.

**Step 3: Run ty type check**

Run: `uv run ty check src/chardet/`

Expected: No new type errors.

**Step 4: Commit any remaining fixes**

If any ruff/ty violations were found and fixed, commit them:

```
git add -u
git commit -m "docs: fix remaining docstring and type annotation violations"
```
