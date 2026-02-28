"""Confusion group computation and resolution for similar single-byte encodings.

Encodings that share >80% of their byte-to-Unicode mappings are grouped together.
Within a group, distinguishing bytes (positions where encodings differ) are used
to resolve statistical scoring ties.
"""

from __future__ import annotations

import codecs
import importlib.resources
import struct
import unicodedata
from pathlib import Path

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
    share more than ``threshold`` fraction of their byte mappings.
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
            queue.extend(
                neighbor for neighbor in adjacency[current] if neighbor not in visited
            )
        if len(group) > 1:
            groups.append(frozenset(group))

    return groups


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


# Unicode general category -> uint8 encoding for struct serialization
_CATEGORY_TO_INT: dict[str, int] = {
    "Lu": 0,
    "Ll": 1,
    "Lt": 2,
    "Lm": 3,
    "Lo": 4,  # Letters
    "Mn": 5,
    "Mc": 6,
    "Me": 7,  # Marks
    "Nd": 8,
    "Nl": 9,
    "No": 10,  # Numbers
    "Pc": 11,
    "Pd": 12,
    "Ps": 13,
    "Pe": 14,  # Punctuation
    "Pi": 15,
    "Pf": 16,
    "Po": 17,
    "Sm": 18,
    "Sc": 19,
    "Sk": 20,
    "So": 21,  # Symbols
    "Zs": 22,
    "Zl": 23,
    "Zp": 24,  # Separators
    "Cc": 25,
    "Cf": 26,
    "Cs": 27,
    "Co": 28,
    "Cn": 29,  # Other
}
_INT_TO_CATEGORY: dict[int, str] = {v: k for k, v in _CATEGORY_TO_INT.items()}

_CONFUSION_CACHE: DistinguishingMaps | None = None


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
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
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
                f.write(
                    struct.pack(
                        "!BBB",
                        bv,
                        _CATEGORY_TO_INT.get(cat_a, 29),
                        _CATEGORY_TO_INT.get(cat_b, 29),
                    )
                )
    return out.stat().st_size


def deserialize_confusion_data_from_bytes(data: bytes) -> DistinguishingMaps:
    """Load confusion group data from raw bytes."""
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

        diff_bytes_list: list[int] = []
        categories: dict[int, tuple[str, str]] = {}
        for _ in range(num_diffs):
            bv, cat_a_int, cat_b_int = struct.unpack_from("!BBB", data, offset)
            offset += 3
            diff_bytes_list.append(bv)
            categories[bv] = (
                _INT_TO_CATEGORY.get(cat_a_int, "Cn"),
                _INT_TO_CATEGORY.get(cat_b_int, "Cn"),
            )
        result[(name_a, name_b)] = (frozenset(diff_bytes_list), categories)

    return result


def deserialize_confusion_data(input_path: str) -> DistinguishingMaps:
    """Load confusion group data from binary format."""
    with Path(input_path).open("rb") as f:
        data = f.read()
    return deserialize_confusion_data_from_bytes(data)


def load_confusion_data() -> DistinguishingMaps:
    """Load confusion group data from the bundled confusion.bin file."""
    global _CONFUSION_CACHE  # noqa: PLW0603
    if _CONFUSION_CACHE is not None:
        return _CONFUSION_CACHE
    ref = importlib.resources.files("chardet.models").joinpath("confusion.bin")
    raw = ref.read_bytes()
    if not raw:
        _CONFUSION_CACHE = {}
        return _CONFUSION_CACHE
    _CONFUSION_CACHE = deserialize_confusion_data_from_bytes(raw)
    return _CONFUSION_CACHE


# Unicode general category preference scores for voting resolution.
# Higher scores indicate more linguistically meaningful characters.
_CATEGORY_PREFERENCE: dict[str, int] = {
    "Lu": 10,
    "Ll": 10,
    "Lt": 10,
    "Lm": 9,
    "Lo": 9,
    "Nd": 8,
    "Nl": 7,
    "No": 7,
    "Pc": 6,
    "Pd": 6,
    "Ps": 6,
    "Pe": 6,
    "Pi": 6,
    "Pf": 6,
    "Po": 6,
    "Sc": 5,
    "Sm": 5,
    "Sk": 4,
    "So": 4,
    "Zs": 3,
    "Zl": 3,
    "Zp": 3,
    "Cf": 2,
    "Cc": 1,
    "Co": 1,
    "Cs": 0,
    "Cn": 0,
    "Mn": 5,
    "Mc": 5,
    "Me": 5,
}


def resolve_by_category_voting(
    data: bytes,
    enc_a: str,
    enc_b: str,
    diff_bytes: frozenset[int],
    categories: dict[int, tuple[str, str]],
) -> str | None:
    """Resolve between two encodings using Unicode category voting.

    For each distinguishing byte present in the data, compare the Unicode
    general category under each encoding. The encoding whose interpretation
    has the higher category preference score gets a vote. The encoding with
    more votes wins.
    """
    votes_a = 0
    votes_b = 0
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
    if votes_a > votes_b:
        return enc_a
    if votes_b > votes_a:
        return enc_b
    return None
