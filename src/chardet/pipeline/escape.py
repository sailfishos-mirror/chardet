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
_B64_CHARS: bytes = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_UTF7_BASE64: frozenset[int] = frozenset(_B64_CHARS)

# Lookup table mapping each Base64 byte to its 6-bit value (0-63).
_B64_DECODE: dict[int, int] = {c: i for i, c in enumerate(_B64_CHARS)}


def _is_valid_utf7_b64(b64_bytes: bytes) -> bool:
    """Check if base64 bytes decode to valid UTF-16BE with correct padding.

    A valid UTF-7 shifted sequence must:
    1. Contain at least 3 Base64 characters (18 bits, enough for one 16-bit
       UTF-16 code unit).
    2. Have zero-valued trailing padding bits (the unused low bits of the last
       Base64 sextet after the last complete 16-bit code unit).

    This rejects accidental ``+<alphanum>-`` patterns found in URLs, MIME
    boundaries, and other ASCII data.
    """
    n = len(b64_bytes)
    if n < 3:  # Need at least 18 bits for one UTF-16 code unit
        return False
    total_bits = n * 6
    # Check that padding bits (trailing bits after last complete code unit)
    # are zero.
    padding_bits = total_bits % 16
    if padding_bits > 0:
        last_val = _B64_DECODE.get(b64_bytes[-1], -1)
        if last_val < 0:
            return False
        # The low `padding_bits` of the last sextet must be zero
        mask = (1 << padding_bits) - 1
        if last_val & mask:
            return False
    return True


def _has_valid_utf7_sequences(data: bytes) -> bool:
    """Check that *data* contains at least one valid UTF-7 shifted sequence.

    A valid shifted sequence is ``+<base64 chars>`` terminated by either an
    explicit ``-`` or any non-Base64 character (per RFC 2152).  The base64
    portion must decode to valid UTF-16BE with correct zero-padding bits.
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
        # Collect consecutive Base64 characters
        i = pos
        while i < len(data) and data[i] in _UTF7_BASE64:
            i += 1
        b64_len = i - pos
        # Accept if base64 content is valid UTF-16BE (padding bits check
        # prevents false positives).  Terminator can be '-', any non-Base64
        # byte, or end of data — all per RFC 2152.
        if b64_len >= 3 and _is_valid_utf7_b64(data[pos:i]):
            return True
        start = max(pos, i)


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
