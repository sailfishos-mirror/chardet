"""Stage 3: Statistical bigram scoring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chardet.models import load_models, score_bigrams
from chardet.pipeline import DetectionResult

if TYPE_CHECKING:
    from chardet.registry import EncodingInfo


def score_candidates(
    data: bytes, candidates: tuple[EncodingInfo, ...]
) -> list[DetectionResult]:
    """Score all candidates and return results sorted by confidence descending."""
    if not data or not candidates:
        return []

    models = load_models()
    scores: list[tuple[str, float]] = []

    for enc in candidates:
        s = score_bigrams(data, enc.name, models)
        scores.append((enc.name, s))

    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)

    # Normalize to confidence values
    max_score = scores[0][1] if scores else 0.0
    results = []
    for name, s in scores:
        if s <= 0.0:
            continue
        confidence = s / max_score if max_score > 0 else 0.0
        results.append(
            DetectionResult(encoding=name, confidence=confidence, language=None)
        )

    return results
