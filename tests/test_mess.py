"""Tests for post-decode mess detection."""

from chardet.pipeline.mess import compute_mess_score


def test_clean_ascii_text():
    """Pure ASCII text should have zero mess."""
    assert compute_mess_score("Hello, world! This is clean text.") == 0.0


def test_clean_accented_text():
    """Normal French text with accents should have low mess."""
    assert compute_mess_score("Café résumé naïve") < 0.1


def test_unprintable_characters():
    """Text with C0/C1 control characters should have high mess."""
    text = "Hello\x01\x02\x03world"
    assert compute_mess_score(text) > 0.2


def test_excessive_accents():
    """More than 40% accented alphabetic chars is suspicious."""
    text = "àéîõüàéîõü" * 10 + "abc"
    score = compute_mess_score(text)
    assert score > 0.1


def test_empty_string():
    assert compute_mess_score("") == 0.0
