"""Universal character encoding detector — MIT-licensed rewrite."""

from __future__ import annotations

from chardet.detector import UniversalDetector
from chardet.enums import EncodingEra, LanguageFilter
from chardet.pipeline.orchestrator import run_pipeline

__version__ = "6.1.0"
__all__ = [
    "EncodingEra",
    "LanguageFilter",
    "UniversalDetector",
    "detect",
    "detect_all",
]


def detect(
    byte_str: bytes | bytearray,
    should_rename_legacy: bool | None = None,  # noqa: ARG001
    encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
    chunk_size: int = 65_536,  # noqa: ARG001
    max_bytes: int = 200_000,
) -> dict[str, str | float | None]:
    """Detect the encoding of the given byte string.

    Parameters match chardet 6.x for backward compatibility.
    *should_rename_legacy* and *chunk_size* are accepted but not used.
    """
    results = run_pipeline(bytes(byte_str), encoding_era, max_bytes=max_bytes)
    return results[0].to_dict()


def detect_all(  # noqa: PLR0913
    byte_str: bytes | bytearray,
    ignore_threshold: bool = False,  # noqa: ARG001, FBT001, FBT002
    should_rename_legacy: bool | None = None,  # noqa: ARG001
    encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
    chunk_size: int = 65_536,  # noqa: ARG001
    max_bytes: int = 200_000,
) -> list[dict[str, str | float | None]]:
    """Detect all possible encodings of the given byte string.

    Parameters match chardet 6.x for backward compatibility.
    *ignore_threshold*, *should_rename_legacy*, and *chunk_size* are accepted
    but not used.
    """
    results = run_pipeline(bytes(byte_str), encoding_era, max_bytes=max_bytes)
    return [r.to_dict() for r in results]
