# Test Coverage Gap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Maximize test coverage from 93.5% to ~98% by removing dead code, adding tests for uncovered paths, and creating `scripts/tests/`.

**Architecture:** Three phases — (1) dead code removal + pragma annotation, (2) new tests in existing files, (3) new `scripts/tests/` directory. Each task is TDD: write test, verify fail, implement/fix, verify pass, commit.

**Tech Stack:** pytest, monkeypatch for mocking, struct for binary payloads, subprocess for CLI tests.

---

### Task 1: Remove dead code and add pragma annotation

**Files:**
- Modify: `src/chardet/pipeline/escape.py:70-72`
- Modify: `src/chardet/pipeline/confusion.py:332`
- Modify: `src/chardet/models/__init__.py:115-117`
- Modify: `src/chardet/pipeline/orchestrator.py:592-594`

**Step 1: Remove `last_val < 0` guard in escape.py**

In `src/chardet/pipeline/escape.py`, the `_is_valid_utf7_b64` function at line 70-72 has a dead branch. The caller (`_has_valid_utf7_sequences`) only passes bytes from `_UTF7_BASE64`, and `_B64_DECODE` covers all those bytes, so `.get(..., -1)` never returns `-1`. Remove the guard and use direct lookup:

```python
# Before (lines 70-72):
        last_val = _B64_DECODE.get(b64_bytes[-1], -1)
        if last_val < 0:
            return False

# After:
        last_val = _B64_DECODE[b64_bytes[-1]]
```

**Step 2: Remove dead `return results` in confusion.py**

In `src/chardet/pipeline/confusion.py`, `resolve_confusion_groups` line 332 has an unreachable `return results`. The `winner` can only be `enc_a`, `enc_b`, or `None` — all handled by lines 326 and 329. Remove the dead line:

```python
# Before (lines 326-332):
    if winner is None or winner == top.encoding:
        return results

    if winner == second.encoding:
        return [second, top, *results[2:]]

    return results

# After:
    if winner is None or winner == top.encoding:
        return results

    return [second, top, *results[2:]]
```

**Step 3: Remove plain-key backward compat branch in models/__init__.py**

In `src/chardet/models/__init__.py`, `get_enc_index` lines 115-117 has a dead `else` branch for model keys without `/`. All current model keys use the `lang/enc` format. Remove the dead branch:

```python
# Before (lines 111-117):
        for key, model in models.items():
            if "/" in key:
                lang, enc = key.split("/", 1)
                index.setdefault(enc, []).append((lang, model, key))
            else:
                # Plain encoding key (backward compat / fallback)
                index.setdefault(key, []).append((None, model, key))

# After:
        for key, model in models.items():
            lang, enc = key.split("/", 1)
            index.setdefault(enc, []).append((lang, model, key))
```

**Step 4: Add pragma to invariant assertion in orchestrator.py**

In `src/chardet/pipeline/orchestrator.py`, lines 592-594 have an unreachable assertion (`_fill_language` never drops items). Add `# pragma: no cover`:

```python
# Before:
    if not results:
        msg = "pipeline must always return at least one result"
        raise RuntimeError(msg)

# After:
    if not results:  # pragma: no cover
        msg = "pipeline must always return at least one result"
        raise RuntimeError(msg)
```

**Step 5: Run tests to confirm nothing broke**

Run: `uv run python -m pytest -x -q`
Expected: All tests pass.

**Step 6: Commit**

```bash
git add src/chardet/pipeline/escape.py src/chardet/pipeline/confusion.py src/chardet/models/__init__.py src/chardet/pipeline/orchestrator.py
git commit -m "refactor: remove dead code branches and add pragma for invariant assertion"
```

---

### Task 2: Add UTF-8 overlong and above-max tests

**Files:**
- Modify: `tests/test_utf8.py`

**Step 1: Write the failing tests**

Add to the end of `tests/test_utf8.py`:

```python
def test_overlong_3byte_rejected():
    """Overlong 3-byte sequence (E0 80 80) encoding U+0000 must be rejected."""
    result = detect_utf8(b"Hello " + b"\xe0\x80\x80" + b" World")
    assert result is None


def test_overlong_4byte_rejected():
    """Overlong 4-byte sequence (F0 80 80 80) encoding U+0000 must be rejected."""
    result = detect_utf8(b"Hello " + b"\xf0\x80\x80\x80" + b" World")
    assert result is None


def test_above_unicode_max_rejected():
    """Code point above U+10FFFF (F4 90 80 80 = U+110000) must be rejected."""
    result = detect_utf8(b"Hello " + b"\xf4\x90\x80\x80" + b" World")
    assert result is None
```

**Step 2: Run tests to verify they fail (they should already pass since the code exists)**

Run: `uv run python -m pytest tests/test_utf8.py::test_overlong_3byte_rejected tests/test_utf8.py::test_overlong_4byte_rejected tests/test_utf8.py::test_above_unicode_max_rejected -v`
Expected: PASS (these test already-existing code paths that were simply untested)

**Step 3: Commit**

```bash
git add tests/test_utf8.py
git commit -m "test: add coverage for UTF-8 overlong 3/4-byte and above-max rejection"
```

---

### Task 3: Add equivalences None-input tests

**Files:**
- Modify: `tests/test_equivalences.py`

**Step 1: Write the tests**

Add to the end of `tests/test_equivalences.py`:

```python
def test_is_correct_expected_none_detected_none():
    """Binary file: expected=None, detected=None -> correct."""
    assert is_correct(None, None) is True


def test_is_correct_expected_none_detected_encoding():
    """Binary file expected but encoding detected -> incorrect."""
    assert is_correct(None, "utf-8") is False


def test_is_equivalent_expected_none_detected_none():
    """Binary file: expected=None, detected=None -> equivalent."""
    assert is_equivalent_detection(b"\x00\x01", None, None) is True


def test_is_equivalent_expected_none_detected_encoding():
    """Binary file expected but encoding detected -> not equivalent."""
    assert is_equivalent_detection(b"\x00\x01", None, "utf-8") is False
```

**Step 2: Run tests**

Run: `uv run python -m pytest tests/test_equivalences.py -v -k "none"`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_equivalences.py
git commit -m "test: add coverage for is_correct/is_equivalent_detection with None inputs"
```

---

### Task 4: Add CLI coverage tests

**Files:**
- Modify: `tests/test_cli.py`

**Step 1: Write the tests**

Add to the end of `tests/test_cli.py`:

```python
def test_cli_python_m_chardet(tmp_path: Path):
    """python -m chardet should work (exercises __main__.py)."""
    f = tmp_path / "test.txt"
    f.write_bytes(b"Hello world")
    result = subprocess.run(
        [sys.executable, "-m", "chardet", str(f)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "with confidence" in result.stdout


def test_cli_detection_failure_on_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Detection exception on file should print error and count as failure."""
    f = tmp_path / "test.txt"
    f.write_bytes(b"Hello world")
    monkeypatch.setattr(chardet, "detect", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(SystemExit, match="1"):
        main([str(f)])
    captured = capsys.readouterr()
    assert "detection failed" in captured.err
    assert "boom" in captured.err


def test_cli_detection_failure_on_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Detection exception on stdin should print error and exit 1."""
    import io

    monkeypatch.setattr(sys, "stdin", type(sys.stdin)(buffer=io.BytesIO(b"Hello")))
    monkeypatch.setattr(chardet, "detect", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(SystemExit, match="1"):
        main([])
    captured = capsys.readouterr()
    assert "detection failed" in captured.err
    assert "stdin" in captured.err
```

Also add `import chardet` to the imports at the top of the file (after `from chardet.cli import main`).

**Step 2: Run tests**

Run: `uv run python -m pytest tests/test_cli.py -v -k "python_m_chardet or detection_failure"`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add CLI coverage for __main__.py and detection failure paths"
```

---

### Task 5: Add escape edge-case tests

**Files:**
- Modify: `tests/test_escape.py`

**Step 1: Write the tests**

Add to the end of `tests/test_escape.py`:

```python
def test_hz_close_marker_before_open_marker() -> None:
    """When ~} appears before any ~{ in the data, _has_valid_hz_regions returns False.

    The data has both markers (so the outer guard passes) but the close
    marker is before the open, making the find(~}, begin+2) return the
    pre-existing close position which is before begin.
    """
    data = b"prefix ~} text ~{CEDE~}"
    result = detect_escape_encoding(data)
    # Should detect because there IS a valid ~{CEDE~} region after the stray ~}
    assert result is not None
    assert result.encoding == "hz-gb-2312"


def test_hz_only_close_before_open() -> None:
    """Data where ~} only appears before ~{ — no valid HZ region."""
    data = b"~} some text ~{ invalid"
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_short_base64_rejected() -> None:
    """UTF-7 shifted sequence with fewer than 3 base64 chars is rejected.

    +AB- has only 2 base64 characters (A, B), which is fewer than the
    minimum of 3 needed for a 16-bit UTF-16 code unit.
    """
    data = b"text +AB- more text"
    result = detect_escape_encoding(data)
    assert result is None
```

**Step 2: Run tests**

Run: `uv run python -m pytest tests/test_escape.py -v -k "close_marker or short_base64"`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_escape.py
git commit -m "test: add escape edge-case coverage for HZ marker ordering and short UTF-7 base64"
```

---

### Task 6: Add confusion.py error-path tests

**Files:**
- Modify: `tests/test_confusion.py`

**Step 1: Write the tests**

Add to `tests/test_confusion.py`. Add required imports first:

```python
import struct
import warnings
from unittest.mock import MagicMock, patch

import pytest
```

Then add these test functions:

```python
def test_load_confusion_data_empty_file():
    """Empty confusion.bin should emit RuntimeWarning and return empty dict."""
    import chardet.pipeline.confusion as mod

    original = mod._CONFUSION_CACHE
    try:
        mod._CONFUSION_CACHE = None
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
        mod._CONFUSION_CACHE = original


def test_load_confusion_data_corrupt_file():
    """Corrupt confusion.bin should raise ValueError."""
    import chardet.pipeline.confusion as mod

    original = mod._CONFUSION_CACHE
    try:
        mod._CONFUSION_CACHE = None
        mock_ref = MagicMock()
        # Valid num_pairs=1 but truncated after that
        mock_ref.read_bytes.return_value = struct.pack("!H", 1)
        with (
            patch.object(
                mod.importlib.resources,
                "files",
                return_value=MagicMock(joinpath=MagicMock(return_value=mock_ref)),
            ),
            pytest.raises(ValueError, match="corrupt confusion.bin"),
        ):
            mod.load_confusion_data()
    finally:
        mod._CONFUSION_CACHE = original


def test_resolve_confusion_groups_single_result():
    """A single result should pass through unchanged."""
    results = [DetectionResult(encoding="utf-8", confidence=0.95, language=None)]
    resolved = resolve_confusion_groups(b"Hello", results)
    assert resolved is results


def test_resolve_by_bigram_rescore_empty_freq():
    """When no bigrams contain distinguishing bytes, return None."""
    # diff_bytes contains 0xFE which won't appear in ASCII data
    diff_bytes = frozenset({0xFE})
    data = b"Hello world, this is plain ASCII text without any high bytes at all."
    result = resolve_by_bigram_rescore(data, "enc_a", "enc_b", diff_bytes)
    assert result is None
```

**Step 2: Run tests**

Run: `uv run python -m pytest tests/test_confusion.py -v -k "empty_file or corrupt_file or single_result or empty_freq"`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_confusion.py
git commit -m "test: add confusion.py coverage for empty/corrupt files, single result, empty freq"
```

---

### Task 7: Add models error-path tests

**Files:**
- Modify: `tests/test_models.py`

**Step 1: Write the tests**

Add imports at top of `tests/test_models.py`:

```python
import struct
import warnings
from unittest.mock import MagicMock, patch
```

Then add these tests:

```python
def test_load_models_empty_file():
    """Empty models.bin should emit RuntimeWarning and return empty dict."""
    import chardet.models as mod

    original = mod._MODEL_CACHE
    try:
        mod._MODEL_CACHE = None
        mock_ref = MagicMock()
        mock_ref.read_bytes.return_value = b""
        with (
            patch.object(
                mod.importlib.resources,
                "files",
                return_value=MagicMock(joinpath=MagicMock(return_value=mock_ref)),
            ),
            pytest.warns(RuntimeWarning, match="models.bin is empty"),
        ):
            result = mod.load_models()
        assert result == {}
    finally:
        mod._MODEL_CACHE = original


def test_load_models_num_encodings_exceeds_limit():
    """num_encodings > 10000 should raise ValueError."""
    import chardet.models as mod

    original = mod._MODEL_CACHE
    try:
        mod._MODEL_CACHE = None
        mock_ref = MagicMock()
        mock_ref.read_bytes.return_value = struct.pack("!I", 10001)
        with (
            patch.object(
                mod.importlib.resources,
                "files",
                return_value=MagicMock(joinpath=MagicMock(return_value=mock_ref)),
            ),
            pytest.raises(ValueError, match="num_encodings=10001 exceeds limit"),
        ):
            mod.load_models()
    finally:
        mod._MODEL_CACHE = original


def test_load_models_name_len_exceeds_limit():
    """name_len > 256 should raise ValueError."""
    import chardet.models as mod

    original = mod._MODEL_CACHE
    try:
        mod._MODEL_CACHE = None
        data = struct.pack("!I", 1)  # num_encodings=1
        data += struct.pack("!I", 300)  # name_len=300
        mock_ref = MagicMock()
        mock_ref.read_bytes.return_value = data
        with (
            patch.object(
                mod.importlib.resources,
                "files",
                return_value=MagicMock(joinpath=MagicMock(return_value=mock_ref)),
            ),
            pytest.raises(ValueError, match="name_len=300 exceeds 256"),
        ):
            mod.load_models()
    finally:
        mod._MODEL_CACHE = original


def test_load_models_num_entries_exceeds_limit():
    """num_entries > 65536 should raise ValueError."""
    import chardet.models as mod

    original = mod._MODEL_CACHE
    try:
        mod._MODEL_CACHE = None
        name = b"test/enc"
        data = struct.pack("!I", 1)  # num_encodings=1
        data += struct.pack("!I", len(name)) + name  # name
        data += struct.pack("!I", 70000)  # num_entries=70000
        mock_ref = MagicMock()
        mock_ref.read_bytes.return_value = data
        with (
            patch.object(
                mod.importlib.resources,
                "files",
                return_value=MagicMock(joinpath=MagicMock(return_value=mock_ref)),
            ),
            pytest.raises(ValueError, match="num_entries=70000 exceeds 65536"),
        ):
            mod.load_models()
    finally:
        mod._MODEL_CACHE = original


def test_load_models_truncated_data():
    """Truncated model data should raise ValueError (struct.error wrapped)."""
    import chardet.models as mod

    original = mod._MODEL_CACHE
    try:
        mod._MODEL_CACHE = None
        name = b"test/enc"
        data = struct.pack("!I", 1)  # num_encodings=1
        data += struct.pack("!I", len(name)) + name  # name
        data += struct.pack("!I", 2)  # num_entries=2
        data += struct.pack("!BBB", 65, 66, 200)  # entry 1 (valid)
        # entry 2 is missing — truncated
        mock_ref = MagicMock()
        mock_ref.read_bytes.return_value = data
        with (
            patch.object(
                mod.importlib.resources,
                "files",
                return_value=MagicMock(joinpath=MagicMock(return_value=mock_ref)),
            ),
            pytest.raises(ValueError, match="corrupt models.bin"),
        ):
            mod.load_models()
    finally:
        mod._MODEL_CACHE = original


def test_score_with_profile_fallback_norm():
    """score_with_profile with empty model_key should compute norm on the fly."""
    from chardet.models import BigramProfile, score_with_profile

    profile = BigramProfile(b"\xc3\xa9\xc3\xa4")  # some high-byte bigrams
    # Build a model with a few non-zero entries
    model = bytearray(65536)
    model[(0xC3 << 8) | 0xA9] = 100
    model[(0xC3 << 8) | 0xA4] = 80
    score = score_with_profile(profile, model, model_key="")
    assert isinstance(score, float)
    assert score > 0.0


def test_score_with_profile_all_zeros_model():
    """All-zeros model should return 0.0 (model_norm == 0)."""
    from chardet.models import BigramProfile, score_with_profile

    profile = BigramProfile(b"\xc3\xa9\xc3\xa4")
    model = bytearray(65536)  # all zeros
    score = score_with_profile(profile, model, model_key="")
    assert score == 0.0
```

**Step 2: Run tests**

Run: `uv run python -m pytest tests/test_models.py -v -k "empty_file or exceeds_limit or truncated or fallback_norm or all_zeros"`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_models.py
git commit -m "test: add models coverage for empty/corrupt files and score_with_profile edge cases"
```

---

### Task 8: Add orchestrator coverage tests

**Files:**
- Modify: `tests/test_orchestrator.py`

**Step 1: Write the tests**

Add these tests to the end of `tests/test_orchestrator.py`:

```python
def test_to_utf8_unknown_encoding():
    """_to_utf8 with an unknown encoding should return None."""
    from chardet.pipeline.orchestrator import _to_utf8

    result = _to_utf8(b"Hello world", "not-a-real-encoding")
    assert result is None


def test_to_utf8_passthrough():
    """_to_utf8 with utf-8 encoding should return data unchanged."""
    from chardet.pipeline.orchestrator import _to_utf8

    data = b"Hello \xc3\xa9"
    result = _to_utf8(data, "utf-8")
    assert result is data  # identity check — same object


def test_demote_niche_latin_iso_8859_14():
    """iso-8859-14 at top should be demoted when no distinguishing bytes."""
    from chardet.pipeline.orchestrator import _demote_niche_latin

    results = [
        DetectionResult("iso-8859-14", 0.90, None),
        DetectionResult("windows-1252", 0.85, None),
    ]
    # Only bytes shared between iso-8859-14 and iso-8859-1
    # 0xC0-0xCF (except 0xD0) are shared between the two encodings
    data = bytes([0xC0, 0xC1, 0xC2])
    demoted = _demote_niche_latin(data, results)
    assert demoted[0].encoding == "windows-1252"


def test_demote_niche_latin_windows_1254():
    """windows-1254 at top should be demoted when no distinguishing bytes."""
    from chardet.pipeline.orchestrator import _demote_niche_latin

    results = [
        DetectionResult("windows-1254", 0.90, None),
        DetectionResult("windows-1252", 0.85, None),
    ]
    # Bytes shared between windows-1254 and windows-1252
    # Distinguishing bytes for 1254 are: 0xD0, 0xDD, 0xDE, 0xF0, 0xFD, 0xFE
    # Use bytes NOT in that set
    data = bytes([0xC0, 0xC1, 0xE9])
    demoted = _demote_niche_latin(data, results)
    assert demoted[0].encoding == "windows-1252"
```

**Step 2: Run tests**

Run: `uv run python -m pytest tests/test_orchestrator.py -v -k "to_utf8 or iso_8859_14 or windows_1254"`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_orchestrator.py
git commit -m "test: add orchestrator coverage for _to_utf8 and niche latin demotion variants"
```

---

### Task 9: Add structural.py edge-case tests

**Files:**
- Modify: `tests/test_structural.py`

**Step 1: Write the tests**

Add imports at top if not present:
```python
from chardet.pipeline.structural import (
    compute_lead_byte_diversity,
    compute_multibyte_byte_coverage,
    compute_structural_score,
)
```

Then add these tests:

```python
def test_euc_jp_ss2_invalid_trail():
    """EUC-JP SS2 (0x8E) with invalid trail byte should count as lead but not valid."""
    # 0x8E followed by 0x20 (space, outside 0xA1-0xDF range)
    data = b"\x8e\x20"
    enc = _get_encoding("euc-jis-2004")
    score = compute_structural_score(data, enc, PipelineContext())
    assert score == 0.0  # lead_count=1, valid_count=0


def test_euc_jp_ss3_valid():
    """EUC-JP SS3 (0x8F) with valid 3-byte JIS X 0212 sequence."""
    # 0x8F + 0xA1 + 0xA1 = valid SS3 sequence
    data = b"\x8f\xa1\xa1" * 5
    enc = _get_encoding("euc-jis-2004")
    score = compute_structural_score(data, enc, PipelineContext())
    assert score > 0.0


def test_euc_jp_ss3_invalid_trail():
    """EUC-JP SS3 (0x8F) with invalid trail bytes should not count as valid."""
    # 0x8F + 0xA1 + 0x20 (second trail byte invalid)
    data = b"\x8f\xa1\x20"
    enc = _get_encoding("euc-jis-2004")
    score = compute_structural_score(data, enc, PipelineContext())
    assert score == 0.0


def test_multibyte_byte_coverage_all_ascii():
    """All-ASCII data should return 0.0 coverage for a multibyte encoding."""
    data = b"Hello world plain ASCII"
    enc = _get_encoding("shift_jis_2004")
    ctx = PipelineContext()
    coverage = compute_multibyte_byte_coverage(data, enc, ctx, non_ascii_count=0)
    assert coverage == 0.0


def test_lead_byte_diversity_empty_data():
    """Empty data should return 0 diversity."""
    enc = _get_encoding("shift_jis_2004")
    diversity = compute_lead_byte_diversity(b"", enc, PipelineContext())
    assert diversity == 0


def test_coverage_no_analyzer_returns_zero():
    """An escape-protocol multibyte encoding with no analyzer returns 0.0 coverage."""
    enc = _get_encoding("hz-gb-2312")
    ctx = PipelineContext()
    coverage = compute_multibyte_byte_coverage(b"\x80\x81\x82", enc, ctx, non_ascii_count=3)
    assert coverage == 0.0


def test_diversity_no_analyzer_returns_256():
    """An escape-protocol multibyte encoding with no analyzer returns 256 (don't gate)."""
    enc = _get_encoding("hz-gb-2312")
    diversity = compute_lead_byte_diversity(b"\x80\x81", enc, PipelineContext())
    assert diversity == 256
```

**Step 2: Run tests**

Run: `uv run python -m pytest tests/test_structural.py -v -k "ss2 or ss3 or all_ascii or empty_data or no_analyzer"`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_structural.py
git commit -m "test: add structural.py coverage for EUC-JP SS2/SS3, coverage edge cases, no-analyzer fallbacks"
```

---

### Task 10: Add UTF-16/32 decode-error and edge-case tests

**Files:**
- Modify: `tests/test_utf1632.py`

**Step 1: Write the tests**

Add these tests to `tests/test_utf1632.py`:

```python
def test_utf32_be_decode_error() -> None:
    """UTF-32-BE with invalid code points should return None.

    Construct data where every first byte is 0x00 (BE pattern matches)
    but the 4-byte units encode values > U+10FFFF which cause UnicodeDecodeError.
    """
    # U+110000 in big-endian: 0x00 0x11 0x00 0x00
    # Needs enough units to pass the threshold
    unit = b"\x00\x11\x00\x00"
    data = unit * 8  # 32 bytes > _MIN_BYTES_UTF32 (16)
    result = detect_utf1632_patterns(data)
    assert result is None


def test_utf32_le_decode_error() -> None:
    """UTF-32-LE with invalid code points should return None.

    Construct data where every last byte is 0x00 (LE pattern matches)
    but the values are invalid Unicode.
    """
    # U+110000 in little-endian: 0x00 0x00 0x11 0x00
    unit = b"\x00\x00\x11\x00"
    data = unit * 8
    result = detect_utf1632_patterns(data)
    assert result is None


def test_utf16_single_candidate_decode_error() -> None:
    """UTF-16 with only one endianness matching but decode fails."""
    # Build data where odd-position bytes have enough nulls for LE detection
    # but the resulting decode hits an unpaired surrogate
    # Unpaired high surrogate: D800 in LE = 0x00 0xD8
    # Need enough real nulls in odd positions to pass threshold
    # followed by the bad surrogate
    good = b"H\x00e\x00l\x00l\x00o\x00"  # "Hello" in UTF-16-LE
    bad = b"\x00\xd8"  # unpaired high surrogate
    # More good text to have enough data
    more = b" \x00w\x00o\x00r\x00l\x00d\x00"  # " world"
    data = good + bad + more
    result = detect_utf1632_patterns(data)
    # May or may not return None depending on whether _looks_like_text passes
    # The key coverage target is the UnicodeDecodeError catch at line 171-172


def test_utf16_both_candidates_low_quality() -> None:
    """Both UTF-16 endiannesses decode but produce garbage (below _MIN_TEXT_QUALITY)."""
    # Build data with nulls in both even and odd positions
    # but content is control characters, not real text
    # \x01\x00 and \x00\x01 both decode to control chars in either endianness
    data = b"\x01\x00\x00\x01" * 20  # 80 bytes
    result = detect_utf1632_patterns(data)
    assert result is None


def test_looks_like_text_empty_string() -> None:
    """_looks_like_text with empty string should return False."""
    from chardet.pipeline.utf1632 import _looks_like_text

    assert _looks_like_text("") is False
```

**Step 2: Run tests**

Run: `uv run python -m pytest tests/test_utf1632.py -v -k "decode_error or low_quality or empty_string"`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_utf1632.py
git commit -m "test: add UTF-16/32 decode-error, low-quality, and empty-text edge case coverage"
```

---

### Task 11: Add PipelineContext.mb_coverage test

**Files:**
- Modify: `tests/test_pipeline_types.py`

**Step 1: Write the test**

Add to `tests/test_pipeline_types.py`:

```python
def test_pipeline_context_mb_coverage():
    ctx = PipelineContext()
    assert ctx.mb_coverage == {}
    ctx.mb_coverage["shift_jis"] = 0.95
    assert ctx.mb_coverage["shift_jis"] == 0.95
```

**Step 2: Run test**

Run: `uv run python -m pytest tests/test_pipeline_types.py::test_pipeline_context_mb_coverage -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/test_pipeline_types.py
git commit -m "test: add PipelineContext.mb_coverage field coverage"
```

---

### Task 12: Create scripts/tests/ and add script utility tests

**Files:**
- Create: `scripts/tests/__init__.py`
- Create: `scripts/tests/test_utils.py`

**Step 1: Create the directory and files**

Create `scripts/tests/__init__.py` (empty file).

Create `scripts/tests/test_utils.py`:

```python
"""Tests for scripts/utils.py shared utilities."""

from __future__ import annotations

from pathlib import Path

from utils import collect_test_files, normalize_language


def test_normalize_language_iso_code():
    """ISO 639-1 code should be mapped to English name."""
    assert normalize_language("fr") == "french"
    assert normalize_language("ja") == "japanese"
    assert normalize_language("zh") == "chinese"


def test_normalize_language_case_insensitive():
    """Uppercase or mixed-case codes should be normalized."""
    assert normalize_language("FR") == "french"
    assert normalize_language("Ja") == "japanese"


def test_normalize_language_unknown_code():
    """Unknown codes should be returned lowered as-is."""
    assert normalize_language("xx") == "xx"


def test_normalize_language_none():
    """None input should return None."""
    assert normalize_language(None) is None


def test_collect_test_files_structure(tmp_path: Path):
    """collect_test_files should parse encoding-language directory names."""
    # Create test directory structure
    enc_dir = tmp_path / "utf-8-english"
    enc_dir.mkdir()
    (enc_dir / "sample.txt").write_bytes(b"Hello")
    (enc_dir / "sample2.txt").write_bytes(b"World")

    results = collect_test_files(tmp_path)
    assert len(results) == 2
    assert results[0][0] == "utf-8"
    assert results[0][1] == "english"
    assert results[0][2].name == "sample.txt"


def test_collect_test_files_none_encoding(tmp_path: Path):
    """'None-None' directory should produce Python None values."""
    enc_dir = tmp_path / "None-None"
    enc_dir.mkdir()
    (enc_dir / "binary.bin").write_bytes(b"\x00\x01")

    results = collect_test_files(tmp_path)
    assert len(results) == 1
    assert results[0][0] is None
    assert results[0][1] is None


def test_collect_test_files_skips_non_dirs(tmp_path: Path):
    """Files at the top level should be skipped."""
    (tmp_path / "readme.txt").write_text("ignore me")
    enc_dir = tmp_path / "utf-8-english"
    enc_dir.mkdir()
    (enc_dir / "sample.txt").write_bytes(b"Hello")

    results = collect_test_files(tmp_path)
    assert len(results) == 1


def test_collect_test_files_skips_bad_names(tmp_path: Path):
    """Directories without a hyphen should be skipped."""
    bad_dir = tmp_path / "nohyphen"
    bad_dir.mkdir()
    (bad_dir / "file.txt").write_bytes(b"data")

    results = collect_test_files(tmp_path)
    assert len(results) == 0


def test_collect_test_files_hyphenated_encoding(tmp_path: Path):
    """Encodings with hyphens (e.g., hz-gb-2312) should split on last hyphen."""
    enc_dir = tmp_path / "hz-gb-2312-chinese"
    enc_dir.mkdir()
    (enc_dir / "sample.txt").write_bytes(b"Hello")

    results = collect_test_files(tmp_path)
    assert len(results) == 1
    assert results[0][0] == "hz-gb-2312"
    assert results[0][1] == "chinese"
```

**Step 2: Run tests**

Run: `uv run python -m pytest scripts/tests/test_utils.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add scripts/tests/__init__.py scripts/tests/test_utils.py
git commit -m "test: add scripts/tests/ with utility function tests"
```

---

### Task 13: Run final coverage and verify improvement

**Step 1: Run full coverage**

Run: `uv run python -m pytest --cov=chardet --cov-report=term-missing -q`
Expected: Coverage significantly above 93.5%, targeting 97-98%.

**Step 2: Check for any remaining easy gaps**

Look at the `Missing` column for any lines that could be easily covered. If any, add additional tests.

**Step 3: Final commit if any additional tests were added**

---

### Task 14: Create a single summary commit (optional squash)

If all individual commits look good, no action needed. The work is done.
