"""Internal shared utilities for chardet."""

from __future__ import annotations

from chardet.enums import EncodingEra


def _resolve_rename(
    should_rename_legacy: bool | None, encoding_era: EncodingEra
) -> bool:
    if should_rename_legacy is None:
        return encoding_era == EncodingEra.MODERN_WEB
    return should_rename_legacy


def _validate_max_bytes(max_bytes: int) -> None:
    if not isinstance(max_bytes, int) or max_bytes < 1:
        msg = "max_bytes must be a positive integer"
        raise ValueError(msg)
