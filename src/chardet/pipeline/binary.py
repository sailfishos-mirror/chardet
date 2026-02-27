"""Stage 0: Binary content detection."""

from __future__ import annotations

# Threshold: if more than this fraction of bytes are binary indicators, it's binary
_BINARY_THRESHOLD = 0.01

# Translation table that maps binary-indicator control bytes (0x00-0x08,
# 0x0E-0x1F — excludes \t \n \r) to None (deleting them) and keeps
# everything else.  len(data) - len(translated) gives the count in one
# C-level pass.
_BINARY_DELETE = bytes(range(0x09)) + bytes(range(0x0E, 0x20))


def is_binary(data: bytes, max_bytes: int = 200_000) -> bool:
    """Return True if data appears to be binary (not text) content."""
    data = data[:max_bytes]
    if not data:
        return False

    clean = data.translate(None, _BINARY_DELETE)
    binary_count = len(data) - len(clean)
    return binary_count / len(data) > _BINARY_THRESHOLD
