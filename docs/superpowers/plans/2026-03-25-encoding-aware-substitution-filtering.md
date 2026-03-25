# Encoding-Aware Substitution Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modify `get_substitutions()` to only substitute characters that the target encoding cannot represent, preserving native byte patterns as training signal.

**Architecture:** Single function change in `scripts/substitutions.py` with an encodability filter applied uniformly to all substitution tables. After the code change, retrain models and measure accuracy impact against the 98.6% baseline.

**Tech Stack:** Python codecs module for encodability checks, existing training pipeline, existing accuracy test suite.

**Spec:** `docs/superpowers/specs/2026-03-25-encoding-aware-substitution-filtering-design.md`

---

### Task 1: Write tests for encoding-aware filtering

**Files:**
- Create: `tests/test_substitutions.py`

- [ ] **Step 1: Write tests for the new filtering behavior**

```python
"""Tests for scripts/substitutions.py encoding-aware filtering."""

from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "scripts")
from substitutions import get_substitutions


class TestEncodingAwareFiltering:
    """get_substitutions only substitutes unencodable characters."""

    def test_smart_quotes_preserved_for_windows_1252(self):
        """Windows-1252 encodes smart quotes — they should NOT be substituted."""
        subs = get_substitutions("windows-1252", ["en"])
        # U+201C LEFT DOUBLE QUOTATION MARK is byte 0x93 in Windows-1252
        assert "\u201c" not in subs
        # U+201D RIGHT DOUBLE QUOTATION MARK is byte 0x94 in Windows-1252
        assert "\u201d" not in subs

    def test_smart_quotes_substituted_for_iso_8859_1(self):
        """ISO-8859-1 cannot encode smart quotes — they SHOULD be substituted."""
        subs = get_substitutions("iso-8859-1", ["en"])
        assert "\u201c" in subs
        assert "\u201d" in subs

    def test_em_dash_preserved_for_windows_1252(self):
        """Windows-1252 encodes em dash (0x97) — should NOT be substituted."""
        subs = get_substitutions("windows-1252", ["en"])
        assert "\u2014" not in subs

    def test_em_dash_substituted_for_iso_8859_1(self):
        """ISO-8859-1 cannot encode em dash — should be substituted."""
        subs = get_substitutions("iso-8859-1", ["en"])
        assert "\u2014" in subs

    def test_nbsp_preserved_for_iso_8859_1(self):
        """ISO-8859-1 encodes NBSP (0xA0) — should NOT be substituted."""
        subs = get_substitutions("iso-8859-1", ["en"])
        assert "\u00a0" not in subs

    def test_zero_width_chars_substituted_for_all(self):
        """Zero-width characters are unencodable in single-byte encodings."""
        for enc in ("windows-1252", "iso-8859-1", "koi8-r"):
            subs = get_substitutions(enc, ["en"])
            assert "\u200b" in subs, f"ZWSP should be substituted for {enc}"

    def test_arabic_comma_preserved_for_cp864(self):
        """CP864 encodes Arabic comma (U+060C) — should NOT be substituted."""
        subs = get_substitutions("cp864", ["ar"])
        assert "\u060c" not in subs

    def test_arabic_comma_substituted_for_cp720(self):
        """CP720 cannot encode Arabic comma — should be substituted."""
        subs = get_substitutions("cp720", ["ar"])
        assert "\u060c" in subs

    def test_cp866_cyrillic_subs_kept(self):
        """CP866 Cyrillic substitutions survive — source chars are not in CP866."""
        subs = get_substitutions("cp866", ["ru"])
        # Ukrainian і (U+0456) → и (U+0438) — і is NOT in CP866
        assert "\u0456" in subs

    def test_invalid_codec_raises(self):
        """Invalid charset_name should raise LookupError, not silently degrade."""
        with pytest.raises(LookupError):
            get_substitutions("not-a-real-encoding", ["en"])

    def test_all_encoding_specific_pairs_succeed(self):
        """Verify get_substitutions runs without error for all encoding/lang pairs."""
        encoding_lang_pairs = [
            ("cp720", ["ar"]),
            ("cp864", ["ar"]),
            ("iso-8859-6", ["ar"]),
            ("cp720", ["fa"]),
            ("iso-8859-6", ["fa"]),
            ("cp1256", ["fa"]),
            ("cp1006", ["ar"]),
            ("cp866", ["ru"]),
            ("iso-8859-2", ["ro"]),
            ("windows-1250", ["ro"]),
        ]
        for enc, langs in encoding_lang_pairs:
            get_substitutions(enc, langs)  # should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run python -m pytest tests/test_substitutions.py -v`
Expected: Several tests FAIL (smart quotes/em dash/NBSP/Arabic comma are currently always substituted).

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_substitutions.py
git commit -m "test: add tests for encoding-aware substitution filtering"
```

---

### Task 2: Implement encoding-aware filtering in `get_substitutions`

**Files:**
- Modify: `scripts/substitutions.py:1-10` (add `import codecs`)
- Modify: `scripts/substitutions.py:355-378` (`get_substitutions` function)

- [ ] **Step 1: Add `codecs` import**

Add `import codecs` to the imports in `scripts/substitutions.py`.

- [ ] **Step 2: Modify `get_substitutions` to filter by encodability**

Replace the function body with:

```python
def get_substitutions(charset_name: str, langs: list[str]) -> dict[str, str]:
    """Build the character substitution table for a given encoding.

    Only includes substitutions for characters the encoding cannot represent.
    Characters the encoding supports natively are left intact so training
    data preserves their actual byte patterns.
    """
    subs = dict(_UNIVERSAL_SUBSTITUTIONS)

    upper = charset_name.upper()
    if upper in ("CP720", "CP864", "ISO-8859-6"):
        subs.update(_ARABIC_SUBSTITUTIONS)
    if "fa" in langs and upper in ("CP720", "ISO-8859-6"):
        subs.update(_FARSI_SUBSTITUTIONS)
    if "fa" in langs and upper == "CP1256":
        subs.update(_CP1256_FARSI_SUBSTITUTIONS)
    if upper in ("CP1006", "CP864"):
        subs.update(_ARABIC_PRESENTATION_FORM_SUBSTITUTIONS)
    if upper == "CP866":
        subs.update(_CP866_SUBSTITUTIONS)
    if "ro" in langs and upper != "ISO-8859-16":
        subs.update(_ROMANIAN_CEDILLA_SUBSTITUTIONS)

    # Validate codec upfront — a bad charset_name is a caller bug
    codecs.lookup(charset_name)

    # Filter: only keep substitutions for unencodable characters.
    # Applies uniformly to all tables — if the encoding can represent a
    # character natively, its actual byte pattern is informative signal.
    filtered = {}
    for char, replacement in subs.items():
        try:
            char.encode(charset_name, errors="strict")
        except UnicodeEncodeError:
            filtered[char] = replacement

    return filtered
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `uv run python -m pytest tests/test_substitutions.py -v`
Expected: All tests PASS.

- [ ] **Step 4: Run the full test suite to check for regressions**

Run: `uv run python -m pytest -n auto tests/test_api.py -x -q`
Expected: All pass (runtime detection code is unchanged).

- [ ] **Step 5: Commit**

```bash
git add scripts/substitutions.py
git commit -m "feat: filter substitutions by encodability in get_substitutions"
```

---

### Task 3: Retrain models and measure accuracy impact

**Files:**
- Modified by training: `src/chardet/models/models.bin`
- Modified by training: `src/chardet/models/confusion.bin`

- [ ] **Step 1: Record the current accuracy baseline**

Run: `uv run python scripts/diagnose_accuracy.py 2>&1 | head -20`
Save the output for comparison.

- [ ] **Step 2: Retrain models**

Run: `uv run python scripts/train.py`
This will take several minutes. The training pipeline calls `get_substitutions`
with the new filtering logic automatically.

- [ ] **Step 3: Run accuracy tests**

Run: `uv run python -m pytest -n auto tests/test_accuracy.py -x -q`
Compare pass/fail count against 2483/2518 baseline.

- [ ] **Step 4: Run detailed accuracy diagnostics**

Run: `uv run python scripts/diagnose_accuracy.py`
Compare output against baseline from Step 1. Look for:
- Encodings that improved (especially Windows-125x vs ISO-8859-x confusion)
- Encodings that regressed
- Overall accuracy change

- [ ] **Step 5: If accuracy dropped, investigate pruning**

If accuracy decreased, check whether the issue is that more high-byte bigrams
are now competing for the 0-255 weight range, causing previously significant
bigrams to be pruned. Compare model sizes (bigram counts) before and after.

If pruning is the issue, try retraining with more samples:
`uv run python scripts/train.py --max-samples 25000`

- [ ] **Step 6: Commit retrained models**

```bash
git add src/chardet/models/models.bin src/chardet/models/confusion.bin
git commit -m "retrain: models with encoding-aware substitution filtering"
```

- [ ] **Step 7: Update known failures if accuracy changed**

If any tests in `_KNOWN_FAILURES` or `_KNOWN_ERA_FILTERED_FAILURES` in
`tests/test_accuracy.py` now pass (or new ones fail), update those sets
accordingly and commit.

```bash
git add tests/test_accuracy.py
git commit -m "test: update known accuracy failures after substitution filtering"
```
