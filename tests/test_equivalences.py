# tests/test_equivalences.py
from chardet.equivalences import is_equivalent_detection


def test_identical_decode_returns_true():
    """Pure ASCII data decoded as 'ascii' vs 'utf-8' is identical."""
    data = b"Hello, world!"
    assert is_equivalent_detection(data, "ascii", "utf-8") is True


def test_base_letter_match_returns_true():
    """Byte 0xC3 is A-tilde in iso-8859-1, A-breve in iso-8859-2.

    Both decompose to base letter 'A' after NFKD + strip combining.
    """
    data = b"\xc3"
    assert is_equivalent_detection(data, "iso-8859-1", "iso-8859-2") is True


def test_completely_different_decode_returns_false():
    """Latin accented letters vs Cyrillic letters have different base letters."""
    data = b"\xc0\xc1\xc2\xc3\xc4"
    assert is_equivalent_detection(data, "iso-8859-1", "iso-8859-5") is False


def test_none_detected_returns_false():
    """None detected encoding always returns False."""
    assert is_equivalent_detection(b"Hello", "utf-8", None) is False


def test_decode_error_returns_false():
    """Invalid bytes for the encoding cause decode failure -> False."""
    # 0x81 is not a valid lead byte in utf-8 by itself
    data = b"\x81\x82\x83"
    assert is_equivalent_detection(data, "iso-8859-1", "utf-8") is False


def test_empty_data_returns_true():
    """Empty bytes decode to empty string in any encoding -> identical."""
    assert is_equivalent_detection(b"", "utf-8", "iso-8859-1") is True


def test_ebcdic_pair_decodes_identically():
    """cp037 and cp500 decode 'Hello' bytes identically."""
    data = "Hello".encode("cp037")
    assert is_equivalent_detection(data, "cp037", "cp500") is True


def test_normalized_name_match_returns_true():
    """Encoding names that normalize to the same codec are considered equal."""
    data = b"Hello"
    assert is_equivalent_detection(data, "UTF-8", "utf8") is True


def test_unknown_encoding_returns_false():
    """Bogus encoding name that cannot be looked up returns False."""
    data = b"Hello"
    assert is_equivalent_detection(data, "utf-8", "not-a-real-encoding") is False


def test_currency_vs_euro_sign_accepted():
    """¤ (currency sign) vs € (euro sign) is an accepted symbol equivalence."""
    data = b"\xa4"
    assert is_equivalent_detection(data, "iso-8859-1", "iso-8859-15") is True


def test_symbol_vs_letter_difference_returns_false():
    """Symbol in one encoding vs letter in another should fail."""
    # 0xD7 = multiplication sign in iso-8859-1, Cyrillic letter in iso-8859-5
    data = b"\xd7"
    assert is_equivalent_detection(data, "iso-8859-1", "iso-8859-5") is False
