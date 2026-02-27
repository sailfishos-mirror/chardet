"""Model loading and bigram scoring utilities."""

from __future__ import annotations

import importlib.resources
import struct

_MODEL_CACHE: dict[str, bytearray] | None = None
# Pre-grouped index: encoding name -> [(lang, model), ...]
_ENC_INDEX: dict[str, list[tuple[str, bytearray]]] | None = None


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

    offset = 0
    (num_encodings,) = struct.unpack_from("!I", data, offset)
    offset += 4

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

    _MODEL_CACHE = models
    return models


def _get_enc_index() -> dict[str, list[tuple[str, bytearray]]]:
    """Return a pre-grouped index mapping encoding name -> [(lang, model), ...]."""
    global _ENC_INDEX  # noqa: PLW0603
    if _ENC_INDEX is not None:
        return _ENC_INDEX
    models = load_models()
    index: dict[str, list[tuple[str, bytearray]]] = {}
    for key, model in models.items():
        if "/" in key:
            lang, enc = key.split("/", 1)
            index.setdefault(enc, []).append((lang, model))
        else:
            # Plain encoding key (backward compat / fallback)
            index.setdefault(key, []).append((None, model))
    _ENC_INDEX = index
    return index


def _score_with_model(data: bytes, model: bytearray) -> float:
    """Score data against a single model bytearray."""
    total_bigrams = len(data) - 1
    if total_bigrams <= 0:
        return 0.0

    score = 0
    weight_sum = 0
    for i in range(total_bigrams):
        b1 = data[i]
        b2 = data[i + 1]
        w = 8 if (b1 > 0x7F or b2 > 0x7F) else 1
        score += model[(b1 << 8) | b2] * w
        weight_sum += 255 * w

    if weight_sum == 0:
        return 0.0
    return score / weight_sum


def score_bigrams(
    data: bytes,
    encoding: str,
    models: dict[str, bytearray],
) -> float:
    """Score data against a specific encoding's bigram model. Returns 0.0-1.0."""
    if not data:
        return 0.0
    score, _ = score_best_language(data, encoding, models)
    return score


def score_best_language(
    data: bytes,
    encoding: str,
    models: dict[str, bytearray],  # noqa: ARG001
) -> tuple[float, str | None]:
    """Score data against all language variants of an encoding.

    Returns (best_score, best_language). Uses a pre-grouped index for O(L)
    lookup where L is the number of language variants for the encoding.

    The *models* parameter is accepted for API consistency with
    ``score_bigrams`` but the internal index (built once from the loaded
    models) is used for efficient lookup.
    """
    if not data:
        return 0.0, None

    index = _get_enc_index()
    variants = index.get(encoding)
    if variants is None:
        return 0.0, None

    best_score = 0.0
    best_lang: str | None = None
    for lang, model in variants:
        s = _score_with_model(data, model)
        if s > best_score:
            best_score = s
            best_lang = lang

    return best_score, best_lang
