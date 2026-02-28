# Confusion Group Resolution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve detection accuracy by auto-computing distinguishing byte maps for similar single-byte encodings and using them to resolve statistical scoring ties.

**Architecture:** A new pipeline stage after statistical scoring resolves confusion between similar encodings. Confusion group data is computed during training, serialized as a separate binary file (`confusion.bin`), and loaded alongside bigram models. Three resolution strategies are implemented behind a flag for experimentation.

**Tech Stack:** Python 3.10+, struct for binary serialization, unicodedata for Unicode category lookup.

---

### Task 1: Confusion Group Computation Module

**Files:**
- Create: `src/chardet/pipeline/confusion.py`
- Test: `tests/test_confusion.py`

**Step 1: Write the failing test for confusion group computation**

```python
# tests/test_confusion.py
"""Tests for confusion group computation and resolution."""

from __future__ import annotations

from chardet.pipeline.confusion import compute_confusion_groups


def test_compute_confusion_groups_finds_ebcdic():
    """EBCDIC encodings (cp037, cp500) should be in the same confusion group."""
    groups = compute_confusion_groups(threshold=0.80)
    # Find the group containing cp037
    cp037_group = None
    for group in groups:
        if "cp037" in group:
            cp037_group = group
            break
    assert cp037_group is not None, "cp037 should be in a confusion group"
    assert "cp500" in cp037_group, "cp500 should be in the same group as cp037"


def test_compute_confusion_groups_finds_dos():
    """DOS encodings cp437 and cp865 differ by only 3 bytes — same group."""
    groups = compute_confusion_groups(threshold=0.80)
    cp437_group = None
    for group in groups:
        if "cp437" in group:
            cp437_group = group
            break
    assert cp437_group is not None
    assert "cp865" in cp437_group


def test_unrelated_encodings_not_grouped():
    """Unrelated encodings should not be in the same group."""
    groups = compute_confusion_groups(threshold=0.80)
    for group in groups:
        # KOI8-R (Cyrillic) should never be grouped with cp437 (DOS Latin)
        assert not ("koi8-r" in group and "cp437" in group)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_confusion.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'chardet.pipeline.confusion'`

**Step 3: Write minimal implementation of `compute_confusion_groups`**

```python
# src/chardet/pipeline/confusion.py
"""Confusion group computation and resolution for similar single-byte encodings.

Encodings that share >80% of their byte-to-Unicode mappings are grouped together.
Within a group, distinguishing bytes (positions where encodings differ) are used
to resolve statistical scoring ties.
"""

from __future__ import annotations

import codecs
import unicodedata

from chardet.registry import REGISTRY


def _decode_byte_table(codec_name: str) -> list[str | None]:
    """Decode all 256 byte values through a codec, returning Unicode chars.

    Returns a list of 256 entries. Each entry is the decoded character,
    or None if the byte is not decodable.
    """
    table: list[str | None] = []
    for b in range(256):
        try:
            table.append(bytes([b]).decode(codec_name))
        except (UnicodeDecodeError, LookupError):
            table.append(None)
    return table


def _compute_pairwise_similarity(
    table_a: list[str | None],
    table_b: list[str | None],
) -> tuple[float, frozenset[int]]:
    """Compute similarity between two byte tables.

    Returns (similarity_ratio, distinguishing_bytes) where similarity is
    the fraction of byte positions that decode to the same character.
    """
    same = 0
    diff_bytes: list[int] = []
    for b in range(256):
        if table_a[b] == table_b[b]:
            same += 1
        else:
            diff_bytes.append(b)
    return same / 256, frozenset(diff_bytes)


def compute_confusion_groups(
    threshold: float = 0.80,
) -> list[frozenset[str]]:
    """Compute confusion groups from the encoding registry.

    Returns a list of frozensets, each containing encoding names that
    share more than `threshold` fraction of their byte mappings.
    Only single-byte encodings are considered.
    """
    # Collect single-byte encodings with valid codecs
    single_byte = []
    for enc in REGISTRY:
        if enc.is_multibyte:
            continue
        try:
            codecs.lookup(enc.python_codec)
            single_byte.append(enc)
        except LookupError:
            continue

    # Compute byte tables
    tables: dict[str, list[str | None]] = {}
    for enc in single_byte:
        tables[enc.name] = _decode_byte_table(enc.python_codec)

    # Build adjacency: which encodings are similar
    adjacency: dict[str, set[str]] = {enc.name: set() for enc in single_byte}
    names = [enc.name for enc in single_byte]

    for i, name_a in enumerate(names):
        for name_b in names[i + 1 :]:
            sim, _ = _compute_pairwise_similarity(tables[name_a], tables[name_b])
            if sim >= threshold:
                adjacency[name_a].add(name_b)
                adjacency[name_b].add(name_a)

    # Transitive closure via BFS to form groups
    visited: set[str] = set()
    groups: list[frozenset[str]] = []
    for name in names:
        if name in visited or not adjacency[name]:
            continue
        # BFS
        group: set[str] = set()
        queue = [name]
        while queue:
            current = queue.pop()
            if current in visited:
                continue
            visited.add(current)
            group.add(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    queue.append(neighbor)
        if len(group) > 1:
            groups.append(frozenset(group))

    return groups
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_confusion.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/pipeline/confusion.py tests/test_confusion.py
git commit -m "feat: add confusion group computation for similar encodings"
```

---

### Task 2: Distinguishing Byte Map and Unicode Category Table

**Files:**
- Modify: `src/chardet/pipeline/confusion.py`
- Modify: `tests/test_confusion.py`

**Step 1: Write the failing test for distinguishing byte maps**

```python
# Add to tests/test_confusion.py

from chardet.pipeline.confusion import compute_distinguishing_maps


def test_distinguishing_map_cp037_cp500():
    """cp037 and cp500 should have exactly 7 distinguishing bytes."""
    maps = compute_distinguishing_maps(threshold=0.80)
    pair_key = ("cp037", "cp500") if ("cp037", "cp500") in maps else ("cp500", "cp037")
    assert pair_key in maps
    diff_bytes, categories = maps[pair_key]
    assert len(diff_bytes) == 7


def test_distinguishing_map_has_categories():
    """Each distinguishing byte should have Unicode category info."""
    maps = compute_distinguishing_maps(threshold=0.80)
    for (enc_a, enc_b), (diff_bytes, categories) in maps.items():
        for byte_val in diff_bytes:
            assert byte_val in categories
            cat_a, cat_b = categories[byte_val]
            # Categories should be 2-char Unicode general category strings
            assert len(cat_a) == 2
            assert len(cat_b) == 2
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_confusion.py::test_distinguishing_map_cp037_cp500 tests/test_confusion.py::test_distinguishing_map_has_categories -v`
Expected: FAIL with `ImportError: cannot import name 'compute_distinguishing_maps'`

**Step 3: Implement `compute_distinguishing_maps`**

Add to `src/chardet/pipeline/confusion.py`:

```python
# Type alias for the distinguishing map structure:
# Maps (enc_a, enc_b) -> (distinguishing_byte_set, {byte_val: (cat_a, cat_b)})
DistinguishingMaps = dict[
    tuple[str, str],
    tuple[frozenset[int], dict[int, tuple[str, str]]],
]


def compute_distinguishing_maps(
    threshold: float = 0.80,
) -> DistinguishingMaps:
    """Compute distinguishing byte maps and Unicode categories for all confusion pairs.

    Returns a dict mapping (enc_a, enc_b) -> (diff_bytes, categories) where:
    - diff_bytes: frozenset of byte values that decode differently
    - categories: {byte_val: (cat_a, cat_b)} Unicode general categories
    """
    # Collect single-byte encodings with valid codecs
    single_byte = []
    for enc in REGISTRY:
        if enc.is_multibyte:
            continue
        try:
            codecs.lookup(enc.python_codec)
            single_byte.append(enc)
        except LookupError:
            continue

    # Compute byte tables
    tables: dict[str, list[str | None]] = {}
    for enc in single_byte:
        tables[enc.name] = _decode_byte_table(enc.python_codec)

    names = [enc.name for enc in single_byte]
    result: DistinguishingMaps = {}

    for i, name_a in enumerate(names):
        for name_b in names[i + 1 :]:
            sim, diff_bytes = _compute_pairwise_similarity(
                tables[name_a], tables[name_b]
            )
            if sim < threshold:
                continue
            # Build category map for distinguishing bytes
            categories: dict[int, tuple[str, str]] = {}
            for b in diff_bytes:
                char_a = tables[name_a][b]
                char_b = tables[name_b][b]
                cat_a = unicodedata.category(char_a) if char_a else "Cn"
                cat_b = unicodedata.category(char_b) if char_b else "Cn"
                categories[b] = (cat_a, cat_b)
            result[(name_a, name_b)] = (diff_bytes, categories)

    return result
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_confusion.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/pipeline/confusion.py tests/test_confusion.py
git commit -m "feat: add distinguishing byte maps with Unicode categories"
```

---

### Task 3: Binary Serialization and Deserialization

**Files:**
- Modify: `src/chardet/pipeline/confusion.py`
- Modify: `tests/test_confusion.py`

**Step 1: Write the failing test for round-trip serialization**

```python
# Add to tests/test_confusion.py
import tempfile
from pathlib import Path

from chardet.pipeline.confusion import (
    compute_distinguishing_maps,
    deserialize_confusion_data,
    serialize_confusion_data,
)


def test_serialize_deserialize_roundtrip():
    """Serialization and deserialization should preserve all data."""
    maps = compute_distinguishing_maps(threshold=0.80)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = Path(f.name)
    try:
        serialize_confusion_data(maps, str(path))
        loaded = deserialize_confusion_data(str(path))
        assert len(loaded) == len(maps)
        for key in maps:
            # Key order may be different
            assert key in loaded or (key[1], key[0]) in loaded
    finally:
        path.unlink(missing_ok=True)


def test_serialized_file_is_small():
    """Confusion data should be <10KB."""
    maps = compute_distinguishing_maps(threshold=0.80)
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        path = Path(f.name)
    try:
        serialize_confusion_data(maps, str(path))
        assert path.stat().st_size < 10_000
    finally:
        path.unlink(missing_ok=True)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_confusion.py::test_serialize_deserialize_roundtrip tests/test_confusion.py::test_serialized_file_is_small -v`
Expected: FAIL with `ImportError`

**Step 3: Implement serialization and deserialization**

Add to `src/chardet/pipeline/confusion.py`:

```python
import os
import struct

# Unicode general category -> uint8 encoding for struct serialization
_CATEGORY_TO_INT: dict[str, int] = {
    "Lu": 0, "Ll": 1, "Lt": 2, "Lm": 3, "Lo": 4,   # Letters
    "Mn": 5, "Mc": 6, "Me": 7,                        # Marks
    "Nd": 8, "Nl": 9, "No": 10,                       # Numbers
    "Pc": 11, "Pd": 12, "Ps": 13, "Pe": 14,           # Punctuation
    "Pi": 15, "Pf": 16, "Po": 17,
    "Sm": 18, "Sc": 19, "Sk": 20, "So": 21,           # Symbols
    "Zs": 22, "Zl": 23, "Zp": 24,                     # Separators
    "Cc": 25, "Cf": 26, "Cs": 27, "Co": 28, "Cn": 29, # Other
}
_INT_TO_CATEGORY: dict[int, str] = {v: k for k, v in _CATEGORY_TO_INT.items()}


def serialize_confusion_data(maps: DistinguishingMaps, output_path: str) -> int:
    """Serialize confusion group data to binary format.

    Format:
      uint16: number_of_pairs
      Per pair:
        uint8:  name_a_length
        bytes:  name_a (UTF-8)
        uint8:  name_b_length
        bytes:  name_b (UTF-8)
        uint8:  num_distinguishing_bytes
        Per distinguishing byte:
          uint8:  byte_value
          uint8:  cat_a (enum)
          uint8:  cat_b (enum)

    Returns file size in bytes.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(struct.pack("!H", len(maps)))
        for (name_a, name_b), (diff_bytes, categories) in sorted(maps.items()):
            a_bytes = name_a.encode("utf-8")
            b_bytes = name_b.encode("utf-8")
            f.write(struct.pack("!B", len(a_bytes)))
            f.write(a_bytes)
            f.write(struct.pack("!B", len(b_bytes)))
            f.write(b_bytes)
            sorted_diffs = sorted(diff_bytes)
            f.write(struct.pack("!B", len(sorted_diffs)))
            for bv in sorted_diffs:
                cat_a, cat_b = categories[bv]
                f.write(struct.pack(
                    "!BBB",
                    bv,
                    _CATEGORY_TO_INT.get(cat_a, 29),
                    _CATEGORY_TO_INT.get(cat_b, 29),
                ))
    return os.path.getsize(output_path)


def deserialize_confusion_data(input_path: str) -> DistinguishingMaps:
    """Load confusion group data from binary format."""
    with open(input_path, "rb") as f:
        data = f.read()

    result: DistinguishingMaps = {}
    offset = 0
    (num_pairs,) = struct.unpack_from("!H", data, offset)
    offset += 2

    for _ in range(num_pairs):
        (name_a_len,) = struct.unpack_from("!B", data, offset)
        offset += 1
        name_a = data[offset : offset + name_a_len].decode("utf-8")
        offset += name_a_len

        (name_b_len,) = struct.unpack_from("!B", data, offset)
        offset += 1
        name_b = data[offset : offset + name_b_len].decode("utf-8")
        offset += name_b_len

        (num_diffs,) = struct.unpack_from("!B", data, offset)
        offset += 1

        diff_bytes: list[int] = []
        categories: dict[int, tuple[str, str]] = {}
        for _ in range(num_diffs):
            bv, cat_a_int, cat_b_int = struct.unpack_from("!BBB", data, offset)
            offset += 3
            diff_bytes.append(bv)
            categories[bv] = (
                _INT_TO_CATEGORY.get(cat_a_int, "Cn"),
                _INT_TO_CATEGORY.get(cat_b_int, "Cn"),
            )
        result[(name_a, name_b)] = (frozenset(diff_bytes), categories)

    return result
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_confusion.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/pipeline/confusion.py tests/test_confusion.py
git commit -m "feat: add binary serialization for confusion group data"
```

---

### Task 4: Integrate into Training Script

**Files:**
- Modify: `scripts/train.py`
- Modify: `tests/test_confusion.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_confusion.py
def test_confusion_bin_exists_after_import():
    """The confusion.bin file should exist in the models package."""
    import importlib.resources

    ref = importlib.resources.files("chardet.models").joinpath("confusion.bin")
    # After training, this file should exist
    # For now, just verify we can construct the path
    assert ref is not None
```

**Step 2: Run test to verify it passes (this is a basic sanity check)**

Run: `uv run pytest tests/test_confusion.py::test_confusion_bin_exists_after_import -v`
Expected: PASS (just checks path construction)

**Step 3: Add confusion data generation to `scripts/train.py`**

Add after the model serialization section (after `serialize_models` call), before the metadata write:

```python
# Add import at top of train.py:
from chardet.pipeline.confusion import (
    compute_distinguishing_maps,
    serialize_confusion_data,
)

# Add after serialize_models call in main():
print("=== Computing confusion groups ===")
confusion_maps = compute_distinguishing_maps(threshold=0.80)
confusion_path = os.path.join(os.path.dirname(args.output), "confusion.bin")
confusion_size = serialize_confusion_data(confusion_maps, confusion_path)
print(f"Confusion groups: {len(confusion_maps)} pairs")
print(f"Confusion data:   {confusion_size:,} bytes ({confusion_size / 1024:.1f} KB)")
```

**Step 4: Run the training script to generate confusion.bin**

Run: `uv run python scripts/train.py --encodings cp037 --max-samples 10`

This runs a minimal training to exercise the new code path. Verify that `src/chardet/models/confusion.bin` is created.

**Step 5: Commit**

```bash
git add scripts/train.py src/chardet/models/confusion.bin
git commit -m "feat: generate confusion.bin during model training"
```

---

### Task 5: Load Confusion Data at Runtime

**Files:**
- Modify: `src/chardet/pipeline/confusion.py`
- Modify: `tests/test_confusion.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_confusion.py
from chardet.pipeline.confusion import load_confusion_data


def test_load_confusion_data():
    """Loading confusion data from the bundled file should return valid maps."""
    maps = load_confusion_data()
    assert len(maps) > 0
    # Should contain EBCDIC pair
    found_ebcdic = any(
        ("cp037" in key[0] and "cp500" in key[1])
        or ("cp500" in key[0] and "cp037" in key[1])
        for key in maps
    )
    assert found_ebcdic
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_confusion.py::test_load_confusion_data -v`
Expected: FAIL with `ImportError`

**Step 3: Implement `load_confusion_data`**

Add to `src/chardet/pipeline/confusion.py`:

```python
import importlib.resources

_CONFUSION_CACHE: DistinguishingMaps | None = None


def load_confusion_data() -> DistinguishingMaps:
    """Load confusion group data from the bundled confusion.bin file.

    Data is loaded lazily on first call and cached globally.
    """
    global _CONFUSION_CACHE  # noqa: PLW0603
    if _CONFUSION_CACHE is not None:
        return _CONFUSION_CACHE

    ref = importlib.resources.files("chardet.models").joinpath("confusion.bin")
    data = ref.read_bytes()
    if not data:
        _CONFUSION_CACHE = {}
        return _CONFUSION_CACHE

    _CONFUSION_CACHE = deserialize_confusion_data_from_bytes(data)
    return _CONFUSION_CACHE
```

Also add a `deserialize_confusion_data_from_bytes` variant that takes `bytes` instead of a file path, to avoid needing to write to a temp file when loading from package resources. The existing `deserialize_confusion_data` can call this internally.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_confusion.py -v`
Expected: PASS (requires `confusion.bin` to have been generated in Task 4)

**Step 5: Commit**

```bash
git add src/chardet/pipeline/confusion.py tests/test_confusion.py
git commit -m "feat: add lazy loading of confusion.bin at runtime"
```

---

### Task 6: Resolution Strategies — Unicode Category Voting

**Files:**
- Modify: `src/chardet/pipeline/confusion.py`
- Modify: `tests/test_confusion.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_confusion.py
from chardet.pipeline.confusion import resolve_by_category_voting


def test_category_voting_prefers_letter_over_symbol():
    """When one encoding maps a byte to a letter and another to a symbol,
    the letter interpretation should win."""
    # Mock data: byte 0xD5 appears in input
    # In a hypothetical pair: enc_a maps it to a letter (Ll), enc_b to a symbol (So)
    diff_bytes = frozenset({0xD5})
    categories = {0xD5: ("Ll", "So")}
    data = bytes([0x41, 0xD5, 0x42])  # A <distinguishing> B

    winner = resolve_by_category_voting(
        data, "enc_a", "enc_b", diff_bytes, categories
    )
    assert winner == "enc_a"


def test_category_voting_returns_none_on_tie():
    """When no distinguishing bytes appear, return None (no opinion)."""
    diff_bytes = frozenset({0xD5})
    categories = {0xD5: ("Ll", "So")}
    data = bytes([0x41, 0x42, 0x43])  # No distinguishing bytes

    winner = resolve_by_category_voting(
        data, "enc_a", "enc_b", diff_bytes, categories
    )
    assert winner is None
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_confusion.py::test_category_voting_prefers_letter_over_symbol tests/test_confusion.py::test_category_voting_returns_none_on_tie -v`
Expected: FAIL with `ImportError`

**Step 3: Implement `resolve_by_category_voting`**

Add to `src/chardet/pipeline/confusion.py`:

```python
# Unicode general category preference (higher = better).
# Letters are most preferred, control chars least.
_CATEGORY_PREFERENCE: dict[str, int] = {
    # Letters (most preferred — these are real text characters)
    "Lu": 10, "Ll": 10, "Lt": 10, "Lm": 9, "Lo": 9,
    # Numbers
    "Nd": 8, "Nl": 7, "No": 7,
    # Punctuation (common in text)
    "Pc": 6, "Pd": 6, "Ps": 6, "Pe": 6, "Pi": 6, "Pf": 6, "Po": 6,
    # Currency and math symbols
    "Sc": 5, "Sm": 5,
    # Other symbols (box drawing, dingbats, etc.)
    "Sk": 4, "So": 4,
    # Separators
    "Zs": 3, "Zl": 3, "Zp": 3,
    # Format/control (least preferred)
    "Cf": 2, "Cc": 1, "Co": 1, "Cs": 0, "Cn": 0,
    # Marks (combining) — neutral
    "Mn": 5, "Mc": 5, "Me": 5,
}


def resolve_by_category_voting(
    data: bytes,
    enc_a: str,
    enc_b: str,
    diff_bytes: frozenset[int],
    categories: dict[int, tuple[str, str]],
) -> str | None:
    """Resolve between two encodings using Unicode category voting.

    For each distinguishing byte present in the data, votes for the encoding
    whose character interpretation has a higher Unicode category preference.

    Returns the winning encoding name, or None if no distinguishing bytes
    were found or the vote was tied.
    """
    votes_a = 0
    votes_b = 0

    # Build a fast lookup set for bytes present in data
    data_bytes = set(data)
    relevant = data_bytes & diff_bytes

    if not relevant:
        return None

    for bv in relevant:
        cat_a, cat_b = categories[bv]
        pref_a = _CATEGORY_PREFERENCE.get(cat_a, 0)
        pref_b = _CATEGORY_PREFERENCE.get(cat_b, 0)
        if pref_a > pref_b:
            votes_a += 1
        elif pref_b > pref_a:
            votes_b += 1
        # Equal preference = no vote

    if votes_a > votes_b:
        return enc_a
    if votes_b > votes_a:
        return enc_b
    return None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_confusion.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/pipeline/confusion.py tests/test_confusion.py
git commit -m "feat: add Unicode category voting resolution strategy"
```

---

### Task 7: Resolution Strategies — Distinguishing-Bigram Re-Scoring

**Files:**
- Modify: `src/chardet/pipeline/confusion.py`
- Modify: `tests/test_confusion.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_confusion.py
from chardet.pipeline.confusion import resolve_by_bigram_rescore


def test_bigram_rescore_returns_winner():
    """Bigram re-scoring should return the encoding whose model better matches
    the distinguishing bigrams in the data."""
    # Use real encodings with loaded models
    from chardet.models import load_models

    models = load_models()
    # Only run if models exist
    if not models:
        return

    diff_bytes = frozenset({0xD5})
    data = bytes([0x41, 0xD5, 0x42, 0xD5, 0x43])

    # This is a smoke test — just verify it returns a valid result
    result = resolve_by_bigram_rescore(data, "cp850", "cp858", diff_bytes)
    assert result in ("cp850", "cp858", None)
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_confusion.py::test_bigram_rescore_returns_winner -v`
Expected: FAIL with `ImportError`

**Step 3: Implement `resolve_by_bigram_rescore`**

Add to `src/chardet/pipeline/confusion.py`:

```python
from chardet.models import BigramProfile, _get_enc_index, _score_with_profile


def resolve_by_bigram_rescore(
    data: bytes,
    enc_a: str,
    enc_b: str,
    diff_bytes: frozenset[int],
) -> str | None:
    """Resolve between two encodings by re-scoring only distinguishing bigrams.

    Extracts bigrams from the data that contain at least one distinguishing
    byte, scores them against each encoding's model, and returns the winner.

    Returns the winning encoding name, or None if no distinguishing bigrams
    were found or scores are tied.
    """
    if len(data) < 2:
        return None

    # Build a profile using only bigrams that contain distinguishing bytes
    freq: dict[int, int] = {}
    w_sum = 0
    for i in range(len(data) - 1):
        b1 = data[i]
        b2 = data[i + 1]
        if b1 not in diff_bytes and b2 not in diff_bytes:
            continue
        idx = (b1 << 8) | b2
        weight = 8 if (b1 > 0x7F or b2 > 0x7F) else 1
        freq[idx] = freq.get(idx, 0) + weight
        w_sum += weight

    if not freq:
        return None

    # Create a minimal BigramProfile with just the distinguishing bigrams
    profile = BigramProfile.__new__(BigramProfile)
    profile.weighted_freq = freq
    profile.weight_sum = w_sum

    # Score against each encoding's models
    index = _get_enc_index()
    best_a = 0.0
    variants_a = index.get(enc_a)
    if variants_a:
        for _, model in variants_a:
            s = _score_with_profile(profile, model)
            best_a = max(best_a, s)

    best_b = 0.0
    variants_b = index.get(enc_b)
    if variants_b:
        for _, model in variants_b:
            s = _score_with_profile(profile, model)
            best_b = max(best_b, s)

    if best_a > best_b:
        return enc_a
    if best_b > best_a:
        return enc_b
    return None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_confusion.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/chardet/pipeline/confusion.py tests/test_confusion.py
git commit -m "feat: add distinguishing-bigram re-scoring resolution strategy"
```

---

### Task 8: Integrate Resolution into Orchestrator Pipeline

**Files:**
- Modify: `src/chardet/pipeline/orchestrator.py`
- Modify: `tests/test_confusion.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_confusion.py
from chardet.pipeline.confusion import resolve_confusion_groups
from chardet.pipeline import DetectionResult


def test_resolve_confusion_groups_no_change_when_unrelated():
    """Results should not change when top candidates are not in a confusion group."""
    results = [
        DetectionResult(encoding="utf-8", confidence=0.95, language=None),
        DetectionResult(encoding="koi8-r", confidence=0.80, language="Russian"),
    ]
    data = b"Hello world"
    resolved = resolve_confusion_groups(data, results)
    assert resolved[0].encoding == "utf-8"


def test_resolve_confusion_groups_reorders_when_confused():
    """When top candidates are in a confusion group and distinguishing bytes
    are present, the resolution should potentially reorder."""
    # This is a smoke test — just verify no crash and valid output
    results = [
        DetectionResult(encoding="cp037", confidence=0.95, language="English"),
        DetectionResult(encoding="cp500", confidence=0.94, language="English"),
        DetectionResult(encoding="windows-1252", confidence=0.50, language="English"),
    ]
    data = bytes(range(256))  # Contains all bytes
    resolved = resolve_confusion_groups(data, results)
    assert len(resolved) == len(results)
    # All original encodings should still be present
    resolved_encs = {r.encoding for r in resolved}
    assert resolved_encs == {"cp037", "cp500", "windows-1252"}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_confusion.py::test_resolve_confusion_groups_no_change_when_unrelated tests/test_confusion.py::test_resolve_confusion_groups_reorders_when_confused -v`
Expected: FAIL with `ImportError`

**Step 3: Implement `resolve_confusion_groups`**

Add to `src/chardet/pipeline/confusion.py`:

```python
from chardet.pipeline import DetectionResult


def resolve_confusion_groups(
    data: bytes,
    results: list[DetectionResult],
    strategy: str = "hybrid",
) -> list[DetectionResult]:
    """Resolve confusion between similar encodings in the top results.

    Checks if the top 2 results belong to the same confusion group. If so,
    applies the specified resolution strategy to potentially reorder them.

    Strategies:
    - "category": Unicode category voting only
    - "bigram": Distinguishing-bigram re-scoring only
    - "hybrid": Try both; use bigram if they disagree
    - "none": No resolution (passthrough)

    Returns the (possibly reordered) results list.
    """
    if strategy == "none" or len(results) < 2:
        return results

    top = results[0]
    second = results[1]
    if top.encoding is None or second.encoding is None:
        return results

    # Find if top two are in the same confusion group
    maps = load_confusion_data()
    pair_key = _find_pair_key(maps, top.encoding, second.encoding)
    if pair_key is None:
        return results

    diff_bytes, categories = maps[pair_key]
    enc_a, enc_b = pair_key

    # Apply resolution strategy
    winner = None
    if strategy == "category":
        winner = resolve_by_category_voting(data, enc_a, enc_b, diff_bytes, categories)
    elif strategy == "bigram":
        winner = resolve_by_bigram_rescore(data, enc_a, enc_b, diff_bytes)
    elif strategy == "hybrid":
        cat_winner = resolve_by_category_voting(
            data, enc_a, enc_b, diff_bytes, categories
        )
        bigram_winner = resolve_by_bigram_rescore(data, enc_a, enc_b, diff_bytes)
        if cat_winner == bigram_winner:
            winner = cat_winner
        elif bigram_winner is not None:
            winner = bigram_winner  # Bigram takes priority on disagreement
        else:
            winner = cat_winner

    if winner is None:
        return results

    # If winner is already on top, no change
    if winner == top.encoding:
        return results

    # Swap: promote winner to top
    if winner == second.encoding:
        return [second, top, *results[2:]]

    return results


def _find_pair_key(
    maps: DistinguishingMaps,
    enc_a: str,
    enc_b: str,
) -> tuple[str, str] | None:
    """Find the pair key in the maps, checking both orderings."""
    if (enc_a, enc_b) in maps:
        return (enc_a, enc_b)
    if (enc_b, enc_a) in maps:
        return (enc_b, enc_a)
    return None
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_confusion.py -v`
Expected: PASS

**Step 5: Wire into orchestrator.py**

In `src/chardet/pipeline/orchestrator.py`, add the import and call:

```python
# Add import:
from chardet.pipeline.confusion import resolve_confusion_groups

# In run_pipeline(), after score_candidates (line ~442), before _demote_niche_latin:
results = list(score_candidates(data, tuple(valid_candidates)))
if not results:
    return [_FALLBACK_RESULT]

results = resolve_confusion_groups(data, results)  # NEW
results = _demote_niche_latin(data, results)
return _promote_koi8t(data, results)
```

Also do the same for `_score_structural_candidates` return path (line ~437):

```python
def _score_structural_candidates(...) -> list[DetectionResult]:
    ...
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results
    # Note: confusion resolution is called by the caller (run_pipeline)
```

Actually, since `_score_structural_candidates` is called from `run_pipeline` and its result is returned directly, we need to apply resolution there too. Modify the `run_pipeline` call site:

```python
if best_score >= _STRUCTURAL_CONFIDENCE_THRESHOLD:
    results = _score_structural_candidates(
        data, structural_scores, valid_candidates
    )
    results = resolve_confusion_groups(data, results)
    results = _demote_niche_latin(data, results)
    return _promote_koi8t(data, results)
```

**Step 6: Run the full test suite to verify no regressions**

Run: `uv run pytest tests/ -x --timeout=60`
Expected: All tests pass

**Step 7: Commit**

```bash
git add src/chardet/pipeline/confusion.py src/chardet/pipeline/orchestrator.py tests/test_confusion.py
git commit -m "feat: integrate confusion group resolution into detection pipeline"
```

---

### Task 9: Baseline Accuracy Measurement

**Files:**
- No code changes — measurement only

**Step 1: Run accuracy diagnostics to establish baseline**

Run: `uv run python scripts/diagnose_accuracy.py 2>&1 | tee baseline_accuracy.txt`

Record the total pass count and per-encoding breakdown.

**Step 2: Run the comparison script**

Run: `uv run python scripts/compare_detectors.py 2>&1 | tee post_confusion_comparison.txt`

**Step 3: Document results**

Note the accuracy delta vs the pre-confusion-resolution baseline. Focus on:
- EBCDIC family (cp037, cp500, cp1026)
- DOS family (cp437, cp850, cp858, cp865)
- ISO-8859 near-duplicates (iso-8859-1 vs iso-8859-15)

**Step 4: No commit (measurement artifacts are gitignored)**

---

### Task 10: Strategy Experimentation

**Files:**
- Modify: `src/chardet/pipeline/confusion.py` (if strategy parameter needs changing)
- Modify: `scripts/diagnose_accuracy.py` (add per-strategy reporting)

**Step 1: Add strategy comparison to diagnostics**

Modify `scripts/diagnose_accuracy.py` to test all three strategies:

```python
# Add near the end of main(), after the standard accuracy report:
from chardet.pipeline.confusion import resolve_confusion_groups

# Test each strategy's impact
for strategy in ("none", "category", "bigram", "hybrid"):
    # Temporarily override the default strategy
    # (This requires passing strategy through the pipeline — see below)
    pass
```

The cleanest way to experiment is to add an environment variable override:

```python
# In confusion.py, modify resolve_confusion_groups:
import os
_STRATEGY_OVERRIDE = os.environ.get("CHARDET_CONFUSION_STRATEGY")

def resolve_confusion_groups(data, results, strategy="hybrid"):
    if _STRATEGY_OVERRIDE:
        strategy = _STRATEGY_OVERRIDE
    ...
```

**Step 2: Run each strategy and compare**

```bash
CHARDET_CONFUSION_STRATEGY=none uv run python scripts/diagnose_accuracy.py 2>&1 | tail -5
CHARDET_CONFUSION_STRATEGY=category uv run python scripts/diagnose_accuracy.py 2>&1 | tail -5
CHARDET_CONFUSION_STRATEGY=bigram uv run python scripts/diagnose_accuracy.py 2>&1 | tail -5
CHARDET_CONFUSION_STRATEGY=hybrid uv run python scripts/diagnose_accuracy.py 2>&1 | tail -5
```

**Step 3: Select best strategy**

Based on the results, set the default strategy in `resolve_confusion_groups` to whichever performs best. Remove the environment variable override.

**Step 4: Commit**

```bash
git add src/chardet/pipeline/confusion.py scripts/diagnose_accuracy.py
git commit -m "feat: finalize confusion resolution strategy based on experimentation"
```

---

### Task 11: Run Full Training with Confusion Data

**Files:**
- Modify: `src/chardet/models/confusion.bin` (regenerated)

**Step 1: Run full training to regenerate all models and confusion data**

Run: `uv run python scripts/train.py --max-samples 15000`

This will take a while if data isn't cached. The confusion.bin generation should happen automatically at the end.

**Step 2: Verify confusion.bin was regenerated**

Run: `ls -la src/chardet/models/confusion.bin`

**Step 3: Run accuracy tests**

Run: `uv run pytest tests/test_accuracy.py -x --timeout=120`
Run: `uv run python scripts/diagnose_accuracy.py 2>&1 | tee final_accuracy.txt`

**Step 4: Commit updated models**

```bash
git add src/chardet/models/confusion.bin
git commit -m "feat: regenerate confusion.bin with full training data"
```

---

### Task 12: Final Verification and Cleanup

**Files:**
- Possibly modify: `src/chardet/pipeline/orchestrator.py` (remove old ad-hoc functions if superseded)
- Modify: `tests/test_confusion.py` (final integration tests)

**Step 1: Run full test suite**

Run: `uv run pytest tests/ --timeout=120`
Expected: All tests pass, no regressions

**Step 2: Run linting**

Run: `uv run ruff check .`
Run: `uv run ruff format --check .`

**Step 3: Verify performance**

Run: `uv run python scripts/benchmark_time.py --pure`

Confirm that the confusion resolution stage adds <0.1ms average per detection.

**Step 4: Final accuracy comparison**

Run: `uv run python scripts/compare_detectors.py 2>&1 | tee final_comparison.txt`

Verify:
- Overall accuracy improved (target: 15+ additional test files passing)
- No regressions on previously-passing encodings
- Detection time is still competitive

**Step 5: Commit any remaining cleanup**

```bash
git add -A
git commit -m "chore: final cleanup after confusion group resolution"
```
