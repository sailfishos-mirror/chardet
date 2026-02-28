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
