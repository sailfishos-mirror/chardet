# tests/test_escape.py
"""Tests for escape-sequence-based encoding detection."""

from __future__ import annotations

from chardet.pipeline.escape import detect_escape_encoding


def test_iso_2022_jp_esc_dollar_b() -> None:
    data = b"Hello \x1b$B$3$s$K$A$O\x1b(B World"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso2022-jp-2"
    assert result.confidence == 0.95


def test_iso_2022_jp_esc_dollar_at() -> None:
    data = b"Hello \x1b$@$3$s$K$A$O\x1b(B World"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso2022-jp-2"


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


def test_utf7_rejects_url_with_plus() -> None:
    data = b"https://www.google.com/search?q=hello+ABC-DEF"
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_rejects_short_base64_in_text() -> None:
    data = b"x+ABC-y"
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_rejects_mime_boundary() -> None:
    data = b"--boundary+ABCdef123-end"
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_rejects_cpp_version() -> None:
    """C++20, C++11, etc. should not trigger UTF-7 (Guard A)."""
    data = b"#include <ranges>  // C++20 feature\nint main() { return 0; }\n"
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_rejects_pem_base64() -> None:
    """PEM certificate base64 blobs should not trigger UTF-7 (Guard B)."""
    data = (
        b"-----BEGIN CERTIFICATE-----\n"
        b"MIICpDCCAYwCCQDU+pQ4pHgSpDANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAls\n"
        b"b2NhbGhvc3QwHhcNMjMwNTI5MTI0ODQ3WhcNMjQwNTI4MTI0ODQ3WjAUMRIwEAYD\n"
        b"VQQDDAlsb2NhbGhvc3QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC+\n"
        b"7e1RRz+BI/kHMBbOz+FN5bEwMmJ2KKQGXN+yTDaj8bKRMqgJ7MJifi3eFmFnqYg\n"
        b"-----END CERTIFICATE-----\n"
    )
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_multi_paragraph_document() -> None:
    """A longer UTF-7 document with multiple shifted sequences must still be detected."""
    parts = [
        "From: sender@example.com\r\n",
        "Subject: Meeting notes\r\n",
        "\r\n",
        "Meeting at 3pm.\r\n",
        "Topic: 日本語テスト.\r\n",
        "Attendees: Müller, René, 田中.\r\n",
        "\r\n",
        "Please review the 資料 before Thursday.\r\n",
        "Best regards,\r\n",
        "André\r\n",
    ]
    data = "".join(parts).encode("utf-7")
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "utf-7"


def test_utf7_mixed_ascii_and_shifted() -> None:
    """UTF-7 with interspersed ASCII and shifted blocks must be detected."""
    # Multiple short non-ASCII words spread across ASCII text
    text = "Price: 100€, shipping to München, estimated 3-5 days. Sincerely, José."
    data = text.encode("utf-7")
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "utf-7"


def test_utf7_consecutive_shifted_sequences() -> None:
    """Back-to-back shifted sequences (common in CJK text) must be detected."""
    text = "これはテストです"  # All non-ASCII
    data = text.encode("utf-7")
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "utf-7"


def test_iso2022_jp_base_returns_jp2() -> None:
    """Base ISO-2022-JP escape codes should default to iso2022-jp-2 (broadest)."""
    data = b"Hello \x1b$B$3$s$K$A$O\x1b(B World"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso2022-jp-2"


def test_iso2022_jp_2004_codes() -> None:
    """JIS X 0213 escape codes should return iso2022-jp-2004."""
    # ESC $ ( O designates JIS X 0213 plane 1
    data = b"\x1b$B$3$s\x1b(B\x1b$(O\x21\x21\x1b(B"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso2022-jp-2004"


def test_iso2022_jp_ext_codes() -> None:
    """Half-width katakana SI/SO should return iso2022-jp-ext."""
    # ESC $ B for JIS X 0208, then SI (0x0E) / SO (0x0F) for half-width katakana
    data = b"\x1b$B$3$s\x1b(B\x0e\xb1\xb2\x0f"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "iso2022-jp-ext"


def test_hz_close_marker_before_open_marker() -> None:
    """When ~} appears before ~{ but a valid region follows, HZ is still detected."""
    data = b"prefix ~} text ~{CEDE~}"
    result = detect_escape_encoding(data)
    assert result is not None
    assert result.encoding == "hz-gb-2312"


def test_hz_only_close_before_open() -> None:
    """Data where ~} only appears before ~{ — no valid HZ region."""
    data = b"~} some text ~{ invalid"
    result = detect_escape_encoding(data)
    assert result is None


def test_utf7_short_base64_rejected() -> None:
    """UTF-7 shifted sequence with fewer than 3 base64 chars is rejected."""
    data = b"text +AB- more text"
    result = detect_escape_encoding(data)
    assert result is None
