"""Stage 1: Pure ASCII detection."""

from __future__ import annotations

from chardet.pipeline import DetectionResult


def detect_ascii(data: bytes) -> DetectionResult | None:
    """Return ASCII result if all bytes are printable ASCII + common whitespace."""
    if not data:
        return None
    # Check that every byte is in the range 0x09-0x0D (whitespace) or 0x20-0x7E
    for byte in data:
        if byte > 0x7E or (byte < 0x20 and byte not in (0x09, 0x0A, 0x0D)):
            return None
    return DetectionResult(encoding="ascii", confidence=1.0, language=None)
