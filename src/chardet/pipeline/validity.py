"""Stage 2a: Byte sequence validity filtering."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chardet.registry import EncodingInfo


def filter_by_validity(
    data: bytes, candidates: tuple[EncodingInfo, ...]
) -> tuple[EncodingInfo, ...]:
    """Filter candidates to only those where data decodes without errors."""
    if not data:
        return candidates

    valid = []
    for enc in candidates:
        try:
            data.decode(enc.python_codec, errors="strict")
            valid.append(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return tuple(valid)
