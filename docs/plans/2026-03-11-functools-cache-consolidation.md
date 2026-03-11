# functools.cache Consolidation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all hand-rolled double-checked-locking caches with `functools.cache` and consolidate `normalize_encoding_name` into `lookup_encoding`.

**Architecture:** Every load-once cache (`_LOOKUP_CACHE`, `_CANDIDATES_CACHE`, `_MODEL_CACHE`/`_MODEL_NORMS`, `_ENC_INDEX`, `_CONFUSION_CACHE`) becomes a `@functools.cache`-decorated function. `normalize_encoding_name` is removed; all callers use `lookup_encoding` from `registry.py`. Tests that previously reset caches by setting globals to `None` switch to `function.cache_clear()`.

**Tech Stack:** Python 3.10+ `functools.cache`, mypyc-compatible

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/chardet/registry.py` | Modify | Simplify `lookup_encoding` and `get_candidates` with `@functools.cache` |
| `src/chardet/equivalences.py` | Modify | Remove `normalize_encoding_name`, use `lookup_encoding` |
| `src/chardet/models/__init__.py` | Modify | Replace model/index caches with `@functools.cache` |
| `src/chardet/pipeline/confusion.py` | Modify | Replace confusion cache with `@functools.cache` |
| `scripts/diagnose_accuracy.py` | Modify | Update import from `normalize_encoding_name` to `lookup_encoding` |
| `tests/test_registry.py` | Modify | Update `test_build_lookup_cache_handles_invalid_codec` |
| `tests/test_models.py` | Modify | Update `mock_models_bin` fixture to use `cache_clear()` |
| `tests/test_confusion.py` | Modify | Update cache reset to use `cache_clear()` |
| `tests/test_thread_safety.py` | Modify | Update cold-cache test to use `cache_clear()` |

---

## Chunk 1: registry.py caches

### Task 1: Simplify `lookup_encoding` with `@functools.cache`

**Files:**
- Modify: `src/chardet/registry.py:5-7` (imports), `791-834` (cache + function)
- Modify: `tests/test_registry.py:307-325` (test referencing `_build_lookup_cache`)

- [ ] **Step 1: Rewrite `lookup_encoding` with `@functools.cache`**

In `src/chardet/registry.py`:

1. Add `import functools` to imports.
2. Delete `_LOOKUP_CACHE`, `_LOOKUP_CACHE_LOCK`, and `_build_lookup_cache` entirely (lines 791–826).
3. Replace `lookup_encoding` (lines 814–834) with:

```python
@functools.cache
def lookup_encoding(name: str) -> EncodingName | None:
    """Convert an encoding name string to the canonical EncodingName.

    Handles arbitrary casing, aliases, and Python codec names.

    :param name: Any encoding name string.
    :returns: The canonical :data:`EncodingName`, or ``None`` if unknown.
    """
    lowered = name.lower()
    for entry in REGISTRY.values():
        if entry.name == lowered:
            return entry.name
        for alias in entry.aliases:
            if alias.lower() == lowered:
                return entry.name
    # Fallback: resolve through Python's codec registry
    try:
        codec_name = codecs.lookup(name).name
    except LookupError:
        return None
    if codec_name != lowered:
        return lookup_encoding(codec_name)
    return None
```

4. Remove `import threading` if no other uses remain (check: `_CANDIDATES_CACHE_LOCK` is removed in Task 2).

- [ ] **Step 2: Update test for removed `_build_lookup_cache`**

In `tests/test_registry.py`, replace `test_build_lookup_cache_handles_invalid_codec` (lines 307–325) with a test that exercises `lookup_encoding` directly for the same scenario:

```python
def test_lookup_encoding_unknown_codec():
    """lookup_encoding returns None for names that aren't in the registry
    and don't resolve through codecs.lookup either."""
    assert lookup_encoding("no_such_codec_xyz") is None
```

- [ ] **Step 3: Run tests to verify**

Run: `uv run python -m pytest tests/test_registry.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add src/chardet/registry.py tests/test_registry.py
git commit -m "refactor: replace lookup_encoding cache with functools.cache"
```

### Task 2: Simplify `get_candidates` with `@functools.cache`

**Files:**
- Modify: `src/chardet/registry.py:138-158` (cache + function)

- [ ] **Step 1: Rewrite `get_candidates`**

Delete `_CANDIDATES_CACHE` and `_CANDIDATES_CACHE_LOCK` (lines 138–139). Replace `get_candidates` (lines 142–158) with:

```python
@functools.cache
def get_candidates(era: EncodingEra) -> tuple[EncodingInfo, ...]:
    """Return registry entries matching the given era filter.

    :param era: Bit flags specifying which encoding eras to include.
    :returns: A tuple of matching :class:`EncodingInfo` entries.
    """
    return tuple(enc for enc in REGISTRY.values() if enc.era & era)
```

Now remove `import threading` from `registry.py` (no remaining uses).

- [ ] **Step 2: Run tests to verify**

Run: `uv run python -m pytest tests/test_registry.py -v`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add src/chardet/registry.py
git commit -m "refactor: replace get_candidates cache with functools.cache"
```

---

## Chunk 2: equivalences.py consolidation

### Task 3: Replace `normalize_encoding_name` with `lookup_encoding`

**Files:**
- Modify: `src/chardet/equivalences.py:27` (imports), `33-42` (function), `251-265` (normalized lookups), `289-290`, `367-368`
- Modify: `scripts/diagnose_accuracy.py:24,83,141,170`

- [ ] **Step 1: Update `equivalences.py`**

1. Remove `import codecs` (line 27).
2. Add `from chardet.registry import lookup_encoding` to existing imports (after line 30).
3. Delete the `normalize_encoding_name` function (lines 33–42).
4. Replace `_NORMALIZED_SUPERSETS` construction (lines 251–256) with:

```python
_NORMALIZED_SUPERSETS: dict[str, frozenset[str]] = {
    lookup_encoding(subset) or subset: frozenset(
        lookup_encoding(s) or s for s in supersets
    )
    for subset, supersets in SUPERSETS.items()
}
```

5. Replace `_build_bidir_index` body (lines 262–265) — update the three `normalize_encoding_name` calls:

```python
def _build_bidir_index() -> dict[str, frozenset[str]]:
    """Build the bidirectional equivalence lookup index."""
    result: dict[str, frozenset[str]] = {}
    for group in BIDIRECTIONAL_GROUPS:
        normed = frozenset(lookup_encoding(n) or n for n in group)
        for name in group:
            result[lookup_encoding(name) or name] = normed
    return result
```

6. In `is_correct` (lines 289–290), replace:

```python
    norm_exp = lookup_encoding(expected) or expected.lower()
    norm_det = lookup_encoding(detected) or detected.lower()
```

7. In `is_equivalent_detection` (lines 367–368), same replacement:

```python
    norm_exp = lookup_encoding(expected) or expected.lower()
    norm_det = lookup_encoding(detected) or detected.lower()
```

- [ ] **Step 2: Update `scripts/diagnose_accuracy.py`**

1. Change import (line 24): remove `normalize_encoding_name` from the `chardet.equivalences` import.
2. Add: `from chardet.registry import lookup_encoding`
3. Replace all `normalize_encoding_name(x)` calls (lines 83, 141, 170) with `lookup_encoding(x) or x`.

- [ ] **Step 3: Run tests to verify**

Run: `uv run python -m pytest tests/ -v`
Expected: All pass (equivalences tests, accuracy tests, API tests)

- [ ] **Step 4: Commit**

```bash
git add src/chardet/equivalences.py scripts/diagnose_accuracy.py
git commit -m "refactor: drop normalize_encoding_name, use lookup_encoding"
```

---

## Chunk 3: models/__init__.py caches

### Task 4: Replace model caches with `@functools.cache`

**Files:**
- Modify: `src/chardet/models/__init__.py:8-28` (imports/globals), `94-131` (`load_models`), `156-165` (`get_enc_index`), `187-193` (`_get_model_norms`)
- Modify: `tests/test_models.py:207-233` (`mock_models_bin` fixture)
- Modify: `tests/test_thread_safety.py:96-122` (cold-cache test)

- [ ] **Step 1: Rewrite model loading with `@functools.cache`**

In `src/chardet/models/__init__.py`:

1. Add `import functools` to imports.
2. Remove `import threading`.
3. Delete globals: `_MODEL_CACHE`, `_MODEL_NORMS`, `_MODEL_CACHE_LOCK`, `_ENC_INDEX`, `_ENC_INDEX_LOCK` (lines 23–28).
4. Create a cached combined loader, and update `load_models` and `_get_model_norms` to use it:

```python
@functools.cache
def _load_models_data() -> tuple[dict[str, bytearray], dict[str, float]]:
    """Load and parse models.bin, returning (models, norms).

    Cached: only reads from disk on first call.
    """
    ref = importlib.resources.files("chardet.models").joinpath("models.bin")
    data = ref.read_bytes()

    if not data:
        warnings.warn(
            "chardet models.bin is empty — statistical detection disabled; "
            "reinstall chardet to fix",
            RuntimeWarning,
            stacklevel=2,
        )
        return {}, {}

    return _parse_models_bin(data)


def load_models() -> dict[str, bytearray]:
    """Load all bigram models from the bundled models.bin file.

    Each model is a bytearray of length 65536 (256*256).
    Index: (b1 << 8) | b2 -> weight (0-255).

    :returns: A dict mapping model key strings to 65536-byte lookup tables.
    """
    return _load_models_data()[0]


def _get_model_norms() -> dict[str, float]:
    """Return cached L2 norms for all models, keyed by model key string."""
    return _load_models_data()[1]
```

5. Replace `get_enc_index` (lines 156–165):

```python
@functools.cache
def get_enc_index() -> dict[str, list[tuple[str | None, bytearray, str]]]:
    """Return a pre-grouped index mapping encoding name -> [(lang, model, model_key), ...]."""
    return _build_enc_index(load_models())
```

- [ ] **Step 2: Update `tests/test_models.py` fixture**

Replace the `mock_models_bin` fixture (lines 207–233) to use `cache_clear()`:

```python
@pytest.fixture
def mock_models_bin():
    """Clear the model cache and provide a helper to mock models.bin content.

    Yields a callable ``set_data(raw_bytes)`` that configures the mock to
    return *raw_bytes* from ``models.bin``.  The cache is cleared on teardown.
    """
    import chardet.models as mod

    mod._load_models_data.cache_clear()
    mock_ref = MagicMock()

    def set_data(data: bytes) -> None:
        mock_ref.read_bytes.return_value = data

    with patch.object(
        mod.importlib.resources,
        "files",
        return_value=MagicMock(joinpath=MagicMock(return_value=mock_ref)),
    ):
        yield set_data

    mod._load_models_data.cache_clear()
```

- [ ] **Step 3: Run model tests to verify**

Run: `uv run python -m pytest tests/test_models.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add src/chardet/models/__init__.py tests/test_models.py
git commit -m "refactor: replace model caches with functools.cache"
```

---

## Chunk 4: confusion.py cache

### Task 5: Replace confusion cache with `@functools.cache`

**Files:**
- Modify: `src/chardet/pipeline/confusion.py:11-15` (imports), `68-69` (globals), `112-146` (`load_confusion_data`)
- Modify: `tests/test_confusion.py:85-128` (cache reset in two tests)

- [ ] **Step 1: Rewrite `load_confusion_data`**

In `src/chardet/pipeline/confusion.py`:

1. Add `import functools` to imports.
2. Remove `import threading`.
3. Delete `_CONFUSION_CACHE` and `_CONFUSION_CACHE_LOCK` (lines 68–69).
4. Replace `load_confusion_data` (lines 112–146):

```python
@functools.cache
def load_confusion_data() -> DistinguishingMaps:
    """Load confusion group data from the bundled confusion.bin file.

    :returns: A :data:`DistinguishingMaps` dictionary keyed by encoding pairs.
    """
    ref = importlib.resources.files("chardet.models").joinpath("confusion.bin")
    raw = ref.read_bytes()
    if not raw:
        warnings.warn(
            "chardet confusion.bin is empty — confusion resolution disabled; "
            "reinstall chardet to fix",
            RuntimeWarning,
            stacklevel=2,
        )
        return {}
    try:
        raw_maps = deserialize_confusion_data_from_bytes(raw)
    except (struct.error, UnicodeDecodeError) as e:
        msg = f"corrupt confusion.bin: {e}"
        raise ValueError(msg) from e
    # Normalize keys to canonical codec names so pipeline output matches.
    normalized: DistinguishingMaps = {}
    for (a, b), value in raw_maps.items():
        norm_a = lookup_encoding(a) or a
        norm_b = lookup_encoding(b) or b
        normalized[(norm_a, norm_b)] = value
    return normalized
```

- [ ] **Step 2: Update `tests/test_confusion.py` cache resets**

In `test_load_confusion_data_empty_file` (lines 85–105) and `test_load_confusion_data_corrupt_file` (lines 108–128), replace the `_CONFUSION_CACHE = None` / restore pattern with `cache_clear()`.

For `test_load_confusion_data_empty_file`:

```python
def test_load_confusion_data_empty_file():
    """Empty confusion.bin should emit RuntimeWarning and return empty dict."""
    import chardet.pipeline.confusion as mod

    mod.load_confusion_data.cache_clear()
    try:
        mock_ref = MagicMock()
        mock_ref.read_bytes.return_value = b""
        with (
            patch.object(
                mod.importlib.resources,
                "files",
                return_value=MagicMock(joinpath=MagicMock(return_value=mock_ref)),
            ),
            pytest.warns(RuntimeWarning, match="confusion.bin is empty"),
        ):
            result = mod.load_confusion_data()
        assert result == {}
    finally:
        mod.load_confusion_data.cache_clear()
```

For `test_load_confusion_data_corrupt_file`:

```python
def test_load_confusion_data_corrupt_file():
    """Corrupt confusion.bin should raise ValueError."""
    import chardet.pipeline.confusion as mod

    mod.load_confusion_data.cache_clear()
    try:
        mock_ref = MagicMock()
        # Valid num_pairs=1 but truncated after that
        mock_ref.read_bytes.return_value = struct.pack("!H", 1)
        with (
            patch.object(
                mod.importlib.resources,
                "files",
                return_value=MagicMock(joinpath=MagicMock(return_value=mock_ref)),
            ),
            pytest.raises(ValueError, match=r"corrupt confusion\.bin"),
        ):
            mod.load_confusion_data()
    finally:
        mod.load_confusion_data.cache_clear()
```

- [ ] **Step 3: Run confusion tests**

Run: `uv run python -m pytest tests/test_confusion.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add src/chardet/pipeline/confusion.py tests/test_confusion.py
git commit -m "refactor: replace confusion cache with functools.cache"
```

---

## Chunk 5: Thread safety test + final verification

### Task 6: Update thread safety test

**Files:**
- Modify: `tests/test_thread_safety.py:80-122`

- [ ] **Step 1: Update cold-cache test**

Replace `test_cold_cache_concurrent_init` (lines 80–122) to use `cache_clear()`:

```python
@pytest.mark.serial
def test_cold_cache_concurrent_init():
    """Race on first-call cache initialization from a cold state.

    Clears all functools.cache-backed caches, then has many threads
    simultaneously call detect().  This stresses the cache population
    path — the most dangerous codepath for thread safety.

    Marked ``serial`` because the global cache mutations are not safe to
    run concurrently with other tests that call ``detect()``.
    """
    import chardet.models as _models
    import chardet.pipeline.confusion as _confusion
    import chardet.registry as _registry

    try:
        # Clear all caches to cold state.
        _models._load_models_data.cache_clear()
        _models.get_enc_index.cache_clear()
        _confusion.load_confusion_data.cache_clear()
        _registry.lookup_encoding.cache_clear()
        _registry.get_candidates.cache_clear()

        errors = _run_concurrent_detect(n_workers=6, iterations=5)
        assert not errors, "Cold-cache race violations:\n" + "\n".join(errors[:10])
    finally:
        # Clear and let caches re-populate naturally on next use.
        _models._load_models_data.cache_clear()
        _models.get_enc_index.cache_clear()
        _confusion.load_confusion_data.cache_clear()
        _registry.lookup_encoding.cache_clear()
        _registry.get_candidates.cache_clear()
```

- [ ] **Step 2: Run thread safety tests**

Run: `uv run python -m pytest tests/test_thread_safety.py -v`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_thread_safety.py
git commit -m "refactor: update thread safety test for functools.cache"
```

### Task 7: Full test suite verification

- [ ] **Step 1: Run all tests**

Run: `uv run python -m pytest`
Expected: All pass, 0 skipped (after the earlier test data path fixes), 0 failures

- [ ] **Step 2: Run linter**

Run: `uv run ruff check .`
Expected: No errors

- [ ] **Step 3: Final commit if any fixups needed**
