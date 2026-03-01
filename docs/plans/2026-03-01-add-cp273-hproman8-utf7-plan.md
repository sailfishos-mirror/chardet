# Add cp273, hp-roman8, and UTF-7 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add support for three missing encodings (UTF-7, cp273, hp-roman8) to close the gap with charset-normalizer.

**Architecture:** UTF-7 is detected structurally in the escape pipeline stage (like ISO-2022-JP and HZ-GB-2312). cp273 and hp-roman8 are added to the encoding registry and trained with bigram models for statistical discrimination.

**Tech Stack:** Python 3.10+, pytest, `scripts/train.py` for model training

---

### Task 1: UTF-7 — Write failing tests

**Files:**
- Modify: `tests/test_escape.py`

**Step 1: Add UTF-7 test cases to `tests/test_escape.py`**

Append these tests at the end of the file:

```python
def test_utf7_basic() -> None:
    # "Hello, 世界" encoded as UTF-7
    data = "Hello, 世界".encode("utf-7")
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "utf-7"
    assert result.confidence == 0.95


def test_utf7_shifted_sequence() -> None:
    # UTF-7 with explicit +<Base64>- regions
    data = b"Hello +AGkAbgB0AGUAbgBzAGU-"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "utf-7"


def test_utf7_literal_plus() -> None:
    # +- is the UTF-7 escape for literal '+', not a shifted sequence
    data = b"2+- 2 = 4"
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_plain_ascii_with_plus() -> None:
    # A stray + in ASCII text should not trigger UTF-7 detection
    data = b"C++ is a programming language"
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_empty_shift() -> None:
    # +- followed by nothing is just a literal plus, not UTF-7
    data = b"price: 10+- tax"
    result = detect_escape_encoding(data)
    assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_escape.py -v -k utf7`
Expected: FAIL — `detect_escape_encoding` does not handle UTF-7 yet

---

### Task 2: UTF-7 — Implement detection

**Files:**
- Modify: `src/chardet/pipeline/escape.py`

**Step 1: Add UTF-7 detection to `escape.py`**

Add this helper function after `_has_valid_hz_regions`:

```python
# Base64 character set used in UTF-7 shifted sequences.
_UTF7_BASE64 = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
)


def _has_valid_utf7_sequences(data: bytes) -> bool:
    """Check for valid UTF-7 shifted sequences (+<Base64 chars>-).

    Returns True if the data contains at least one non-empty +...  region
    with valid Base64 characters.  The literal-plus escape ``+-`` is
    excluded.
    """
    start = 0
    while True:
        pos = data.find(ord("+"), start)
        if pos == -1:
            return False
        # +- is a literal plus, skip it
        if pos + 1 < len(data) and data[pos + 1] == ord("-"):
            start = pos + 2
            continue
        # Scan for Base64 content after the +
        end = pos + 1
        while end < len(data) and data[end] in _UTF7_BASE64:
            end += 1
        length = end - (pos + 1)
        if length >= 2:
            return True
        start = end if end > pos + 1 else pos + 1
```

Then add the UTF-7 check at the end of `detect_escape_encoding`, just before the final `return None`:

```python
    # UTF-7: +<Base64>- shifted sequences for non-ASCII characters
    if b"+" in data and _has_valid_utf7_sequences(data):
        return DetectionResult(
            encoding="utf-7",
            confidence=DETERMINISTIC_CONFIDENCE,
            language=None,
        )
```

Also update the early-exit guard at the top of `detect_escape_encoding` to include `+`:

Change:
```python
    if b"\x1b" not in data and b"~" not in data:
        return None
```

To:
```python
    if b"\x1b" not in data and b"~" not in data and b"+" not in data:
        return None
```

Update the docstring of `detect_escape_encoding` from:
```python
    """Detect ISO-2022 and HZ-GB-2312 from escape/tilde sequences.
```
To:
```python
    """Detect ISO-2022, HZ-GB-2312, and UTF-7 from escape/shift sequences.
```

**Step 2: Run UTF-7 tests to verify they pass**

Run: `uv run python -m pytest tests/test_escape.py -v -k utf7`
Expected: PASS

**Step 3: Run all escape tests to verify no regressions**

Run: `uv run python -m pytest tests/test_escape.py -v`
Expected: All PASS

**Step 4: Run full test suite to verify no regressions**

Run: `uv run python -m pytest`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/chardet/pipeline/escape.py tests/test_escape.py
git commit -m "feat: add UTF-7 detection via escape sequence matching"
```

---

### Task 3: cp273 — Write failing test

**Files:**
- Modify: `tests/test_registry.py`

**Step 1: Add cp273 registry test**

Append to `tests/test_registry.py`:

```python
def test_registry_cp273_is_mainframe():
    cp273 = next(e for e in REGISTRY if e.name == "cp273")
    assert EncodingEra.MAINFRAME in cp273.era
    assert cp273.is_multibyte is False
    assert cp273.python_codec == "cp273"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_registry.py::test_registry_cp273_is_mainframe -v`
Expected: FAIL — StopIteration (cp273 not in REGISTRY)

---

### Task 4: cp273 — Add to registry

**Files:**
- Modify: `src/chardet/registry.py`

**Step 1: Add cp273 to registry under MAINFRAME section**

Add after the `cp1026` entry (end of MAINFRAME section):

```python
    EncodingInfo(
        name="cp273",
        aliases=(),
        era=EncodingEra.MAINFRAME,
        is_multibyte=False,
        python_codec="cp273",
    ),
```

**Step 2: Run registry test to verify it passes**

Run: `uv run python -m pytest tests/test_registry.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/chardet/registry.py tests/test_registry.py
git commit -m "feat: add cp273 (EBCDIC German) to encoding registry"
```

---

### Task 5: cp273 — Add to training config and single-language map

**Files:**
- Modify: `scripts/train.py`
- Modify: `src/chardet/models/__init__.py`

**Step 1: Add cp273 to `ENCODING_LANG_MAP` in `scripts/train.py`**

In the EBCDIC section (after the `cp500` entry), add:

```python
    "cp273": ["de"],
```

**Step 2: Add cp273 to `_SINGLE_LANG_MAP` in `src/chardet/models/__init__.py`**

Add in alphabetical order (after the `cp1125` entry):

```python
    "cp273": "de",
```

**Step 3: Commit**

```bash
git add scripts/train.py src/chardet/models/__init__.py
git commit -m "feat: add cp273 to training config and language map"
```

---

### Task 6: hp-roman8 — Write failing test

**Files:**
- Modify: `tests/test_registry.py`

**Step 1: Add hp-roman8 registry test**

Append to `tests/test_registry.py`:

```python
def test_registry_hp_roman8_is_legacy_regional():
    hp = next(e for e in REGISTRY if e.name == "hp-roman8")
    assert EncodingEra.LEGACY_REGIONAL in hp.era
    assert hp.is_multibyte is False
    assert hp.python_codec == "hp-roman8"
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/test_registry.py::test_registry_hp_roman8_is_legacy_regional -v`
Expected: FAIL — StopIteration (hp-roman8 not in REGISTRY)

---

### Task 7: hp-roman8 — Add to registry

**Files:**
- Modify: `src/chardet/registry.py`

**Step 1: Add hp-roman8 to registry under LEGACY_REGIONAL section**

Add after the `ptcp154` entry (end of LEGACY_REGIONAL section):

```python
    EncodingInfo(
        name="hp-roman8",
        aliases=("roman8", "r8", "csHPRoman8"),
        era=EncodingEra.LEGACY_REGIONAL,
        is_multibyte=False,
        python_codec="hp-roman8",
    ),
```

**Step 2: Run registry test to verify it passes**

Run: `uv run python -m pytest tests/test_registry.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/chardet/registry.py tests/test_registry.py
git commit -m "feat: add hp-roman8 to encoding registry"
```

---

### Task 8: hp-roman8 — Add to training config

**Files:**
- Modify: `scripts/train.py`

**Step 1: Add hp-roman8 to `ENCODING_LANG_MAP` in `scripts/train.py`**

Add a new comment and entry near the other Western European legacy entries (after the `mac-iceland` entry or near the end of the Western European section):

```python
    # HP legacy
    "hp-roman8": _WESTERN_EUROPEAN_LANGS,
```

**Step 2: Commit**

```bash
git add scripts/train.py
git commit -m "feat: add hp-roman8 to training config"
```

---

### Task 9: Train models

**Step 1: Retrain models with new encodings**

Run: `uv run python scripts/train.py --encodings cp273 hp-roman8`

This will download CulturaX training data if not cached and generate new bigram models for the two encodings. The models are appended to `src/chardet/models/models.bin`.

Note: If `--encodings` only trains the specified encodings without rewriting the full file, a full retrain may be needed:

Run: `uv run python scripts/train.py`

**Step 2: Verify models loaded**

Run: `uv run python -c "from chardet.models import load_models; m = load_models(); print([k for k in sorted(m) if 'cp273' in k or 'hp-roman8' in k or 'roman8' in k])"`

Expected: List containing `de/cp273` and language/hp-roman8 entries.

**Step 3: Run full test suite**

Run: `uv run python -m pytest`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/chardet/models/models.bin
git commit -m "feat: train bigram models for cp273 and hp-roman8"
```

---

### Task 10: End-to-end detection tests

**Files:**
- Modify: `tests/test_api.py`

**Step 1: Add end-to-end detection tests**

Append to `tests/test_api.py`:

```python
def test_detect_utf7():
    data = "Hello, 世界!".encode("utf-7")
    result = chardet.detect(data)
    assert result["encoding"] == "utf-7"


def test_detect_cp273():
    data = "Grüße aus Deutschland".encode("cp273")
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    assert result["encoding"] is not None
    # Should detect an EBCDIC encoding (cp273 or a close variant)
    assert "cp" in result["encoding"].lower() or "ebcdic" in result["encoding"].lower()


def test_detect_hp_roman8():
    data = "café résumé naïve".encode("hp-roman8")
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    assert result["encoding"] is not None
```

**Step 2: Run the new tests**

Run: `uv run python -m pytest tests/test_api.py -v -k "utf7 or cp273 or hp_roman8"`
Expected: All PASS

**Step 3: Run full test suite**

Run: `uv run python -m pytest`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/test_api.py
git commit -m "test: add end-to-end detection tests for UTF-7, cp273, hp-roman8"
```

---

### Task 11: Update README encoding count

**Files:**
- Modify: `README.md`

**Step 1: Update the supported encoding count in the comparison chart**

The registry now has 83 encodings (81 + cp273 + hp-roman8). UTF-7 is not in the registry (handled by the escape detector) but is still a supported encoding, so the count is 84.

Update the chart row from:
```
| Supported encodings | 81 | 99 |
```
To:
```
| Supported encodings | 84 | 99 |
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update supported encoding count to 84"
```
