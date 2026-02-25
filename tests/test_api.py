# tests/test_api.py
import chardet
from chardet.enums import EncodingEra


def test_detect_returns_dict():
    result = chardet.detect(b"Hello world")
    assert isinstance(result, dict)
    assert "encoding" in result
    assert "confidence" in result
    assert "language" in result


def test_detect_ascii():
    result = chardet.detect(b"Hello world")
    assert result["encoding"] == "ascii"
    assert result["confidence"] == 1.0


def test_detect_utf8_bom():
    result = chardet.detect(b"\xef\xbb\xbfHello")
    assert result["encoding"] == "utf-8-sig"


def test_detect_utf8_multibyte():
    data = "Héllo wörld café".encode()
    result = chardet.detect(data)
    assert result["encoding"] == "utf-8"


def test_detect_empty():
    result = chardet.detect(b"")
    assert result["encoding"] == "windows-1252"
    assert result["confidence"] == 0.10


def test_detect_with_encoding_era():
    data = b"Hello world"
    result = chardet.detect(data, encoding_era=EncodingEra.MODERN_WEB)
    assert result["encoding"] is not None


def test_detect_with_max_bytes():
    data = b"Hello world" * 100_000
    result = chardet.detect(data, max_bytes=100)
    assert result is not None


def test_detect_all_returns_list():
    result = chardet.detect_all(b"Hello world")
    assert isinstance(result, list)
    assert len(result) >= 1


def test_detect_all_sorted_by_confidence():
    data = "Héllo wörld".encode()
    results = chardet.detect_all(data)
    confidences = [r["confidence"] for r in results]
    assert confidences == sorted(confidences, reverse=True)


def test_detect_all_each_is_dict():
    results = chardet.detect_all(b"Hello world")
    for r in results:
        assert "encoding" in r
        assert "confidence" in r
        assert "language" in r


def test_version_exists():
    assert hasattr(chardet, "__version__")
    assert isinstance(chardet.__version__, str)
    assert chardet.__version__ == "6.1.0"
