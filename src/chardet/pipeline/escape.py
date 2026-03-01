"""Early detection of escape-sequence-based encodings (ISO-2022, HZ-GB-2312, UTF-7).

These encodings use ESC (0x1B), tilde (~), or plus (+) sequences to switch
character sets.  They must be detected before binary detection (ESC is a control
byte) and before ASCII detection (HZ-GB-2312 and UTF-7 use only printable ASCII
bytes plus their respective shift markers).

Note: ``from __future__ import annotations`` is intentionally omitted because
this module is compiled with mypyc, which does not support PEP 563 string
annotations.
"""

from chardet.pipeline import DETERMINISTIC_CONFIDENCE, DetectionResult


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


# Base64 alphabet used inside UTF-7 shifted sequences (+<Base64>-)
_UTF7_BASE64: frozenset[int] = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
)


def _has_valid_utf7_sequences(data: bytes) -> bool:
    """Check that *data* contains at least one valid UTF-7 shifted sequence.

    A valid shifted sequence is ``+<base64 chars>-`` where the base64 portion
    is at least 3 characters long (the minimum for one UTF-16 code unit:
    16 bits -> 3 Base64 sextets).  The explicit ``-`` terminator is required to
    avoid false positives from timezone offsets, URLs, and similar patterns.
    The sequence ``+-`` is a literal plus sign and is **not** counted.
    """
    start = 0
    while True:
        pos = data.find(ord("+"), start)
        if pos == -1:
            return False
        pos += 1  # skip the '+'
        # +- is a literal plus, not a shifted sequence
        if pos < len(data) and data[pos] == ord("-"):
            start = pos + 1
            continue
        # Count consecutive Base64 characters
        b64_len = 0
        i = pos
        while i < len(data) and data[i] in _UTF7_BASE64:
            b64_len += 1
            i += 1
        # Require at least 3 Base64 chars AND an explicit '-' terminator
        if b64_len >= 3 and i < len(data) and data[i] == ord("-"):
            return True
        start = i if i > pos else pos


def detect_escape_encoding(data: bytes) -> DetectionResult | None:
    """Detect ISO-2022, HZ-GB-2312, and UTF-7 from escape/tilde/plus sequences.

    :param data: The raw byte data to examine.
    :returns: A :class:`DetectionResult` if an escape encoding is found, or ``None``.
    """
    if b"\x1b" not in data and b"~" not in data and b"+" not in data:
        return None

    # ISO-2022-JP: ESC sequences for JIS X 0208 / JIS X 0201
    if b"\x1b$B" in data or b"\x1b$@" in data or b"\x1b(J" in data:
        return DetectionResult(
            encoding="iso-2022-jp",
            confidence=DETERMINISTIC_CONFIDENCE,
            language="Japanese",
        )

    # ISO-2022-KR: ESC sequence for KS C 5601
    if b"\x1b$)C" in data:
        return DetectionResult(
            encoding="iso-2022-kr",
            confidence=DETERMINISTIC_CONFIDENCE,
            language="Korean",
        )

    # HZ-GB-2312: tilde escapes for GB2312
    # Require valid GB2312 byte pairs (0x21-0x7E range) between ~{ and ~} markers.
    if b"~{" in data and b"~}" in data and _has_valid_hz_regions(data):
        return DetectionResult(
            encoding="hz-gb-2312",
            confidence=DETERMINISTIC_CONFIDENCE,
            language="Chinese",
        )

    # UTF-7: plus-sign shifts into Base64-encoded Unicode
    if b"+" in data and _has_valid_utf7_sequences(data):
        return DetectionResult(
            encoding="utf-7",
            confidence=DETERMINISTIC_CONFIDENCE,
            language=None,
        )

    return None
