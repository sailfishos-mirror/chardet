# tests/test_detector.py
import pytest

from chardet.detector import UniversalDetector
from chardet.enums import EncodingEra


def test_basic_lifecycle():
    detector = UniversalDetector()
    detector.feed(b"Hello world")
    detector.close()
    result = detector.result
    assert result["encoding"] is not None


def test_result_before_close():
    detector = UniversalDetector()
    detector.feed(b"Hello world")
    result = detector.result
    assert "encoding" in result
    assert "confidence" in result
    assert "language" in result


def test_reset():
    detector = UniversalDetector()
    detector.feed(b"Hello world")
    detector.close()
    detector.reset()
    result = detector.result
    assert result["encoding"] is None
    assert result["confidence"] == 0.0


def test_done_property():
    detector = UniversalDetector()
    assert detector.done is False


def test_done_after_bom():
    detector = UniversalDetector()
    detector.feed(b"\xef\xbb\xbfHello")
    assert detector.done is True
    assert detector.result["encoding"] == "utf-8-sig"


def test_feed_after_close_raises():
    detector = UniversalDetector()
    detector.feed(b"Hello")
    detector.close()
    with pytest.raises(ValueError):
        detector.feed(b"more data")


def test_feed_after_done_is_ignored():
    detector = UniversalDetector()
    detector.feed(b"\xef\xbb\xbfHello")
    assert detector.done is True
    detector.feed(b"more data")  # Should not raise


def test_multiple_feeds():
    detector = UniversalDetector()
    data = "Héllo wörld café".encode()
    chunk_size = 5
    for i in range(0, len(data), chunk_size):
        detector.feed(data[i : i + chunk_size])
    detector.close()
    assert detector.result["encoding"] is not None


def test_done_after_ascii_feed():
    """feed() should set done=True for pure ASCII after enough data."""
    detector = UniversalDetector()
    detector.feed(b"Hello world, this is enough ASCII data for detection. " * 2)
    assert detector.done is True
    assert detector.result["encoding"] == "ascii"


def test_done_after_utf8_feed():
    """feed() should set done=True for valid UTF-8 with multibyte chars."""
    detector = UniversalDetector()
    data = "Héllo wörld café résumé naïve über".encode()
    detector.feed(data * 2)
    assert detector.done is True
    assert detector.result["encoding"] == "utf-8"


def test_done_after_escape_feed():
    """feed() should set done=True for ISO-2022-JP escape sequences."""
    detector = UniversalDetector()
    data = b"Hello \x1b$B$3$s$K$A$O\x1b(B World" + b" " * 64
    detector.feed(data)
    assert detector.done is True
    assert detector.result["encoding"] == "iso-2022-jp"


def test_incremental_ascii_not_premature():
    """feed() should not set done for ASCII with too little data."""
    detector = UniversalDetector()
    detector.feed(b"Hi")
    assert detector.done is False


def test_encoding_era_parameter():
    detector = UniversalDetector(encoding_era=EncodingEra.MODERN_WEB)
    detector.feed(b"Hello world")
    detector.close()
    assert detector.result is not None


def test_max_bytes_parameter():
    detector = UniversalDetector(max_bytes=100)
    detector.feed(b"x" * 200)
    detector.close()
    assert detector.result is not None


def test_max_bytes_zero_raises():
    with pytest.raises(ValueError, match="max_bytes"):
        UniversalDetector(max_bytes=0)


def test_max_bytes_negative_raises():
    with pytest.raises(ValueError, match="max_bytes"):
        UniversalDetector(max_bytes=-1)


def test_close_idempotent():
    detector = UniversalDetector()
    detector.feed(b"Hello world, this is enough text. " * 3)
    result1 = detector.close()
    result2 = detector.close()
    assert result1 == result2


def test_reset_allows_new_detection():
    detector = UniversalDetector()
    detector.feed(b"\xef\xbb\xbfHello")
    detector.close()
    assert detector.result["encoding"] == "utf-8-sig"

    detector.reset()
    detector.feed("Héllo wörld café".encode())
    detector.close()
    assert detector.result["encoding"] == "utf-8"
