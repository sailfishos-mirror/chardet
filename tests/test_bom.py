# tests/test_bom.py
from chardet.pipeline import DetectionResult
from chardet.pipeline.bom import detect_bom


def test_utf8_bom():
    data = b"\xef\xbb\xbfHello"
    result = detect_bom(data)
    assert result == DetectionResult("utf-8-sig", 1.0, None)


def test_utf16_le_bom():
    data = b"\xff\xfeH\x00e\x00l\x00l\x00o\x00"
    result = detect_bom(data)
    assert result == DetectionResult("utf-16-le", 1.0, None)


def test_utf16_be_bom():
    data = b"\xfe\xff\x00H\x00e\x00l\x00l\x00o"
    result = detect_bom(data)
    assert result == DetectionResult("utf-16-be", 1.0, None)


def test_utf32_le_bom():
    data = b"\xff\xfe\x00\x00" + b"\x48\x00\x00\x00"
    result = detect_bom(data)
    assert result == DetectionResult("utf-32-le", 1.0, None)


def test_utf32_be_bom():
    data = b"\x00\x00\xfe\xff" + b"\x00\x00\x00\x48"
    result = detect_bom(data)
    assert result == DetectionResult("utf-32-be", 1.0, None)


def test_no_bom():
    data = b"Hello, world!"
    result = detect_bom(data)
    assert result is None


def test_empty_input():
    assert detect_bom(b"") is None


def test_too_short_for_bom():
    assert detect_bom(b"\xef") is None
    assert detect_bom(b"\xef\xbb") is None


def test_utf32_le_checked_before_utf16_le():
    # UTF-32-LE BOM starts with \xff\xfe (same as UTF-16-LE) but has \x00\x00 after
    data = b"\xff\xfe\x00\x00" + b"\x48\x00\x00\x00"
    result = detect_bom(data)
    assert result is not None
    assert result.encoding == "utf-32-le"
