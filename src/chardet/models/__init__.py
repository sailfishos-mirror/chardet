"""Model loading and bigram scoring utilities.

Note: ``from __future__ import annotations`` is intentionally omitted because
this module is compiled with mypyc, which does not support PEP 563 string
annotations.
"""

import importlib.resources
import struct

_MODEL_CACHE: dict[str, bytearray] | None = None
# Pre-grouped index: encoding name -> [(lang, model), ...]
_ENC_INDEX: dict[str, list[tuple[str | None, bytearray]]] | None = None


def load_models() -> dict[str, bytearray]:
    """Load all bigram models from the bundled models.bin file.

    Each model is a bytearray of length 65536 (256*256).
    Index: (b1 << 8) | b2 -> weight (0-255).
    """
    global _MODEL_CACHE  # noqa: PLW0603
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    models: dict[str, bytearray] = {}
    ref = importlib.resources.files("chardet.models").joinpath("models.bin")
    data = ref.read_bytes()

    if not data:
        _MODEL_CACHE = models
        return models

    try:
        offset = 0
        (num_encodings,) = struct.unpack_from("!I", data, offset)
        offset += 4

        if num_encodings > 10_000:
            msg = f"corrupt models.bin: num_encodings={num_encodings} exceeds limit"
            raise ValueError(msg)

        for _ in range(num_encodings):
            (name_len,) = struct.unpack_from("!I", data, offset)
            offset += 4
            name = data[offset : offset + name_len].decode("utf-8")
            offset += name_len
            (num_entries,) = struct.unpack_from("!I", data, offset)
            offset += 4

            table = bytearray(65536)
            for _ in range(num_entries):
                b1, b2, weight = struct.unpack_from("!BBB", data, offset)
                offset += 3
                table[(b1 << 8) | b2] = weight
            models[name] = table
    except (struct.error, UnicodeDecodeError) as e:
        msg = f"corrupt models.bin: {e}"
        raise ValueError(msg) from e

    _MODEL_CACHE = models
    return models


def _get_enc_index() -> dict[str, list[tuple[str | None, bytearray]]]:
    """Return a pre-grouped index mapping encoding name -> [(lang, model), ...]."""
    global _ENC_INDEX  # noqa: PLW0603
    if _ENC_INDEX is not None:
        return _ENC_INDEX
    models = load_models()
    index: dict[str, list[tuple[str | None, bytearray]]] = {}
    for key, model in models.items():
        if "/" in key:
            lang, enc = key.split("/", 1)
            index.setdefault(enc, []).append((lang, model))
        else:
            # Plain encoding key (backward compat / fallback)
            index.setdefault(key, []).append((None, model))
    _ENC_INDEX = index
    return index


class BigramProfile:
    """Pre-computed bigram frequency distribution for a data sample.

    Computing this once and reusing it across all models reduces per-model
    scoring from O(n) to O(distinct_bigrams).

    Stores a single ``weighted_freq`` dict mapping bigram index to
    *count * weight* (weight is 8 for non-ASCII bigrams, 1 otherwise).
    This pre-multiplies the weight during construction so the scoring
    inner loop only needs a single dict traversal with no branching.
    """

    __slots__ = ("weight_sum", "weighted_freq")

    def __init__(self, data: bytes) -> None:
        total_bigrams = len(data) - 1
        if total_bigrams <= 0:
            self.weighted_freq: dict[int, int] = {}
            self.weight_sum: int = 0
            return

        freq: dict[int, int] = {}
        w_sum = 0
        _get = freq.get
        for i in range(total_bigrams):
            b1 = data[i]
            b2 = data[i + 1]
            idx = (b1 << 8) | b2
            if b1 > 0x7F or b2 > 0x7F:
                freq[idx] = _get(idx, 0) + 8
                w_sum += 8
            else:
                freq[idx] = _get(idx, 0) + 1
                w_sum += 1
        self.weighted_freq = freq
        self.weight_sum = w_sum


def _score_with_profile(profile: BigramProfile, model: bytearray) -> float:
    """Score a pre-computed bigram profile against a single model."""
    if profile.weight_sum == 0:
        return 0.0
    score = 0
    for idx, wcount in profile.weighted_freq.items():
        score += model[idx] * wcount
    return score / (255 * profile.weight_sum)


def score_bigrams(
    data: bytes,
    encoding: str,
    models: dict[str, bytearray] | None = None,
) -> float:
    """Score data against a specific encoding's bigram model. Returns 0.0-1.0.

    Convenience wrapper around ``score_best_language`` that discards the
    language result.  Primarily used in tests.
    """
    if not data:
        return 0.0
    score, _ = score_best_language(data, encoding, models)
    return score


def score_best_language(
    data: bytes,
    encoding: str,
    models: dict[str, bytearray] | None = None,  # noqa: ARG001
    profile: BigramProfile | None = None,
) -> tuple[float, str | None]:
    """Score data against all language variants of an encoding.

    Returns (best_score, best_language). Uses a pre-grouped index for O(L)
    lookup where L is the number of language variants for the encoding.

    The *models* parameter is accepted for backward compatibility but is not
    used; the internal index (built once from the loaded models) is used
    for efficient lookup.

    If *profile* is provided, it is reused instead of recomputing the bigram
    frequency distribution from *data*.
    """
    if not data:
        return 0.0, None

    index = _get_enc_index()
    variants = index.get(encoding)
    if variants is None:
        return 0.0, None

    if profile is None:
        profile = BigramProfile(data)

    best_score = 0.0
    best_lang: str | None = None
    for lang, model in variants:
        s = _score_with_profile(profile, model)
        if s > best_score:
            best_score = s
            best_lang = lang

    return best_score, best_lang
