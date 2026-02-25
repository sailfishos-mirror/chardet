"""Model loading and bigram scoring utilities."""

from __future__ import annotations

import importlib.resources
import struct

_MODEL_CACHE: dict[str, dict[tuple[int, int], int]] | None = None


def load_models() -> dict[str, dict[tuple[int, int], int]]:
    """Load all bigram models from the bundled models.bin file."""
    global _MODEL_CACHE  # noqa: PLW0603
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE

    models: dict[str, dict[tuple[int, int], int]] = {}
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

        bigrams: dict[tuple[int, int], int] = {}
        for _ in range(num_entries):
            b1, b2, weight = struct.unpack_from("!BBB", data, offset)
            offset += 3
            bigrams[(b1, b2)] = weight
        models[name] = bigrams

    _MODEL_CACHE = models
    return models


def score_bigrams(
    data: bytes,
    encoding: str,
    models: dict[str, dict[tuple[int, int], int]],
) -> float:
    """Score data against a specific encoding's bigram model. Returns 0.0-1.0."""
    if not data or encoding not in models:
        return 0.0

    model = models[encoding]
    if not model:
        return 0.0

    total_bigrams = len(data) - 1
    if total_bigrams <= 0:
        return 0.0

    score = 0
    weight_sum = 0
    for i in range(total_bigrams):
        b1 = data[i]
        b2 = data[i + 1]
        pair = (b1, b2)
        # High-byte bigrams are much more discriminative for single-byte encodings
        w = 8 if (b1 > 0x7F or b2 > 0x7F) else 1
        if pair in model:
            score += model[pair] * w
        weight_sum += 255 * w

    if weight_sum == 0:
        return 0.0
    return score / weight_sum
