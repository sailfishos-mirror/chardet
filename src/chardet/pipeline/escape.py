"""Early detection of escape-sequence-based encodings (ISO-2022, HZ-GB-2312).

These encodings use ESC (0x1B) or tilde (~) sequences to switch character sets.
They must be detected before binary detection (ESC is a control byte) and before
ASCII detection (HZ-GB-2312 uses only printable ASCII bytes plus tildes).
"""

from __future__ import annotations

from chardet.pipeline import DetectionResult

_ESCAPE_CONFIDENCE = 0.95


def detect_escape_encoding(data: bytes) -> DetectionResult | None:
    """Detect ISO-2022 and HZ-GB-2312 from escape/tilde sequences."""
    # ISO-2022-JP: ESC sequences for JIS X 0208 / JIS X 0201
    if b"\x1b$B" in data or b"\x1b$@" in data or b"\x1b(J" in data:
        return DetectionResult(
            encoding="iso-2022-jp", confidence=_ESCAPE_CONFIDENCE, language="Japanese"
        )

    # ISO-2022-KR: ESC sequence for KS C 5601
    if b"\x1b$)C" in data:
        return DetectionResult(
            encoding="iso-2022-kr", confidence=_ESCAPE_CONFIDENCE, language="Korean"
        )

    # HZ-GB-2312: tilde escapes for GB2312
    if b"~{" in data and b"~}" in data:
        return DetectionResult(
            encoding="hz-gb-2312", confidence=_ESCAPE_CONFIDENCE, language="Chinese"
        )

    return None
