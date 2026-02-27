# tests/test_orchestrator.py
from chardet.enums import EncodingEra
from chardet.pipeline import DetectionResult
from chardet.pipeline.orchestrator import run_pipeline


def test_empty_input():
    result = run_pipeline(b"", EncodingEra.MODERN_WEB)
    assert result == [DetectionResult("utf-8", 0.10, None)]


def test_bom_detected():
    data = b"\xef\xbb\xbfHello"
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "utf-8-sig"
    assert result[0].confidence == 1.0


def test_bom_utf16_le():
    data = b"\xff\xfe" + "Hello world".encode("utf-16-le")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "utf-16-le"
    assert result[0].confidence == 1.0


def test_bom_utf16_be():
    data = b"\xfe\xff" + "Hello world".encode("utf-16-be")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "utf-16-be"
    assert result[0].confidence == 1.0


def test_bom_utf32_le():
    data = b"\xff\xfe\x00\x00" + "Hello world".encode("utf-32-le")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "utf-32-le"
    assert result[0].confidence == 1.0


def test_bom_utf32_be():
    data = b"\x00\x00\xfe\xff" + "Hello world".encode("utf-32-be")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "utf-32-be"
    assert result[0].confidence == 1.0


def test_utf16_le_no_bom():
    """UTF-16-LE without a BOM should be detected via null-byte patterns."""
    data = "Hello world, this is a test of UTF-16 detection.".encode("utf-16-le")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "utf-16-le"
    assert result[0].confidence == 0.95


def test_utf16_be_no_bom():
    """UTF-16-BE without a BOM should be detected via null-byte patterns."""
    data = "Hello world, this is a test of UTF-16 detection.".encode("utf-16-be")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "utf-16-be"
    assert result[0].confidence == 0.95


def test_utf32_le_no_bom():
    """UTF-32-LE without a BOM should be detected via null-byte patterns."""
    data = "Hello world, this is a test.".encode("utf-32-le")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "utf-32-le"
    assert result[0].confidence == 0.95


def test_utf32_be_no_bom():
    """UTF-32-BE without a BOM should be detected via null-byte patterns."""
    data = "Hello world, this is a test.".encode("utf-32-be")
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "utf-32-be"
    assert result[0].confidence == 0.95


def test_pure_ascii():
    result = run_pipeline(b"Hello world 123", EncodingEra.ALL)
    assert result[0].encoding == "ascii"
    assert result[0].confidence == 1.0


def test_utf8_multibyte():
    data = "Héllo wörld café".encode()
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "utf-8"
    assert result[0].confidence >= 0.9


def test_binary_content():
    data = b"\x00\x01\x02\x03\x04\x05" * 100
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding is None
    assert result[0].confidence == 0.95


def test_xml_charset_declaration():
    data = b'<?xml version="1.0" encoding="iso-8859-1"?><root>Hello</root>'
    result = run_pipeline(data, EncodingEra.ALL)
    assert result[0].encoding == "iso-8859-1"


def test_max_bytes_truncation():
    data = b"Hello" * 100_000
    result = run_pipeline(data, EncodingEra.ALL, max_bytes=100)
    assert result[0] is not None


def test_returns_list():
    result = run_pipeline(b"Hello", EncodingEra.ALL)
    assert isinstance(result, list)
    assert all(isinstance(r, DetectionResult) for r in result)


def test_single_high_byte_returns_encoding():
    """A single high byte should return an encoding, not None."""
    result = run_pipeline(b"\xe4", EncodingEra.MODERN_WEB)
    assert result[0].encoding is not None


def test_encoding_era_filtering():
    data = b"Hello world"
    for era in EncodingEra:
        result = run_pipeline(data, era)
        assert len(result) >= 1
