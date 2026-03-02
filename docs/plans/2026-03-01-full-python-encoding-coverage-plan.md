# Full Python Encoding Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Support every Python character encoding (excluding transforms) by adding 15 missing encodings as aliases and flipping superset relationships so the broadest encoding per family is the primary.

**Architecture:** Add aliases to existing registry entries, rename 5 entries to their broader supersets, split ISO-2022-JP into 3 branch entries, update the structural analyzer dispatch table, enhance the escape detector to differentiate ISO-2022-JP branches, fix model loading to resolve aliases, and update equivalences.

**Tech Stack:** Python 3.10+, pytest, ruff

---

### Task 1: Registry — Flip Big5 to big5hkscs

**Files:**
- Modify: `src/chardet/registry.py:132-139`

**Step 1: Write the failing test**

In `tests/test_registry.py`, add a test that the Big5 family entry is named `big5hkscs` and includes all expected aliases.

```python
def test_big5_family_uses_broadest_superset() -> None:
    entry = next(e for e in REGISTRY if e.python_codec == "big5hkscs")
    assert entry.name == "big5hkscs"
    assert "big5" in entry.aliases
    assert "cp950" in entry.aliases
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_registry.py::test_big5_family_uses_broadest_superset -v`
Expected: FAIL (current entry is named `big5` with `python_codec="big5"`)

**Step 3: Update the registry entry**

In `src/chardet/registry.py`, change the Big5 entry (lines 132-139):

```python
EncodingInfo(
    name="big5hkscs",
    aliases=("big5", "big5-tw", "csbig5", "cp950"),
    era=EncodingEra.MODERN_WEB,
    is_multibyte=True,
    python_codec="big5hkscs",
    languages=("zh",),
),
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_registry.py::test_big5_family_uses_broadest_superset -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/registry.py tests/test_registry.py
git commit -m "refactor: flip big5 to big5hkscs as primary (broadest superset)"
```

---

### Task 2: Registry — Add gb2312/gbk aliases to gb18030

**Files:**
- Modify: `src/chardet/registry.py:172-179`

**Step 1: Write the failing test**

```python
def test_gb18030_has_subset_aliases() -> None:
    entry = next(e for e in REGISTRY if e.name == "gb18030")
    assert "gb2312" in entry.aliases
    assert "gbk" in entry.aliases
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_registry.py::test_gb18030_has_subset_aliases -v`
Expected: FAIL (current aliases are only `("gb-18030",)`)

**Step 3: Add aliases**

In `src/chardet/registry.py`, update the gb18030 entry's aliases (line 174):

```python
aliases=("gb-18030", "gb2312", "gbk"),
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_registry.py::test_gb18030_has_subset_aliases -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/registry.py tests/test_registry.py
git commit -m "refactor: add gb2312 and gbk as aliases of gb18030"
```

---

### Task 3: Registry — Flip euc-jp to euc-jis-2004

**Files:**
- Modify: `src/chardet/registry.py:156-163`

**Step 1: Write the failing test**

```python
def test_euc_jp_family_uses_broadest_superset() -> None:
    entry = next(e for e in REGISTRY if e.python_codec == "euc_jis_2004")
    assert entry.name == "euc-jis-2004"
    assert "euc-jp" in entry.aliases
    assert "euc-jisx0213" in entry.aliases
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_registry.py::test_euc_jp_family_uses_broadest_superset -v`
Expected: FAIL

**Step 3: Update the registry entry**

```python
EncodingInfo(
    name="euc-jis-2004",
    aliases=("euc-jp", "eucjp", "ujis", "u-jis", "euc-jisx0213"),
    era=EncodingEra.MODERN_WEB,
    is_multibyte=True,
    python_codec="euc_jis_2004",
    languages=("ja",),
),
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_registry.py::test_euc_jp_family_uses_broadest_superset -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/registry.py tests/test_registry.py
git commit -m "refactor: flip euc-jp to euc-jis-2004 as primary (broadest superset)"
```

---

### Task 4: Registry — Flip shift_jis to shift_jis_2004

**Files:**
- Modify: `src/chardet/registry.py:204-211`

**Step 1: Write the failing test**

```python
def test_shift_jis_family_uses_broadest_superset() -> None:
    entry = next(e for e in REGISTRY if e.python_codec == "shift_jis_2004")
    assert entry.name == "shift_jis_2004"
    assert "shift_jis" in entry.aliases
    assert "shift-jisx0213" in entry.aliases
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_registry.py::test_shift_jis_family_uses_broadest_superset -v`
Expected: FAIL

**Step 3: Update the registry entry**

```python
EncodingInfo(
    name="shift_jis_2004",
    aliases=("shift_jis", "sjis", "shiftjis", "s_jis", "shift-jisx0213"),
    era=EncodingEra.MODERN_WEB,
    is_multibyte=True,
    python_codec="shift_jis_2004",
    languages=("ja",),
),
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_registry.py::test_shift_jis_family_uses_broadest_superset -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/registry.py tests/test_registry.py
git commit -m "refactor: flip shift_jis to shift_jis_2004 as primary (broadest superset)"
```

---

### Task 5: Registry — Split ISO-2022-JP into three branch entries

**Files:**
- Modify: `src/chardet/registry.py:188-195`

**Step 1: Write the failing test**

```python
def test_iso2022_jp_split_into_branches() -> None:
    names = {e.name for e in REGISTRY}
    assert "iso2022-jp-2" in names
    assert "iso2022-jp-2004" in names
    assert "iso2022-jp-ext" in names
    # Old entry should be gone as primary
    assert "iso-2022-jp" not in names
    # But it should be an alias of iso2022-jp-2
    jp2 = next(e for e in REGISTRY if e.name == "iso2022-jp-2")
    assert "iso-2022-jp" in jp2.aliases
    assert "iso2022-jp-1" in jp2.aliases
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_registry.py::test_iso2022_jp_split_into_branches -v`
Expected: FAIL

**Step 3: Replace the single ISO-2022-JP entry with three entries**

In `src/chardet/registry.py`, replace lines 188-195 with:

```python
EncodingInfo(
    name="iso2022-jp-2",
    aliases=("iso-2022-jp", "csiso2022jp", "iso2022-jp-1"),
    era=EncodingEra.MODERN_WEB,
    is_multibyte=True,
    python_codec="iso2022_jp_2",
    languages=("ja",),
),
EncodingInfo(
    name="iso2022-jp-2004",
    aliases=("iso2022-jp-3",),
    era=EncodingEra.MODERN_WEB,
    is_multibyte=True,
    python_codec="iso2022_jp_2004",
    languages=("ja",),
),
EncodingInfo(
    name="iso2022-jp-ext",
    aliases=(),
    era=EncodingEra.MODERN_WEB,
    is_multibyte=True,
    python_codec="iso2022_jp_ext",
    languages=("ja",),
),
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_registry.py::test_iso2022_jp_split_into_branches -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/registry.py tests/test_registry.py
git commit -m "refactor: split iso-2022-jp into three branch entries (jp-2, jp-2004, jp-ext)"
```

---

### Task 6: Registry — Flip cp500 to cp1140 and add iso-8859-11 alias

**Files:**
- Modify: `src/chardet/registry.py:701-708` (cp500 entry)
- Modify: `src/chardet/registry.py:311-318` (tis-620 entry)

**Step 1: Write the failing test**

```python
def test_cp500_flipped_to_cp1140() -> None:
    entry = next(e for e in REGISTRY if e.python_codec == "cp1140")
    assert entry.name == "cp1140"
    assert "cp500" in entry.aliases

def test_tis620_has_iso8859_11_alias() -> None:
    entry = next(e for e in REGISTRY if e.name == "tis-620")
    assert "iso-8859-11" in entry.aliases
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_registry.py::test_cp500_flipped_to_cp1140 tests/test_registry.py::test_tis620_has_iso8859_11_alias -v`
Expected: FAIL

**Step 3: Update both entries**

For cp500 (MAINFRAME section), change to:

```python
EncodingInfo(
    name="cp1140",
    aliases=("cp500",),
    era=EncodingEra.MAINFRAME,
    is_multibyte=False,
    python_codec="cp1140",
    languages=("en", "fr", "de", "es", "pt", "it", "nl", "da", "sv", "no", "fi", "is", "id", "ms"),
),
```

For tis-620, add `"iso-8859-11"` to aliases:

```python
aliases=("tis620", "iso-8859-11"),
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_registry.py::test_cp500_flipped_to_cp1140 tests/test_registry.py::test_tis620_has_iso8859_11_alias -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/registry.py tests/test_registry.py
git commit -m "refactor: flip cp500 to cp1140, add iso-8859-11 alias to tis-620"
```

---

### Task 7: Structural analyzer — Update dispatch table keys

**Files:**
- Modify: `src/chardet/pipeline/structural.py:291-300`

After Tasks 1, 3, 4 renamed registry entries, the dispatch table keys must match the new names.

**Step 1: Write the failing test**

```python
def test_big5hkscs_scores_high_on_big5_data():
    data = "你好世界".encode("big5")
    score = compute_structural_score(data, _get_encoding("big5hkscs"), PipelineContext())
    assert score > 0.7

def test_euc_jis_2004_scores_high_on_euc_jp_data():
    data = "こんにちは世界".encode("euc-jp")
    score = compute_structural_score(data, _get_encoding("euc-jis-2004"), PipelineContext())
    assert score > 0.7

def test_shift_jis_2004_scores_high_on_shift_jis_data():
    data = "こんにちは世界".encode("shift_jis")
    score = compute_structural_score(data, _get_encoding("shift_jis_2004"), PipelineContext())
    assert score > 0.7
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_structural.py::test_big5hkscs_scores_high_on_big5_data tests/test_structural.py::test_euc_jis_2004_scores_high_on_euc_jp_data tests/test_structural.py::test_shift_jis_2004_scores_high_on_shift_jis_data -v`
Expected: FAIL (dispatch table has old keys `"big5"`, `"euc-jp"`, `"shift_jis"`)

**Step 3: Update the dispatch table**

In `src/chardet/pipeline/structural.py`, change the `_ANALYZERS` dict (lines 291-300):

```python
_ANALYZERS: dict[str, Callable[[bytes], tuple[float, int, int]]] = {
    "shift_jis_2004": _analyze_shift_jis,
    "cp932": _analyze_shift_jis,
    "euc-jis-2004": _analyze_euc_jp,
    "euc-kr": _analyze_euc_kr,
    "cp949": _analyze_euc_kr,
    "gb18030": _analyze_gb18030,
    "big5hkscs": _analyze_big5,
    "johab": _analyze_johab,
}
```

Note: the analyzer *functions* (`_analyze_shift_jis`, `_analyze_big5`, `_analyze_euc_jp`) remain unchanged — only the dispatch keys change. The byte-level structural analysis is identical for the broader codec variants.

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_structural.py -v`
Expected: PASS (all tests including the new ones)

Also update existing tests in `tests/test_structural.py` that reference old names: change `_get_encoding("shift_jis")` to `_get_encoding("shift_jis_2004")`, `_get_encoding("euc-jp")` to `_get_encoding("euc-jis-2004")`, `_get_encoding("big5")` to `_get_encoding("big5hkscs")`.

**Step 5: Commit**

```bash
git add src/chardet/pipeline/structural.py tests/test_structural.py
git commit -m "refactor: update structural analyzer dispatch keys for renamed encodings"
```

---

### Task 8: Model loading — Resolve aliases in get_enc_index()

**Files:**
- Modify: `src/chardet/models/__init__.py:97-115`

Models are keyed by old names (e.g., `zh/big5`). After the registry renames, `get_enc_index()` must map these to the new primary names.

**Step 1: Write the failing test**

```python
from chardet.models import get_enc_index

def test_enc_index_resolves_aliases() -> None:
    index = get_enc_index()
    # big5 model should be accessible under big5hkscs
    assert "big5hkscs" in index
    # euc-jp model should be accessible under euc-jis-2004
    assert "euc-jis-2004" in index
    # shift_jis model should be accessible under shift_jis_2004
    assert "shift_jis_2004" in index
    # cp500 model should be accessible under cp1140
    assert "cp1140" in index
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_models.py::test_enc_index_resolves_aliases -v`
Expected: FAIL (models keyed as `zh/big5` etc. don't match new names)

**Step 3: Add alias resolution to get_enc_index()**

In `src/chardet/models/__init__.py`, build a reverse alias map from the registry and use it in `get_enc_index()`. After the main loop that builds the index from model keys, add a second pass that maps old names to new names:

```python
def get_enc_index() -> dict[str, list[tuple[str | None, bytearray]]]:
    """Return a pre-grouped index mapping encoding name -> [(lang, model), ...]."""
    global _ENC_INDEX  # noqa: PLW0603
    if _ENC_INDEX is not None:
        return _ENC_INDEX
    with _ENC_INDEX_LOCK:
        models = load_models()
        index: dict[str, list[tuple[str | None, bytearray]]] = {}
        for key, model in models.items():
            if "/" in key:
                lang, enc = key.split("/", 1)
                index.setdefault(enc, []).append((lang, model))
            else:
                index.setdefault(key, []).append((None, model))

        # Resolve aliases: if a model key matches a registry alias but not
        # the primary name, copy the entry under the primary name.
        alias_to_primary: dict[str, str] = {}
        for entry in REGISTRY:
            for alias in entry.aliases:
                alias_to_primary[alias] = entry.name
        for alias, primary in alias_to_primary.items():
            if alias in index and primary not in index:
                index[primary] = index[alias]

        _ENC_INDEX = index
        return index
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/test_models.py::test_enc_index_resolves_aliases -v`
Expected: PASS

**Step 5: Also remove the gb2312 hack from _SINGLE_LANG_MAP**

In `src/chardet/models/__init__.py`, lines 32-33, remove:

```python
# gb2312 is not in the registry (detector returns gb18030 instead) but
# needs a language mapping for accuracy test evaluation.
_SINGLE_LANG_MAP["gb2312"] = "zh"
```

This hack is no longer needed since gb2312 is now an alias of gb18030 in the registry. Since `_SINGLE_LANG_MAP` is built from `enc.name` keys and gb18030 has `languages=("zh",)`, it's already covered. (gb2312 in accuracy test expected values is handled by `equivalences.py`, not by this map.)

**Step 6: Commit**

```bash
git add src/chardet/models/__init__.py tests/test_models.py
git commit -m "feat: resolve registry aliases in model index, remove gb2312 hack"
```

---

### Task 9: Escape detector — Differentiate ISO-2022-JP branches

**Files:**
- Modify: `src/chardet/pipeline/escape.py:124-130`

**Step 1: Write the failing tests**

Add to `tests/test_escape.py`:

```python
def test_iso2022_jp_base_returns_jp2() -> None:
    """Base ISO-2022-JP escape codes should default to iso2022-jp-2 (broadest)."""
    data = b"Hello \x1b$B$3$s$K$A$O\x1b(B World"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso2022-jp-2"


def test_iso2022_jp_multinational_codes() -> None:
    """Multinational escape codes (GB2312 designation) should return iso2022-jp-2."""
    # ESC $ ( A designates GB2312 — multinational branch
    data = b"\x1b$B$3$s\x1b(B\x1b$(A\x30\x21\x1b(B"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso2022-jp-2"


def test_iso2022_jp_2004_codes() -> None:
    """JIS X 0213 escape codes should return iso2022-jp-2004."""
    # ESC $ ( O designates JIS X 0213 plane 1
    data = b"\x1b$(O\x21\x21\x1b(B"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso2022-jp-2004"


def test_iso2022_jp_ext_codes() -> None:
    """Half-width katakana SI/SO should return iso2022-jp-ext."""
    # ESC $ B for JIS X 0208, then SI (0x0E) / SO (0x0F) for half-width katakana
    data = b"\x1b$B$3$s\x1b(B\x0e\xb1\xb2\x0f"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso2022-jp-ext"
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_escape.py::test_iso2022_jp_base_returns_jp2 tests/test_escape.py::test_iso2022_jp_multinational_codes tests/test_escape.py::test_iso2022_jp_2004_codes tests/test_escape.py::test_iso2022_jp_ext_codes -v`
Expected: FAIL (current detector returns `"iso-2022-jp"` for all)

**Step 3: Enhance the escape detector**

In `src/chardet/pipeline/escape.py`, replace the ISO-2022-JP detection block (lines 124-130) with variant-aware detection:

```python
# ISO-2022-JP family: check for base ESC sequences, then classify variant.
if has_esc and (b"\x1b$B" in data or b"\x1b$@" in data or b"\x1b(J" in data):
    # JIS X 0213 designation -> modern Japanese branch
    if b"\x1b$(O" in data or b"\x1b$(P" in data:
        return DetectionResult(
            encoding="iso2022-jp-2004",
            confidence=DETERMINISTIC_CONFIDENCE,
            language="ja",
        )
    # Half-width katakana SI/SO markers (0x0E / 0x0F)
    if b"\x0e" in data and b"\x0f" in data:
        return DetectionResult(
            encoding="iso2022-jp-ext",
            confidence=DETERMINISTIC_CONFIDENCE,
            language="ja",
        )
    # Multinational designations or base codes -> broadest multinational
    return DetectionResult(
        encoding="iso2022-jp-2",
        confidence=DETERMINISTIC_CONFIDENCE,
        language="ja",
    )
```

Note: ISO-2022-JP-2 multinational escape codes (`\x1b$(A`, `\x1b$(C`, `\x1b-A`, `\x1b-F`) also fall through to the `iso2022-jp-2` default, which is correct — it's the broadest multinational variant.

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_escape.py -v`
Expected: PASS (all tests including new ones)

Also update the two existing ISO-2022-JP tests to expect `"iso2022-jp-2"` instead of `"iso-2022-jp"`:
- `test_iso_2022_jp_esc_dollar_b`: change `assert result.encoding == "iso-2022-jp"` to `assert result.encoding == "iso2022-jp-2"`
- `test_iso_2022_jp_esc_dollar_at`: same change

**Step 5: Commit**

```bash
git add src/chardet/pipeline/escape.py tests/test_escape.py
git commit -m "feat: differentiate ISO-2022-JP branches in escape detector"
```

---

### Task 10: Equivalences — Update for new primary names

**Files:**
- Modify: `src/chardet/equivalences.py`

**Step 1: Write the failing test**

```python
from chardet.equivalences import is_correct

def test_superset_equivalences_for_renamed_encodings() -> None:
    # big5 expected, big5hkscs detected -> correct (superset)
    assert is_correct("big5", "big5hkscs")
    # euc-jp expected, euc-jis-2004 detected -> correct
    assert is_correct("euc-jp", "euc-jis-2004")
    # shift_jis expected, shift_jis_2004 detected -> correct
    assert is_correct("shift_jis", "shift_jis_2004")
    # cp500 expected, cp1140 detected -> correct
    assert is_correct("cp500", "cp1140")
    # iso-2022-jp expected, any branch -> correct
    assert is_correct("iso-2022-jp", "iso2022-jp-2")
    assert is_correct("iso-2022-jp", "iso2022-jp-2004")
    assert is_correct("iso-2022-jp", "iso2022-jp-ext")
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_equivalences.py::test_superset_equivalences_for_renamed_encodings -v`
Expected: FAIL (these superset entries don't exist yet)

**Step 3: Update equivalences**

In `src/chardet/equivalences.py`, update `SUPERSETS`:

```python
SUPERSETS: dict[str, frozenset[str]] = {
    "ascii": frozenset({"utf-8", "windows-1252"}),
    "tis-620": frozenset({"iso-8859-11", "cp874"}),
    "iso-8859-11": frozenset({"cp874"}),
    "gb2312": frozenset({"gb18030"}),
    "gbk": frozenset({"gb18030"}),
    "big5": frozenset({"big5hkscs", "cp950"}),
    "shift_jis": frozenset({"cp932", "shift_jis_2004"}),
    "shift-jisx0213": frozenset({"shift_jis_2004"}),
    "euc-jp": frozenset({"euc-jis-2004"}),
    "euc-jisx0213": frozenset({"euc-jis-2004"}),
    "euc-kr": frozenset({"cp949"}),
    "cp500": frozenset({"cp1140"}),
    # ISO-2022-JP subsets: any branch variant is acceptable
    "iso-2022-jp": frozenset({"iso2022-jp-2", "iso2022-jp-2004", "iso2022-jp-ext"}),
    "iso2022-jp-1": frozenset({"iso2022-jp-2", "iso2022-jp-ext"}),
    "iso2022-jp-3": frozenset({"iso2022-jp-2004"}),
    # ISO/Windows superset pairs
    "iso-8859-1": frozenset({"windows-1252"}),
    "iso-8859-2": frozenset({"windows-1250"}),
    "iso-8859-5": frozenset({"windows-1251"}),
    "iso-8859-6": frozenset({"windows-1256"}),
    "iso-8859-7": frozenset({"windows-1253"}),
    "iso-8859-8": frozenset({"windows-1255"}),
    "iso-8859-9": frozenset({"windows-1254"}),
    "iso-8859-13": frozenset({"windows-1257"}),
}
```

Add a new bidirectional group for the ISO-2022-JP branches (all decode base ISO-2022-JP correctly):

```python
BIDIRECTIONAL_GROUPS: tuple[tuple[str, ...], ...] = (
    ("utf-16", "utf-16-le", "utf-16-be"),
    ("utf-32", "utf-32-le", "utf-32-be"),
    ("iso2022-jp-2", "iso2022-jp-2004", "iso2022-jp-ext"),
)
```

**Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_equivalences.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/equivalences.py tests/test_equivalences.py
git commit -m "feat: update equivalences for flipped supersets and ISO-2022-JP branches"
```

---

### Task 11: CJK gating tests — Update encoding name references

**Files:**
- Modify: `tests/test_cjk_gating.py`

**Step 1: Update `_CJK_ENCODINGS` set**

Change the set to use new primary names and include all three ISO-2022-JP branches:

```python
_CJK_ENCODINGS = frozenset(
    {
        "gb18030",
        "big5hkscs",
        "cp932",
        "cp949",
        "euc-jis-2004",
        "euc-kr",
        "shift_jis_2004",
        "johab",
        "hz-gb-2312",
        "iso2022-jp-2",
        "iso2022-jp-2004",
        "iso2022-jp-ext",
        "iso-2022-kr",
    }
)
```

**Step 2: Update test assertions**

In `test_real_cjk_still_detected`, change:
```python
assert result[0].encoding in {"shift_jis_2004", "cp932"}
```

**Step 3: Run tests**

Run: `uv run python -m pytest tests/test_cjk_gating.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/test_cjk_gating.py
git commit -m "test: update CJK gating tests for renamed encodings"
```

---

### Task 12: Detector test — Update ISO-2022-JP reference

**Files:**
- Modify: `tests/test_detector.py`

**Step 1: Check for hardcoded `"iso-2022-jp"` in assertions**

The test at line 139 feeds ISO-2022-JP escape data. If it asserts the encoding name, update it to expect `"iso2022-jp-2"`.

**Step 2: Run tests**

Run: `uv run python -m pytest tests/test_detector.py -v`
Expected: PASS

**Step 3: Commit (if changes needed)**

```bash
git add tests/test_detector.py
git commit -m "test: update detector test for iso2022-jp-2 rename"
```

---

### Task 13: Training script — Verify ENCODING_LANG_MAP still works

**Files:**
- Verify: `scripts/train.py`

The training script derives `ENCODING_LANG_MAP` from the registry via `enc.name`. After renames, the map keys will automatically use new names (e.g., `big5hkscs` instead of `big5`). Verify this works:

**Step 1: Run a quick check**

Run: `uv run python -c "from scripts.train import ENCODING_LANG_MAP; print(sorted(ENCODING_LANG_MAP.keys())); assert 'big5hkscs' in ENCODING_LANG_MAP; assert 'euc-jis-2004' in ENCODING_LANG_MAP; assert 'shift_jis_2004' in ENCODING_LANG_MAP; assert 'cp1140' in ENCODING_LANG_MAP; print('OK')"`

Expected: prints the sorted keys and `OK`

Note: The training script doesn't need code changes — it auto-derives from the registry. But training with new names would produce model keys like `zh/big5hkscs` which wouldn't match the existing `models.bin` keys. This is fine because:
1. We DON'T retrain here — existing models.bin is kept
2. Task 8 already handles the alias resolution in the model loader
3. Retraining is a separate future task

**Step 2: Commit (no changes expected)**

No commit needed if the script works without modification.

---

### Task 14: Full test suite — Run and fix any remaining failures

**Step 1: Run the full test suite**

Run: `uv run python -m pytest -x`

**Step 2: Fix any failures**

Likely failure points:
- Tests referencing old encoding names in assertions
- The `PREFERRED_SUPERSET` map in `equivalences.py` may need updates if any renamed encoding was a key
- `conftest.py` line 103 has a cp500 reference in skipped tests

For each failure: identify the root cause, update the reference to use the new name, and re-run.

**Step 3: Run again to confirm all pass**

Run: `uv run python -m pytest`
Expected: All tests pass

**Step 4: Commit any remaining fixes**

```bash
git add -u
git commit -m "fix: update remaining encoding name references for full test suite"
```

---

### Task 15: Accuracy tests — Run with EncodingEra.ALL

**Step 1: Run accuracy tests**

Run: `uv run python -m pytest tests/test_accuracy.py -v --tb=short 2>&1 | tail -30`

**Step 2: Check for new failures**

The accuracy tests use `is_correct()` and `is_equivalent_detection()` from equivalences. With the updated SUPERSETS, most cases should pass. If any new failures appear, investigate whether:
- A test expected `"big5"` but we now return `"big5hkscs"` → should be handled by SUPERSETS
- A test expected `"euc-jp"` but we now return `"euc-jis-2004"` → should be handled by SUPERSETS
- A test expected `"iso-2022-jp"` but we now return `"iso2022-jp-2"` → should be handled by SUPERSETS

**Step 3: Fix any remaining equivalence gaps**

Add missing entries to SUPERSETS if needed.

**Step 4: Commit**

```bash
git add -u
git commit -m "fix: ensure accuracy tests pass with renamed encodings"
```

---

### Task 16: Lint and format

**Step 1: Run ruff**

Run: `uv run ruff check . && uv run ruff format --check .`

**Step 2: Fix any issues**

Run: `uv run ruff check --fix . && uv run ruff format .`

**Step 3: Commit**

```bash
git add -u
git commit -m "style: fix lint and formatting"
```
