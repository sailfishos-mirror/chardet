"""Model loading and bigram scoring utilities."""

from __future__ import annotations

import importlib.resources
import struct

_MODEL_CACHE: dict[str, bytearray] | None = None


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
    if not data or encoding not in models:
        return 0.0
    return _score_with_model(data, models[encoding])


def score_best_language(
    data: bytes,
    encoding: str,
    models: dict[str, bytearray],
) -> tuple[float, str | None]:
    """Score data against all language variants of an encoding.

    Returns (best_score, best_language). If no language-specific models
    exist, falls back to the plain encoding model.
    """
    best_score = 0.0
    best_lang: str | None = None

    suffix = f"/{encoding}"
    for key, model in models.items():
        if key.endswith(suffix) and "/" in key:
            lang = key.split("/", 1)[0]
            s = _score_with_model(data, model)
            if s > best_score:
                best_score = s
                best_lang = lang

    # Fall back to plain encoding model if no language variants exist
    if best_score == 0.0 and encoding in models:
        best_score = _score_with_model(data, models[encoding])

    return best_score, best_lang
