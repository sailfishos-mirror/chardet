"""Stage 3: Statistical bigram scoring with optional parallelism."""

from __future__ import annotations

import concurrent.futures
import os
from typing import TYPE_CHECKING

from chardet.models import load_models, score_bigrams
from chardet.pipeline import DetectionResult

if TYPE_CHECKING:
    from chardet.registry import EncodingInfo

_PARALLEL_THRESHOLD = 6


def _score_one(data: bytes, encoding_name: str) -> tuple[str, float]:
    """Score a single encoding — callable by pool workers."""
    models = load_models()
    return (encoding_name, score_bigrams(data, encoding_name, models))


def score_candidates(
    data: bytes, candidates: tuple[EncodingInfo, ...]
) -> list[DetectionResult]:
    """Score all candidates and return results sorted by confidence descending."""
    if not data or not candidates:
        return []

    models = load_models()
    scores: list[tuple[str, float]] = []

    workers = int(os.environ.get("CHARDET_WORKERS", "0")) or os.cpu_count() or 1
    use_parallel = len(candidates) > _PARALLEL_THRESHOLD and workers > 1

    if use_parallel:
        try:
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(_score_one, data, enc.name): enc for enc in candidates
                }
                for future in concurrent.futures.as_completed(futures):
                    try:
                        scores.append(future.result())
                    except Exception:  # noqa: BLE001
                        enc = futures[future]
                        scores.append((enc.name, 0.0))
        except (RuntimeError, OSError):
            use_parallel = False

    if not use_parallel and not scores:
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
