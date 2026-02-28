"""Confusion group resolution for similar single-byte encodings.

At runtime, loads pre-computed distinguishing byte maps from confusion.bin
and uses them to resolve statistical scoring ties between similar encodings.

Build-time computation (``compute_confusion_groups``, ``compute_distinguishing_maps``,
``serialize_confusion_data``) lives in ``scripts/confusion_training.py``.
"""

from __future__ import annotations

import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chardet.pipeline import DetectionResult

# Type alias for the distinguishing map structure:
# Maps (enc_a, enc_b) -> (distinguishing_byte_set, {byte_val: (cat_a, cat_b)})
DistinguishingMaps = dict[
    tuple[str, str],
    tuple[frozenset[int], dict[int, tuple[str, str]]],
]

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


def load_confusion_data() -> DistinguishingMaps:
    """Load confusion group data from the bundled confusion.bin file."""
    global _CONFUSION_CACHE  # noqa: PLW0603
    if _CONFUSION_CACHE is not None:
        return _CONFUSION_CACHE
    import importlib.resources

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
            votes_a += pref_a - pref_b
        elif pref_b > pref_a:
            votes_b += pref_b - pref_a
    if votes_a > votes_b:
        return enc_a
    if votes_b > votes_a:
        return enc_b
    return None


def resolve_by_bigram_rescore(
    data: bytes,
    enc_a: str,
    enc_b: str,
    diff_bytes: frozenset[int],
) -> str | None:
    """Resolve between two encodings by re-scoring only distinguishing bigrams.

    Builds a focused bigram profile containing only bigrams where at least one
    byte is a distinguishing byte, then scores both encodings against their
    best language model.
    """
    from chardet.models import (
        BigramProfile,
        _get_enc_index,
        _score_with_profile,
    )

    if len(data) < 2:
        return None

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

    profile = BigramProfile.from_weighted_freq(freq, w_sum)

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


def _find_pair_key(
    maps: DistinguishingMaps,
    enc_a: str,
    enc_b: str,
) -> tuple[str, str] | None:
    """Find the canonical key for a pair of encodings in the confusion maps."""
    if (enc_a, enc_b) in maps:
        return (enc_a, enc_b)
    if (enc_b, enc_a) in maps:
        return (enc_b, enc_a)
    return None


def resolve_confusion_groups(
    data: bytes,
    results: list[DetectionResult],
    strategy: str = "hybrid",
) -> list[DetectionResult]:
    """Resolve confusion between similar encodings in the top results.

    Compares the top two results. If they form a known confusion pair,
    applies the specified resolution strategy to determine the winner.

    Strategies:
    - "category": Unicode category voting only
    - "bigram": Distinguishing-bigram re-scoring only
    - "hybrid": Both strategies; bigram wins on disagreement
    - "none": No resolution (passthrough)
    """
    if strategy == "none" or len(results) < 2:
        return results

    top = results[0]
    second = results[1]
    if top.encoding is None or second.encoding is None:
        return results

    maps = load_confusion_data()
    pair_key = _find_pair_key(maps, top.encoding, second.encoding)
    if pair_key is None:
        return results

    diff_bytes, categories = maps[pair_key]
    enc_a, enc_b = pair_key

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
            winner = bigram_winner
        else:
            winner = cat_winner

    if winner is None or winner == top.encoding:
        return results

    if winner == second.encoding:
        return [second, top, *results[2:]]

    return results
