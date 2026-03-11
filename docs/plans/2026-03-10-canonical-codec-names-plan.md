# Canonical Codec Names Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch chardet's internal canonical encoding names from display-cased strings (e.g., `"UTF-8"`, `"Windows-1252"`) to Python codec names (`codecs.lookup(name).name`, e.g., `"utf-8"`, `"cp1252"`), add `compat_names` and `prefer_superset` API parameters, and retrain models with new key format.

**Architecture:** All internal encoding names become the output of `codecs.lookup().name`. A `_COMPAT_NAMES` mapping at the API boundary converts codec names back to chardet 5.x/6.x display names when `compat_names=True` (default). `prefer_superset` replaces `should_rename_legacy` for ISO→Windows remapping. Model keys switch from `"French/Windows-1252"` to `"fr/cp1252"`.

**Tech Stack:** Python 3.10+, mypyc-compiled modules, pytest

**Design spec:** `docs/plans/2026-03-10-canonical-codec-names-design.md`

---

## Chunk 1: Equivalences & API Parameters

### Task 1: Replace `_LEGACY_NAMES` with `_COMPAT_NAMES`

**Files:**
- Modify: `src/chardet/equivalences.py`
- Test: `tests/test_equivalences.py`

The new `_COMPAT_NAMES` maps codec name → 5.x/6.x display name. Only encodings where codec name ≠ 5.x/6.x output need entries. New-to-v7 encodings (DOS codepages, EBCDIC, etc.) have no entry — codec name passes through.

- [ ] **Step 1: Write failing test for `_COMPAT_NAMES` mapping**

In `tests/test_equivalences.py`, add:

```python
def test_compat_names_maps_codec_to_display() -> None:
    """_COMPAT_NAMES maps codec names to 5.x/6.x display names."""
    from chardet.equivalences import _COMPAT_NAMES

    # 5.x compat entries
    assert _COMPAT_NAMES["big5hkscs"] == "Big5"
    assert _COMPAT_NAMES["cp855"] == "IBM855"
    assert _COMPAT_NAMES["euc_jis_2004"] == "EUC-JP"
    assert _COMPAT_NAMES["iso2022_jp_2"] == "ISO-2022-JP"
    assert _COMPAT_NAMES["shift_jis_2004"] == "SHIFT_JIS"
    # Windows codepage entries
    assert _COMPAT_NAMES["cp1252"] == "Windows-1252"
    assert _COMPAT_NAMES["cp1251"] == "Windows-1251"
    # ISO entries
    assert _COMPAT_NAMES["iso8859-1"] == "ISO-8859-1"
    # Codec names that match 5.x output have no entry
    assert "ascii" not in _COMPAT_NAMES
    assert "utf-8" not in _COMPAT_NAMES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_equivalences.py::test_compat_names_maps_codec_to_display -xvs`
Expected: FAIL with `ImportError` (no `_COMPAT_NAMES` yet)

- [ ] **Step 3: Implement `_COMPAT_NAMES` in `equivalences.py`**

Replace `_LEGACY_NAMES` dict (lines 128-146) with `_COMPAT_NAMES`. Keep `_LEGACY_NAMES` as an alias for backward compat in case anything imports it. The complete mapping (generated from current registry):

```python
# Mapping from Python codec names to chardet 5.x/6.x compatible display names.
# Only entries where codec name differs from the compat output are listed.
# Encodings where codec name == compat name (e.g., "ascii", "utf-8") and
# encodings new to v7 have no entry — the codec name passes through unchanged.
_COMPAT_NAMES: dict[str, str] = {
    # 5.x compat — these encodings existed in chardet 5.x with different names
    "big5hkscs": "Big5",
    "cp855": "IBM855",
    "cp866": "IBM866",
    "cp949": "CP949",
    "euc_jis_2004": "EUC-JP",
    "euc_kr": "EUC-KR",
    "gb18030": "GB18030",
    "hz": "HZ-GB-2312",
    "iso2022_jp_2": "ISO-2022-JP",
    "iso2022_kr": "ISO-2022-KR",
    "iso8859-1": "ISO-8859-1",
    "iso8859-5": "ISO-8859-5",
    "iso8859-7": "ISO-8859-7",
    "iso8859-8": "ISO-8859-8",
    "iso8859-9": "ISO-8859-9",
    "johab": "Johab",
    "koi8-r": "KOI8-R",
    "mac-cyrillic": "MacCyrillic",
    "mac-roman": "MacRoman",
    "shift_jis_2004": "SHIFT_JIS",
    "tis-620": "TIS-620",
    "utf-16": "UTF-16",
    "utf-32": "UTF-32",
    "utf-8-sig": "UTF-8-SIG",
    "cp1251": "Windows-1251",
    "cp1252": "Windows-1252",
    "cp1253": "Windows-1253",
    "cp1254": "Windows-1254",
    "cp1255": "Windows-1255",
    # 6.x compat — new in chardet 6.x with different names
    "kz1048": "KZ1048",
    "mac-greek": "MacGreek",
    "mac-iceland": "MacIceland",
    "mac-latin2": "MacLatin2",
    "mac-turkish": "MacTurkish",
}

# Backward compat alias
_LEGACY_NAMES = _COMPAT_NAMES
```

Update `apply_compat_names()` (line 162) to use `_COMPAT_NAMES`:

```python
result["encoding"] = _COMPAT_NAMES.get(enc, enc)
```

(This already works since `_LEGACY_NAMES` is aliased to `_COMPAT_NAMES`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_equivalences.py -xvs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/chardet/equivalences.py tests/test_equivalences.py
git commit -m "refactor: replace _LEGACY_NAMES with _COMPAT_NAMES (codec name keys)"
```

---

### Task 2: Add `compat_names` and `prefer_superset` parameters to `detect()`

**Files:**
- Modify: `src/chardet/__init__.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing tests for new parameters**

In `tests/test_api.py`, add tests near the end of the file:

```python
def test_detect_compat_names_true_returns_display_names() -> None:
    """compat_names=True (default) returns 5.x/6.x display names."""
    result = detect("日本語".encode("utf-8"), compat_names=True)
    # With compat_names=True, internal "utf-8" -> display "utf-8" (same)
    assert result["encoding"] is not None


def test_detect_compat_names_false_returns_codec_names() -> None:
    """compat_names=False returns raw Python codec names."""
    result = detect("日本語".encode("utf-8"), compat_names=False)
    assert result["encoding"] is not None


def test_detect_prefer_superset_remaps() -> None:
    """prefer_superset=True remaps ISO to Windows supersets."""
    # ASCII data should be remapped to Windows-1252 (or cp1252)
    result = detect(b"Hello World", prefer_superset=True, compat_names=True)
    assert result["encoding"] in ("Windows-1252", "cp1252", "ascii")


def test_detect_should_rename_legacy_is_alias() -> None:
    """should_rename_legacy is a deprecated alias for prefer_superset."""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        try:
            detect(b"Hello", should_rename_legacy=True)
        except DeprecationWarning:
            pass  # Expected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_api.py::test_detect_compat_names_true_returns_display_names tests/test_api.py::test_detect_compat_names_false_returns_codec_names tests/test_api.py::test_detect_prefer_superset_remaps tests/test_api.py::test_detect_should_rename_legacy_is_alias -xvs`
Expected: FAIL with `TypeError: unexpected keyword argument 'compat_names'`

- [ ] **Step 3: Implement new parameters in `detect()` and `detect_all()`**

In `src/chardet/__init__.py`, update `detect()`:

```python
import warnings

def detect(
    byte_str: bytes | bytearray,
    should_rename_legacy: bool = False,
    encoding_era: EncodingEra = EncodingEra.ALL,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    max_bytes: int = DEFAULT_MAX_BYTES,
    *,
    prefer_superset: bool = False,
    compat_names: bool = True,
) -> DetectionDict:
    _warn_deprecated_chunk_size(chunk_size)
    _validate_max_bytes(max_bytes)

    # should_rename_legacy is a deprecated alias for prefer_superset
    if should_rename_legacy:
        warnings.warn(
            "should_rename_legacy is deprecated, use prefer_superset instead",
            DeprecationWarning,
            stacklevel=2,
        )
        prefer_superset = True

    data = byte_str if isinstance(byte_str, bytes) else bytes(byte_str)
    results = run_pipeline(data, encoding_era, max_bytes=max_bytes)
    result = results[0].to_dict()
    if prefer_superset:
        apply_legacy_rename(result)
    if compat_names:
        apply_compat_names(result)
    return result
```

Apply the same pattern to `detect_all()`. Note the flow change: `prefer_superset` and `compat_names` are now independent — both can be applied in sequence. The superset remap happens first (on codec names), then compat names maps the result to display names.

Update import at top of file:

```python
import warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_api.py -xvs`
Expected: PASS (all existing + new tests)

- [ ] **Step 5: Commit**

```bash
git add src/chardet/__init__.py tests/test_api.py
git commit -m "feat: add compat_names and prefer_superset parameters to detect()"
```

---

### Task 3: Add same parameters to `UniversalDetector`

**Files:**
- Modify: `src/chardet/detector.py`
- Test: `tests/test_detector.py`

- [ ] **Step 1: Write failing test**

```python
def test_universal_detector_compat_names() -> None:
    """UniversalDetector respects compat_names parameter."""
    detector = UniversalDetector(compat_names=True)
    detector.feed("日本語".encode("utf-8"))
    detector.close()
    assert detector.result["encoding"] is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_detector.py::test_universal_detector_compat_names -xvs`
Expected: FAIL with `TypeError: unexpected keyword argument 'compat_names'`

- [ ] **Step 3: Implement in `detector.py`**

Add `prefer_superset` and `compat_names` parameters to `UniversalDetector.__init__()`. Deprecate `should_rename_legacy`. Apply the same two-step flow in the `result` property.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_detector.py -xvs`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/chardet/detector.py tests/test_detector.py
git commit -m "feat: add compat_names and prefer_superset to UniversalDetector"
```

---

### Task 4: Rename `apply_legacy_rename` to `apply_preferred_superset`

**Files:**
- Modify: `src/chardet/equivalences.py`
- Modify: `src/chardet/__init__.py`
- Modify: `src/chardet/detector.py`

- [ ] **Step 1: Rename function and add alias**

In `equivalences.py`, rename `apply_legacy_rename` to `apply_preferred_superset`. Keep `apply_legacy_rename` as a deprecated alias.

- [ ] **Step 2: Update all call sites**

In `__init__.py` and `detector.py`, change `apply_legacy_rename` → `apply_preferred_superset`.

- [ ] **Step 3: Run full test suite**

Run: `uv run python -m pytest tests/ -x`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/chardet/equivalences.py src/chardet/__init__.py src/chardet/detector.py
git commit -m "refactor: rename apply_legacy_rename to apply_preferred_superset"
```

---

## Chunk 2: Registry Rename

### Task 5: Switch `EncodingName` type and all `EncodingInfo` entries to codec names

This is the core change. After this task, ALL internal encoding names are Python codec names.

**Files:**
- Modify: `src/chardet/registry.py`

**Important:** The `EncodingName` Literal type and every `EncodingInfo(name=...)` must change. The `python_codec` field becomes redundant but is kept temporarily (removed in Task 12). Old display-cased names must be added to `aliases` for backward-compat lookups (model keys, `lookup_encoding()` callers).

- [ ] **Step 1: Generate the new registry programmatically**

Write a script at `/tmp/gen_registry.py` that reads the current registry and outputs the updated `EncodingName` Literal and all `EncodingInfo` entries with:
- `name` = `codecs.lookup(python_codec).name`
- `python_codec` = same as `name` (kept temporarily)
- `aliases` = existing aliases + old display-cased name (if different from codec name)

Run it and paste the output into `registry.py`.

- [ ] **Step 2: Update `EncodingName` Literal type**

Replace the Literal type (lines 13-100) with codec names. Example:

```python
EncodingName = Literal[
    "ascii",
    "big5hkscs",
    "cp1250",
    ...
    "utf-8",
    "utf-8-sig",
]
```

- [ ] **Step 3: Update all `EncodingInfo` entries**

Change every `name=` field. Example:

```python
# Before:
EncodingInfo(name="Windows-1252", aliases=("cp1252", "windows-1252", ...), python_codec="cp1252", ...)

# After:
EncodingInfo(name="cp1252", aliases=("Windows-1252", "cp1252", "windows-1252", ...), python_codec="cp1252", ...)
```

- [ ] **Step 4: Run existing tests (expect some failures)**

Run: `uv run python -m pytest tests/test_api.py tests/test_models.py -x --tb=short`

At this point, pipeline modules still return old names but registry uses codec names. Tests that go through the full pipeline with `compat_names=True` should still pass because `apply_compat_names()` maps codec→display. Tests that check internal names directly will fail — that's expected and fixed in Task 7.

- [ ] **Step 5: Commit (WIP)**

```bash
git add src/chardet/registry.py
git commit -m "wip: switch EncodingName to Python codec names"
```

---

### Task 6: Update all pipeline modules to use codec names

**Files:**
- Modify: `src/chardet/pipeline/bom.py`
- Modify: `src/chardet/pipeline/escape.py`
- Modify: `src/chardet/pipeline/ascii.py`
- Modify: `src/chardet/pipeline/utf8.py`
- Modify: `src/chardet/pipeline/utf1632.py`
- Modify: `src/chardet/pipeline/orchestrator.py`

- [ ] **Step 1: Update `bom.py`**

```python
# Change _BOMS tuple entries:
"UTF-32-BE" → "utf-32-be"
"UTF-32-LE" → "utf-32-le"
"UTF-8-SIG" → "utf-8-sig"
"UTF-16-BE" → "utf-16-be"
"UTF-16-LE" → "utf-16-le"
```

- [ ] **Step 2: Update `escape.py`**

```python
# Change all DetectionResult encoding= values:
"ISO-2022-JP-2004" → "iso2022_jp_2004"
"ISO-2022-JP-EXT"  → "iso2022_jp_ext"
"ISO-2022-JP-2"    → "iso2022_jp_2"
"ISO-2022-KR"      → "iso2022_kr"
"HZ-GB-2312"       → "hz"
"UTF-7"             → "utf-7"
```

- [ ] **Step 3: Update `ascii.py`**

```python
"ASCII" → "ascii"
```

- [ ] **Step 4: Update `utf8.py`**

```python
"UTF-8" → "utf-8"
```

- [ ] **Step 5: Update `utf1632.py`**

```python
"UTF-32-BE" → "utf-32-be"
"UTF-32-LE" → "utf-32-le"
"UTF-16-LE" → "utf-16-le"
"UTF-16-BE" → "utf-16-be"
```

- [ ] **Step 6: Update `orchestrator.py`**

```python
# _EMPTY_RESULT:
"UTF-8" → "utf-8"

# _FALLBACK_RESULT:
"Windows-1252" → "cp1252"

# _COMMON_LATIN_ENCODINGS:
"ISO-8859-1" → "iso8859-1"
"ISO-8859-15" → "iso8859-15"
"Windows-1252" → "cp1252"

# _DEMOTION_CANDIDATES keys:
"ISO-8859-10" → "iso8859-10"
"ISO-8859-14" → "iso8859-14"
"Windows-1254" → "cp1254"

# _promote_koi8t():
"KOI8-R" → "koi8-r"
"KOI8-T" → "koi8-t"

# _postprocess_results():
"UTF-8" → "utf-8"
```

- [ ] **Step 7: Commit**

```bash
git add src/chardet/pipeline/
git commit -m "refactor: switch all pipeline modules to Python codec names"
```

---

### Task 7: Update equivalences dicts to codec names

**Files:**
- Modify: `src/chardet/equivalences.py`

- [ ] **Step 1: Update `SUPERSETS` dict**

Change all keys and values to codec names. Use `codecs.lookup(name).name` for every entry. For names that aren't valid Python codecs (e.g., `"GBK"`, `"Shift_JIS"`, `"ISO-8859-11"`), keep the existing form — `normalize_encoding_name()` handles the normalization.

```python
SUPERSETS: dict[str, frozenset[str]] = {
    "ascii": frozenset({"utf-8", "cp1252"}),
    "tis-620": frozenset({"ISO-8859-11", "cp874"}),
    "ISO-8859-11": frozenset({"cp874"}),
    "GB2312": frozenset({"gb18030"}),
    "GBK": frozenset({"gb18030"}),
    "Big5": frozenset({"big5hkscs", "CP950"}),
    "Shift_JIS": frozenset({"cp932", "shift_jis_2004"}),
    "Shift-JISX0213": frozenset({"shift_jis_2004"}),
    "EUC-JP": frozenset({"euc_jis_2004"}),
    "EUC-JISX0213": frozenset({"euc_jis_2004"}),
    "euc_kr": frozenset({"cp949"}),
    "CP037": frozenset({"cp1140"}),
    "ISO-2022-JP": frozenset({"iso2022_jp_2", "iso2022_jp_2004", "iso2022_jp_ext"}),
    "ISO2022-JP-1": frozenset({"iso2022_jp_2", "iso2022_jp_ext"}),
    "ISO2022-JP-3": frozenset({"iso2022_jp_2004"}),
    "iso8859-1": frozenset({"cp1252"}),
    "iso8859-2": frozenset({"cp1250"}),
    "iso8859-5": frozenset({"cp1251"}),
    "iso8859-6": frozenset({"cp1256"}),
    "iso8859-7": frozenset({"cp1253"}),
    "iso8859-8": frozenset({"cp1255"}),
    "iso8859-9": frozenset({"cp1254"}),
    "iso8859-13": frozenset({"cp1257"}),
}
```

Note: Keys like `"GB2312"`, `"GBK"`, `"Big5"`, `"Shift_JIS"`, `"EUC-JP"`, `"EUC-JISX0213"`, `"ISO-8859-11"`, `"CP037"`, `"ISO-2022-JP"`, `"ISO2022-JP-1"`, `"ISO2022-JP-3"`, `"Shift-JISX0213"` are test-data directory names / external names that get normalized via `normalize_encoding_name()` at lookup time. They are NOT chardet canonical names and don't need to be codec names. Only the VALUES (which are chardet detection outputs) need to be codec names.

- [ ] **Step 2: Update `PREFERRED_SUPERSET` dict**

```python
PREFERRED_SUPERSET: dict[str, str] = {
    "ascii": "cp1252",
    "euc_kr": "cp949",
    "iso8859-1": "cp1252",
    "iso8859-2": "cp1250",
    "iso8859-5": "cp1251",
    "iso8859-6": "cp1256",
    "iso8859-7": "cp1253",
    "iso8859-8": "cp1255",
    "iso8859-9": "cp1254",
    "ISO-8859-11": "cp874",
    "iso8859-13": "cp1257",
    "tis-620": "cp874",
}
```

Note: `"ISO-8859-11"` is NOT in the Python codecs registry, so it stays as-is. It's only a key here, never a detection output.

- [ ] **Step 3: Update `BIDIRECTIONAL_GROUPS`**

```python
BIDIRECTIONAL_GROUPS: tuple[tuple[str, ...], ...] = (
    ("utf-16", "utf-16-le", "utf-16-be"),
    ("utf-32", "utf-32-le", "utf-32-be"),
    ("iso2022_jp_2", "iso2022_jp_2004", "iso2022_jp_ext"),
)
```

- [ ] **Step 4: Update module docstring**

Update the module docstring (lines 1-23) to reflect the new naming scheme.

- [ ] **Step 5: Run full test suite**

Run: `uv run python -m pytest tests/ -x --tb=short`

At this point, the internal rename is complete. Tests going through the public API with `compat_names=True` (default) should pass because `apply_compat_names()` maps codec→display names. Pipeline-level tests (test_escape.py, test_bom.py, etc.) will fail — fixed in Task 8.

- [ ] **Step 6: Commit**

```bash
git add src/chardet/equivalences.py
git commit -m "refactor: switch equivalences dicts to Python codec names"
```

---

### Task 8: Update all test assertions

**Files:**
- Modify: `tests/test_escape.py` — all `result.encoding == "..."` assertions
- Modify: `tests/test_bom.py` — if it exists, BOM encoding assertions
- Modify: `tests/test_models.py` — fix `test_enc_index_alias_resolution`
- Modify: other test files with internal encoding name assertions

Tests that call pipeline functions directly (not through `detect()`) will see codec names. Tests that call `detect()` see compat names (default) or codec names (`compat_names=False`).

- [ ] **Step 1: Update `test_escape.py`**

Change all `result.encoding == "..."` assertions to codec names:

```python
"ISO-2022-JP-2"    → "iso2022_jp_2"
"ISO-2022-JP-2004" → "iso2022_jp_2004"
"ISO-2022-JP-EXT"  → "iso2022_jp_ext"
"ISO-2022-KR"      → "iso2022_kr"
"HZ-GB-2312"       → "hz"
"UTF-7"             → "utf-7"
```

Also update confidence checks: `0.95` is `DETERMINISTIC_CONFIDENCE`.

- [ ] **Step 2: Update other pipeline-level test files**

For each test file that imports pipeline functions directly and asserts on `result.encoding`:
- `tests/test_bom.py`
- `tests/test_utf8.py`
- `tests/test_utf1632.py`
- `tests/test_ascii.py`
- `tests/test_orchestrator.py`

Change assertions to use codec names.

- [ ] **Step 3: Update `test_models.py`**

Fix `test_enc_index_alias_resolution`: the test uses `"utf8"` as a non-canonical alias and expects both `"utf8"` and `"UTF-8"` to resolve. After the rename, the canonical name is `"utf-8"` (codec name). Update:

```python
# The canonical name "utf-8" should be present via alias resolution
assert "utf-8" in index
assert index["utf-8"] is index["utf8"]
```

- [ ] **Step 4: Update API-level tests that use `compat_names=False`**

For tests that call `detect()` or `detect_all()` and want to test raw codec names, add `compat_names=False`. For tests that check default output, assertions should use 5.x display names (compat mode).

- [ ] **Step 5: Run full test suite**

Run: `uv run python -m pytest tests/ -x`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add tests/
git commit -m "test: update all assertions for Python codec name internals"
```

---

## Chunk 3: Models & Training

### Task 9: Update `scripts/train.py` to use ISO language codes + codec names

**Files:**
- Modify: `scripts/train.py`

- [ ] **Step 1: Update model key format**

Model keys currently use `"French/Windows-1252"` format. Change to `"fr/cp1252"`:

In `train.py`, find where model keys are constructed (the `ENCODING_LANG_MAP` dict and the training loop). Update to use:
- ISO 639-1 language codes (from `EncodingInfo.languages`)
- Codec names (from `EncodingInfo.name`, which is now the codec name)

Update `ENCODING_LANG_MAP` construction:

```python
# Before:
ENCODING_LANG_MAP["UTF-8"] = _ALL_LANGS

# After:
ENCODING_LANG_MAP["utf-8"] = _ALL_LANGS
```

- [ ] **Step 2: Update model key parsing in `models/__init__.py`**

In `get_enc_index()` (line 144), the split `lang, enc = key.split("/", 1)` still works. The alias resolution at line 150 (`canonical = lookup_encoding(enc_name)`) handles both old and new key formats since old display names are in aliases.

No code change needed — just verify it works with new keys.

- [ ] **Step 3: Retrain models**

Run: `uv run python scripts/train.py`

Verify the new model keys use the `"fr/cp1252"` format.

- [ ] **Step 4: Run tests**

Run: `uv run python -m pytest tests/test_models.py tests/test_accuracy.py -x`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/train.py src/chardet/models/
git commit -m "feat: retrain models with ISO language codes and codec name keys"
```

---

### Task 10: Update `collect_test_files()` normalization

**Files:**
- Modify: `scripts/utils.py`

- [ ] **Step 1: Normalize parsed encoding names**

In `collect_test_files()`, the encoding name parsed from directory names (e.g., `"utf-8"` from `"utf-8-en"`) should be normalized through `codecs.lookup().name` so comparisons against codec names work:

```python
from chardet.equivalences import normalize_encoding_name

# After parsing encoding_name from directory name:
if encoding_name is not None:
    encoding_name = normalize_encoding_name(encoding_name)
```

- [ ] **Step 2: Run accuracy tests**

Run: `uv run python -m pytest tests/test_accuracy.py -x`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add scripts/utils.py
git commit -m "fix: normalize test data encoding names to codec format"
```

---

## Chunk 4: Cleanup

### Task 11: Remove `EncodingInfo.python_codec` field

**Files:**
- Modify: `src/chardet/registry.py`
- Modify: `src/chardet/pipeline/validity.py` (uses `enc.python_codec`)
- Modify: any other file referencing `.python_codec`

- [ ] **Step 1: Find all `.python_codec` usages**

Run: `grep -rn "python_codec" src/chardet/`

- [ ] **Step 2: Replace all usages with `.name`**

In `validity.py` and any other files, change `enc.python_codec` → `enc.name`.

- [ ] **Step 3: Remove the field from `EncodingInfo`**

In `registry.py`, remove the `python_codec` parameter from the dataclass and all `EncodingInfo(...)` constructor calls.

- [ ] **Step 4: Run full test suite**

Run: `uv run python -m pytest tests/ -x`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/chardet/
git commit -m "refactor: remove redundant EncodingInfo.python_codec field"
```

---

### Task 12: Final verification

- [ ] **Step 1: Run full test suite**

Run: `uv run python -m pytest tests/ -x`
Expected: ALL PASS

- [ ] **Step 2: Verify default output unchanged**

Write a quick check script:

```python
import chardet
# Default (compat_names=True) should return display names
result = chardet.detect("日本語".encode("utf-8"))
assert result["encoding"] == "utf-8"  # 5.x compat name

result = chardet.detect("Hello World".encode("ascii"))
assert result["encoding"] == "ascii"  # 5.x compat name

# compat_names=False should return codec names
result = chardet.detect("日本語".encode("utf-8"), compat_names=False)
assert result["encoding"] == "utf-8"  # codec name (same for utf-8)
```

- [ ] **Step 3: Verify prefer_superset works**

```python
result = chardet.detect(b"Hello", prefer_superset=True, compat_names=True)
# ASCII -> Windows-1252 (superset remap + compat name)

result = chardet.detect(b"Hello", prefer_superset=True, compat_names=False)
# ASCII -> cp1252 (superset remap, raw codec name)
```

- [ ] **Step 4: Run linting**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: PASS

- [ ] **Step 5: Final commit if any fixes needed**
