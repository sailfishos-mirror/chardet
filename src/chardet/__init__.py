"""Universal character encoding detector — MIT-licensed rewrite."""

from __future__ import annotations

import warnings

from chardet.detector import UniversalDetector
from chardet.enums import EncodingEra, LanguageFilter
from chardet.equivalences import apply_legacy_rename
from chardet.pipeline.orchestrator import run_pipeline

__version__ = "6.1.0"
__all__ = [
    "EncodingEra",
    "LanguageFilter",
    "UniversalDetector",
    "detect",
    "detect_all",
]


def _resolve_rename(
    should_rename_legacy: bool | None, encoding_era: EncodingEra
) -> bool:
    if should_rename_legacy is None:
        return encoding_era == EncodingEra.MODERN_WEB
    return should_rename_legacy


def detect(
    byte_str: bytes | bytearray,
    should_rename_legacy: bool | None = None,
    encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
    chunk_size: int = 65_536,
    max_bytes: int = 200_000,
) -> dict[str, str | float | None]:
    """Detect the encoding of the given byte string.

    Parameters match chardet 6.x for backward compatibility.
    *chunk_size* is accepted but has no effect.
    """
    if chunk_size != 65_536:
        warnings.warn(
            "chunk_size is not used in this version of chardet and will be ignored",
            DeprecationWarning,
            stacklevel=2,
        )
    results = run_pipeline(bytes(byte_str), encoding_era, max_bytes=max_bytes)
    result = results[0].to_dict()
    if _resolve_rename(should_rename_legacy, encoding_era):
        apply_legacy_rename(result)
    return result


def detect_all(  # noqa: PLR0913
    byte_str: bytes | bytearray,
    ignore_threshold: bool = False,
    should_rename_legacy: bool | None = None,
    encoding_era: EncodingEra = EncodingEra.MODERN_WEB,
    chunk_size: int = 65_536,
    max_bytes: int = 200_000,
) -> list[dict[str, str | float | None]]:
    """Detect all possible encodings of the given byte string.

    Parameters match chardet 6.x for backward compatibility.
    *chunk_size* is accepted but has no effect.
    """
    if chunk_size != 65_536:
        warnings.warn(
            "chunk_size is not used in this version of chardet and will be ignored",
            DeprecationWarning,
            stacklevel=2,
        )
    results = run_pipeline(bytes(byte_str), encoding_era, max_bytes=max_bytes)
    rename = _resolve_rename(should_rename_legacy, encoding_era)
    dicts = [r.to_dict() for r in results]
    if not ignore_threshold:
        filtered = [
            d
            for d in dicts
            if (d.get("confidence") or 0) > UniversalDetector.MINIMUM_THRESHOLD
        ]
        if filtered:
            dicts = filtered
    if rename:
        for d in dicts:
            apply_legacy_rename(d)
    return sorted(dicts, key=lambda d: -(d.get("confidence") or 0))
