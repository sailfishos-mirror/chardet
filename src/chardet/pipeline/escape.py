"""Early detection of escape-sequence-based encodings (ISO-2022, HZ-GB-2312).

These encodings use ESC (0x1B) or tilde (~) sequences to switch character sets.
They must be detected before binary detection (ESC is a control byte) and before
ASCII detection (HZ-GB-2312 uses only printable ASCII bytes plus tildes).

Note: ``from __future__ import annotations`` is intentionally omitted because
this module is compiled with mypyc, which does not support PEP 563 string
annotations.
"""

from chardet.pipeline import DetectionResult

_ESCAPE_CONFIDENCE = 0.95


def _has_valid_hz_regions(data: bytes) -> bool:
    """Check that at least one ~{...~} region contains valid GB2312 byte pairs.

    In HZ-GB-2312 GB mode, characters are encoded as pairs of bytes in the
    0x21-0x7E range.  We require at least one region with a non-empty, even-
    length run of such bytes.
    """
    start = 0
    while True:
        begin = data.find(b"~{", start)
        if begin == -1:
            return False
        end = data.find(b"~}", begin + 2)
        if end == -1:
            return False
        region = data[begin + 2 : end]
        # Must be non-empty, even length, and all bytes in GB2312 range
        if (
            len(region) >= 2
            and len(region) % 2 == 0
            and all(0x21 <= b <= 0x7E for b in region)
        ):
            return True
        start = end + 2


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
    # Require valid GB2312 byte pairs (0x21-0x7E range) between ~{ and ~} markers.
    if b"~{" in data and b"~}" in data and _has_valid_hz_regions(data):
        return DetectionResult(
            encoding="hz-gb-2312", confidence=_ESCAPE_CONFIDENCE, language="Chinese"
        )

    return None
