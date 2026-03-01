# tests/test_escape.py
"""Tests for escape-sequence-based encoding detection."""

from __future__ import annotations

from chardet.pipeline.escape import detect_escape_encoding


def test_iso_2022_jp_esc_dollar_b() -> None:
    data = b"Hello \x1b$B$3$s$K$A$O\x1b(B World"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso-2022-jp"
    assert result.confidence == 0.95


def test_iso_2022_jp_esc_dollar_at() -> None:
    data = b"Hello \x1b$@$3$s$K$A$O\x1b(B World"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso-2022-jp"


def test_iso_2022_kr() -> None:
    data = b"\x1b$)C\x0e\x21\x21\x0f"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso-2022-kr"
    assert result.confidence == 0.95


def test_hz_gb_2312() -> None:
    data = b"Hello ~{CEDE~} World"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "hz-gb-2312"
    assert result.confidence == 0.95


def test_hz_gb_2312_needs_both_markers() -> None:
    # Only shift-in without shift-out should not match
    data = b"Hello ~{CEDE World"
    result = detect_escape_encoding(data)
    assert result is None


def test_hz_gb_2312_rejects_english_with_tildes() -> None:
    # English text containing ~{ and ~} must NOT be detected as HZ-GB-2312
    data = b"The formula ~{x + y~} is simple."
    result = detect_escape_encoding(data)
    assert result is None


def test_hz_gb_2312_rejects_odd_length_region() -> None:
    # Odd-length region between markers is not valid GB2312 pairs
    data = b"~{ABC~}"
    result = detect_escape_encoding(data)
    assert result is None


def test_hz_gb_2312_rejects_empty_region() -> None:
    data = b"~{~}"
    result = detect_escape_encoding(data)
    assert result is None


def test_hz_gb_2312_rejects_bytes_outside_range() -> None:
    # Bytes outside 0x21-0x7E (e.g., space 0x20) are not valid GB2312
    data = b"~{ a ~}"
    result = detect_escape_encoding(data)
    assert result is None


def test_plain_ascii_returns_none() -> None:
    data = b"Hello World"
    result = detect_escape_encoding(data)
    assert result is None


def test_random_bytes_returns_none() -> None:
    data = bytes(range(256))
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_basic() -> None:
    # "Hello, 世界" encoded as UTF-7
    data = "Hello, 世界".encode("utf-7")
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "utf-7"
    assert result.confidence == 0.95


def test_utf7_shifted_sequence() -> None:
    # UTF-7 with explicit +<Base64>- regions
    data = b"Hello +AGkAbgB0AGUAbgBzAGU-"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "utf-7"


def test_utf7_literal_plus() -> None:
    # +- is the UTF-7 escape for literal '+', not a shifted sequence
    data = b"2+- 2 = 4"
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_plain_ascii_with_plus() -> None:
    # A stray + in ASCII text should not trigger UTF-7 detection
    data = b"C++ is a programming language"
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_empty_shift() -> None:
    # +- followed by nothing is just a literal plus, not UTF-7
    data = b"price: 10+- tax"
    result = detect_escape_encoding(data)
    assert result is None
