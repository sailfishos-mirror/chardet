"""Stage 2b: Multi-byte structural probing.

Computes how well byte patterns in the data match the expected multi-byte
structure for a given encoding.  Used after byte-validity filtering (Stage 2a)
to further rank multi-byte encoding candidates.
"""

from collections.abc import Callable

from chardet.registry import EncodingInfo

# ---------------------------------------------------------------------------
# Per-encoding structural scorers
# ---------------------------------------------------------------------------


def _score_shift_jis(data: bytes) -> float:
    """Score data against Shift_JIS / CP932 structure.

    Lead bytes: 0x81-0x9F, 0xE0-0xEF
    Trail bytes: 0x40-0x7E, 0x80-0xFC
    """
    lead_count = 0
    valid_count = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xEF):
            lead_count += 1
            if i + 1 < length:
                trail = data[i + 1]
                if (0x40 <= trail <= 0x7E) or (0x80 <= trail <= 0xFC):
                    valid_count += 1
                    i += 2
                    continue
            # Lead byte without valid trail
            i += 1
        else:
            i += 1
    if lead_count == 0:
        return 0.0
    return valid_count / lead_count


def _score_euc_jp(data: bytes) -> float:
    """Score data against EUC-JP structure.

    Two-byte: Lead 0xA1-0xFE, Trail 0xA1-0xFE
    SS2 (half-width katakana): 0x8E + 0xA1-0xDF
    SS3 (JIS X 0212): 0x8F + 0xA1-0xFE + 0xA1-0xFE
    """
    lead_count = 0
    valid_count = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if b == 0x8E:
            # SS2 sequence
            lead_count += 1
            if i + 1 < length and 0xA1 <= data[i + 1] <= 0xDF:
                valid_count += 1
                i += 2
                continue
            i += 1
        elif b == 0x8F:
            # SS3 sequence
            lead_count += 1
            if (
                i + 2 < length
                and 0xA1 <= data[i + 1] <= 0xFE
                and 0xA1 <= data[i + 2] <= 0xFE
            ):
                valid_count += 1
                i += 3
                continue
            i += 1
        elif 0xA1 <= b <= 0xFE:
            lead_count += 1
            if i + 1 < length and 0xA1 <= data[i + 1] <= 0xFE:
                valid_count += 1
                i += 2
                continue
            i += 1
        else:
            i += 1
    if lead_count == 0:
        return 0.0
    return valid_count / lead_count


def _score_euc_kr(data: bytes) -> float:
    """Score data against EUC-KR / CP949 structure.

    Lead 0xA1-0xFE; Trail 0xA1-0xFE
    """
    lead_count = 0
    valid_count = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if 0xA1 <= b <= 0xFE:
            lead_count += 1
            if i + 1 < length and 0xA1 <= data[i + 1] <= 0xFE:
                valid_count += 1
                i += 2
                continue
            i += 1
        else:
            i += 1
    if lead_count == 0:
        return 0.0
    return valid_count / lead_count


def _score_gb18030(data: bytes) -> float:
    """Score data against GB18030 / GB2312 structure.

    Only counts strict GB2312 2-byte pairs (lead 0xA1-0xF7, trail 0xA1-0xFE)
    and GB18030 4-byte sequences.  The broader GBK extension range
    (lead 0x81-0xFE, trail 0x40-0x7E / 0x80-0xFE) is intentionally excluded
    because it is so permissive that unrelated single-byte data (EBCDIC, DOS
    codepages, etc.) can score 1.0, leading to false positives.
    """
    lead_count = 0
    valid_count = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if 0x81 <= b <= 0xFE:
            lead_count += 1
            # Try 4-byte first (byte2 in 0x30-0x39 distinguishes from 2-byte)
            if (
                i + 3 < length
                and 0x30 <= data[i + 1] <= 0x39
                and 0x81 <= data[i + 2] <= 0xFE
                and 0x30 <= data[i + 3] <= 0x39
            ):
                valid_count += 1
                i += 4
                continue
            # 2-byte GB2312: Lead 0xA1-0xF7, Trail 0xA1-0xFE
            if 0xA1 <= b <= 0xF7 and i + 1 < length and 0xA1 <= data[i + 1] <= 0xFE:
                valid_count += 1
                i += 2
                continue
            i += 1
        else:
            i += 1
    if lead_count == 0:
        return 0.0
    return valid_count / lead_count


def _score_big5(data: bytes) -> float:
    """Score data against Big5 structure.

    Lead 0xA1-0xF9; Trail 0x40-0x7E, 0xA1-0xFE
    """
    lead_count = 0
    valid_count = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if 0xA1 <= b <= 0xF9:
            lead_count += 1
            if i + 1 < length:
                trail = data[i + 1]
                if (0x40 <= trail <= 0x7E) or (0xA1 <= trail <= 0xFE):
                    valid_count += 1
                    i += 2
                    continue
            i += 1
        else:
            i += 1
    if lead_count == 0:
        return 0.0
    return valid_count / lead_count


def _score_iso_2022_jp(data: bytes) -> float:
    """Score data for ISO-2022-JP structure (escape-sequence based).

    Look for ESC sequences: ESC ( B, ESC ( J, ESC $ @, ESC $ B
    """
    esc_count = 0
    valid_count = 0
    i = 0
    length = len(data)
    while i < length:
        if data[i] == 0x1B:  # ESC
            esc_count += 1
            if i + 2 < length:
                seq = data[i + 1 : i + 3]
                if seq in (b"(B", b"(J", b"$@", b"$B"):
                    valid_count += 1
                    i += 3
                    continue
            i += 1
        else:
            i += 1
    if esc_count == 0:
        return 0.0
    return valid_count / esc_count


def _score_iso_2022_kr(data: bytes) -> float:
    """Score data for ISO-2022-KR structure (escape-sequence based).

    Designator: ESC $ ) C
    Shift-in (SI, 0x0F) and Shift-out (SO, 0x0E) toggle between ASCII and KS.
    """
    indicators = 0
    valid = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if b == 0x1B:  # ESC
            indicators += 1
            if i + 3 < length and data[i + 1 : i + 4] == b"$)C":
                valid += 1
                i += 4
                continue
            i += 1
        elif b in {0x0E, 0x0F}:  # SO / SI
            indicators += 1
            valid += 1
            i += 1
        else:
            i += 1
    if indicators == 0:
        return 0.0
    return valid / indicators


def _score_hz_gb_2312(data: bytes) -> float:
    """Score data for HZ-GB-2312 structure (tilde-escape based).

    ~{ enters GB mode, ~} leaves GB mode, ~~ is literal tilde.
    """
    tilde_count = 0
    valid_count = 0
    i = 0
    length = len(data)
    while i < length:
        if data[i] == 0x7E:  # tilde
            tilde_count += 1
            if i + 1 < length:
                follow = data[i + 1]
                if follow in (0x7B, 0x7D, 0x7E, 0x0A):
                    # ~{  ~}  ~~  ~\n
                    valid_count += 1
                    i += 2
                    continue
            i += 1
        else:
            i += 1
    if tilde_count == 0:
        return 0.0
    return valid_count / tilde_count


def _score_johab(data: bytes) -> float:
    """Score data against Johab structure.

    Lead: 0x84-0xD3, 0xD8-0xDE, 0xE0-0xF9
    Trail: 0x31-0x7E, 0x91-0xFE
    """
    lead_count = 0
    valid_count = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if (0x84 <= b <= 0xD3) or (0xD8 <= b <= 0xDE) or (0xE0 <= b <= 0xF9):
            lead_count += 1
            if i + 1 < length:
                trail = data[i + 1]
                if (0x31 <= trail <= 0x7E) or (0x91 <= trail <= 0xFE):
                    valid_count += 1
                    i += 2
                    continue
            i += 1
        else:
            i += 1
    if lead_count == 0:
        return 0.0
    return valid_count / lead_count


# ---------------------------------------------------------------------------
# Dispatch table: encoding name -> scorer function
# ---------------------------------------------------------------------------

_SCORERS: dict[str, Callable[[bytes], float]] = {
    "shift_jis": _score_shift_jis,
    "cp932": _score_shift_jis,
    "euc-jp": _score_euc_jp,
    "euc-kr": _score_euc_kr,
    "cp949": _score_euc_kr,
    "gb18030": _score_gb18030,
    "big5": _score_big5,
    "iso-2022-jp": _score_iso_2022_jp,
    "iso-2022-kr": _score_iso_2022_kr,
    "hz-gb-2312": _score_hz_gb_2312,
    "johab": _score_johab,
}


# ---------------------------------------------------------------------------
# Per-encoding multi-byte byte counters
#
# Each returns the number of non-ASCII bytes (> 0x7F) that participate in
# valid multi-byte sequences.  This is a different metric from the pair-based
# structural score: it measures what *fraction of all high bytes* are
# accounted for by the encoding's multi-byte structure.
# ---------------------------------------------------------------------------


def _mb_bytes_shift_jis(data: bytes) -> int:
    """Count non-ASCII bytes in valid Shift_JIS / CP932 multi-byte pairs."""
    mb = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xEF):
            if i + 1 < length:
                trail = data[i + 1]
                if (0x40 <= trail <= 0x7E) or (0x80 <= trail <= 0xFC):
                    # Lead is always > 0x7F; trail may or may not be
                    mb += 1
                    if trail > 0x7F:
                        mb += 1
                    i += 2
                    continue
            i += 1
        else:
            i += 1
    return mb


def _mb_bytes_euc_jp(data: bytes) -> int:
    """Count non-ASCII bytes in valid EUC-JP multi-byte sequences."""
    mb = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if b == 0x8E:
            if i + 1 < length and 0xA1 <= data[i + 1] <= 0xDF:
                mb += 2
                i += 2
                continue
            i += 1
        elif b == 0x8F:
            if (
                i + 2 < length
                and 0xA1 <= data[i + 1] <= 0xFE
                and 0xA1 <= data[i + 2] <= 0xFE
            ):
                mb += 3
                i += 3
                continue
            i += 1
        elif 0xA1 <= b <= 0xFE:
            if i + 1 < length and 0xA1 <= data[i + 1] <= 0xFE:
                mb += 2
                i += 2
                continue
            i += 1
        else:
            i += 1
    return mb


def _mb_bytes_euc_kr(data: bytes) -> int:
    """Count non-ASCII bytes in valid EUC-KR / CP949 multi-byte pairs."""
    mb = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if 0xA1 <= b <= 0xFE:
            if i + 1 < length and 0xA1 <= data[i + 1] <= 0xFE:
                mb += 2
                i += 2
                continue
            i += 1
        else:
            i += 1
    return mb


def _mb_bytes_gb18030(data: bytes) -> int:
    """Count non-ASCII bytes in valid GB18030 / GB2312 multi-byte sequences."""
    mb = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if 0x81 <= b <= 0xFE:
            # 4-byte GB18030: bytes 0 and 2 are > 0x7F
            if (
                i + 3 < length
                and 0x30 <= data[i + 1] <= 0x39
                and 0x81 <= data[i + 2] <= 0xFE
                and 0x30 <= data[i + 3] <= 0x39
            ):
                mb += 2  # bytes 0 and 2 are non-ASCII
                i += 4
                continue
            # 2-byte GB2312: both bytes are > 0x7F
            if 0xA1 <= b <= 0xF7 and i + 1 < length and 0xA1 <= data[i + 1] <= 0xFE:
                mb += 2
                i += 2
                continue
            i += 1
        else:
            i += 1
    return mb


def _mb_bytes_big5(data: bytes) -> int:
    """Count non-ASCII bytes in valid Big5 multi-byte pairs."""
    mb = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if 0xA1 <= b <= 0xF9:
            if i + 1 < length:
                trail = data[i + 1]
                if (0x40 <= trail <= 0x7E) or (0xA1 <= trail <= 0xFE):
                    # Lead is always > 0x7F; trail may or may not be
                    mb += 1
                    if trail > 0x7F:
                        mb += 1
                    i += 2
                    continue
            i += 1
        else:
            i += 1
    return mb


def _mb_bytes_johab(data: bytes) -> int:
    """Count non-ASCII bytes in valid Johab multi-byte pairs."""
    mb = 0
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if (0x84 <= b <= 0xD3) or (0xD8 <= b <= 0xDE) or (0xE0 <= b <= 0xF9):
            if i + 1 < length:
                trail = data[i + 1]
                if (0x31 <= trail <= 0x7E) or (0x91 <= trail <= 0xFE):
                    if b > 0x7F:
                        mb += 1
                    if trail > 0x7F:
                        mb += 1
                    i += 2
                    continue
            i += 1
        else:
            i += 1
    return mb


_MB_BYTE_COUNTERS: dict[str, Callable[[bytes], int]] = {
    "shift_jis": _mb_bytes_shift_jis,
    "cp932": _mb_bytes_shift_jis,
    "euc-jp": _mb_bytes_euc_jp,
    "euc-kr": _mb_bytes_euc_kr,
    "cp949": _mb_bytes_euc_kr,
    "gb18030": _mb_bytes_gb18030,
    "big5": _mb_bytes_big5,
    "johab": _mb_bytes_johab,
}


# ---------------------------------------------------------------------------
# Per-encoding lead byte diversity counters
#
# Each returns the number of *distinct* lead byte values that participate in
# valid multi-byte sequences.  Genuine CJK text draws from a wide repertoire
# (many distinct lead bytes); European false positives cluster in a narrow
# band (e.g. 0xC0-0xDF for accented Latin characters).
# ---------------------------------------------------------------------------


def _lead_diversity_shift_jis(data: bytes) -> int:
    """Count distinct lead bytes in valid Shift-JIS pairs."""
    leads: set[int] = set()
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xEF):
            if i + 1 < length:
                trail = data[i + 1]
                if (0x40 <= trail <= 0x7E) or (0x80 <= trail <= 0xFC):
                    leads.add(b)
                    i += 2
                    continue
            i += 1
        else:
            i += 1
    return len(leads)


def _lead_diversity_euc_jp(data: bytes) -> int:
    """Count distinct lead bytes in valid EUC-JP pairs."""
    leads: set[int] = set()
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if b == 0x8E:
            # SS2 sequence
            if i + 1 < length and 0xA1 <= data[i + 1] <= 0xDF:
                leads.add(b)
                i += 2
                continue
            i += 1
        elif b == 0x8F:
            # SS3 sequence
            if (
                i + 2 < length
                and 0xA1 <= data[i + 1] <= 0xFE
                and 0xA1 <= data[i + 2] <= 0xFE
            ):
                leads.add(b)
                i += 3
                continue
            i += 1
        elif 0xA1 <= b <= 0xFE:
            if i + 1 < length and 0xA1 <= data[i + 1] <= 0xFE:
                leads.add(b)
                i += 2
                continue
            i += 1
        else:
            i += 1
    return len(leads)


def _lead_diversity_euc_kr(data: bytes) -> int:
    """Count distinct lead bytes in valid EUC-KR pairs."""
    leads: set[int] = set()
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if 0xA1 <= b <= 0xFE:
            if i + 1 < length and 0xA1 <= data[i + 1] <= 0xFE:
                leads.add(b)
                i += 2
                continue
            i += 1
        else:
            i += 1
    return len(leads)


def _lead_diversity_gb18030(data: bytes) -> int:
    """Count distinct lead bytes in valid GB18030 pairs."""
    leads: set[int] = set()
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if 0x81 <= b <= 0xFE:
            # 4-byte GB18030
            if (
                i + 3 < length
                and 0x30 <= data[i + 1] <= 0x39
                and 0x81 <= data[i + 2] <= 0xFE
                and 0x30 <= data[i + 3] <= 0x39
            ):
                leads.add(b)
                i += 4
                continue
            # 2-byte GB2312
            if 0xA1 <= b <= 0xF7 and i + 1 < length and 0xA1 <= data[i + 1] <= 0xFE:
                leads.add(b)
                i += 2
                continue
            i += 1
        else:
            i += 1
    return len(leads)


def _lead_diversity_big5(data: bytes) -> int:
    """Count distinct lead bytes in valid Big5 pairs."""
    leads: set[int] = set()
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if 0xA1 <= b <= 0xF9:
            if i + 1 < length:
                trail = data[i + 1]
                if (0x40 <= trail <= 0x7E) or (0xA1 <= trail <= 0xFE):
                    leads.add(b)
                    i += 2
                    continue
            i += 1
        else:
            i += 1
    return len(leads)


def _lead_diversity_johab(data: bytes) -> int:
    """Count distinct lead bytes in valid Johab pairs."""
    leads: set[int] = set()
    i = 0
    length = len(data)
    while i < length:
        b = data[i]
        if (0x84 <= b <= 0xD3) or (0xD8 <= b <= 0xDE) or (0xE0 <= b <= 0xF9):
            if i + 1 < length:
                trail = data[i + 1]
                if (0x31 <= trail <= 0x7E) or (0x91 <= trail <= 0xFE):
                    leads.add(b)
                    i += 2
                    continue
            i += 1
        else:
            i += 1
    return len(leads)


_LEAD_BYTE_DIVERSITY_COUNTERS: dict[str, Callable[[bytes], int]] = {
    "shift_jis": _lead_diversity_shift_jis,
    "cp932": _lead_diversity_shift_jis,
    "euc-jp": _lead_diversity_euc_jp,
    "euc-kr": _lead_diversity_euc_kr,
    "cp949": _lead_diversity_euc_kr,
    "gb18030": _lead_diversity_gb18030,
    "big5": _lead_diversity_big5,
    "johab": _lead_diversity_johab,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_structural_score(data: bytes, encoding_info: EncodingInfo) -> float:
    """Return 0.0-1.0 indicating how well *data* matches the encoding's structure.

    For single-byte encodings (``is_multibyte is False``), always returns 0.0.
    For empty data, always returns 0.0.
    """
    if not data or not encoding_info.is_multibyte:
        return 0.0

    scorer = _SCORERS.get(encoding_info.name)
    if scorer is None:
        return 0.0

    return scorer(data)


def compute_multibyte_byte_coverage(data: bytes, encoding_info: EncodingInfo) -> float:
    """Ratio of non-ASCII bytes that participate in valid multi-byte sequences.

    Genuine CJK text has nearly all non-ASCII bytes paired into valid
    multi-byte sequences (coverage close to 1.0), while Latin text with
    scattered high bytes has many "orphan" bytes that don't form valid pairs
    (coverage well below 1.0).

    Returns 0.0 for single-byte encodings, empty data, or data with no
    non-ASCII bytes.
    """
    if not data or not encoding_info.is_multibyte:
        return 0.0

    counter = _MB_BYTE_COUNTERS.get(encoding_info.name)
    if counter is None:
        return 0.0

    non_ascii = 0
    for b in data:
        if b > 0x7F:
            non_ascii += 1

    if non_ascii == 0:
        return 0.0

    mb_bytes = counter(data)
    return mb_bytes / non_ascii


def compute_lead_byte_diversity(data: bytes, encoding_info: EncodingInfo) -> int:
    """Count distinct lead byte values in valid multi-byte pairs.

    Genuine CJK text uses lead bytes from across the encoding's full
    repertoire.  European text falsely matching a CJK structural scorer
    clusters lead bytes in a narrow band (e.g. 0xC0-0xDF for accented
    Latin characters).
    """
    if not data or not encoding_info.is_multibyte:
        return 0
    counter = _LEAD_BYTE_DIVERSITY_COUNTERS.get(encoding_info.name)
    if counter is None:
        return 256  # Unknown encoding -- don't gate
    return counter(data)
