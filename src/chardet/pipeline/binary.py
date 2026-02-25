"""Stage 0: Binary content detection."""

from __future__ import annotations

# Control chars that indicate binary (excluding tab, newline, carriage return)
_BINARY_CONTROL_BYTES = frozenset(range(0x09)) | frozenset(range(0x0E, 0x20))

# Threshold: if more than this fraction of bytes are binary indicators, it's binary
_BINARY_THRESHOLD = 0.01


def is_binary(data: bytes, max_bytes: int = 200_000) -> bool:
    """Return True if data appears to be binary (not text) content."""
    data = data[:max_bytes]
    if not data:
        return False

    binary_count = sum(1 for b in data if b in _BINARY_CONTROL_BYTES)
    return binary_count / len(data) > _BINARY_THRESHOLD
