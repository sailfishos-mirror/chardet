"""Universal character encoding detector — MIT-licensed rewrite."""

from __future__ import annotations

from chardet.detector import UniversalDetector
from chardet.enums import EncodingEra
from chardet.pipeline.orchestrator import run_pipeline

__version__ = "6.1.0"
__all__ = [
    "EncodingEra",
    "UniversalDetector",
    "detect",
    "detect_all",
]


def detect(
    data: bytes,
    max_bytes: int = 200_000,
    chunk_size: int = 65_536,  # noqa: ARG001 — kept for chardet 6.x API compat
    encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
) -> dict[str, str | float | None]:
    """Detect the encoding of the given byte string."""
    results = run_pipeline(data, encoding_era, max_bytes=max_bytes)
    return results[0].to_dict()


def detect_all(
    data: bytes,
    max_bytes: int = 200_000,
    chunk_size: int = 65_536,  # noqa: ARG001 — kept for chardet 6.x API compat
    encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
) -> list[dict[str, str | float | None]]:
    """Detect all possible encodings of the given byte string."""
    results = run_pipeline(data, encoding_era, max_bytes=max_bytes)
    return [r.to_dict() for r in results]
