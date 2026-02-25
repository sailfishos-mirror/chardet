# tests/test_binary.py
from chardet.pipeline.binary import is_binary


def test_empty_input_is_not_binary():
    assert is_binary(b"") is False


def test_plain_ascii_is_not_binary():
    assert is_binary(b"Hello, world!") is False


def test_text_with_newlines_tabs_is_not_binary():
    assert is_binary(b"Hello\n\tworld\r\n") is False


def test_all_null_bytes_is_binary():
    assert is_binary(b"\x00" * 100) is True


def test_high_null_concentration_is_binary():
    # >1% null bytes
    data = b"Hello" + b"\x00" * 10 + b"world" * 10
    assert is_binary(data) is True


def test_single_null_in_large_text_is_not_binary():
    # <1% null bytes
    data = b"a" * 500 + b"\x00" + b"b" * 500
    assert is_binary(data) is False


def test_control_characters_indicate_binary():
    # Bytes 0x01-0x08, 0x0E-0x1F (excluding \t=0x09, \n=0x0A, \r=0x0D)
    data = b"\x01\x02\x03\x04\x05\x06\x07\x08" * 20
    assert is_binary(data) is True


def test_few_control_chars_in_large_text_is_not_binary():
    data = b"Normal text " * 100 + b"\x01"
    assert is_binary(data) is False


def test_jpeg_header_is_binary():
    jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 50 + bytes(range(256))
    assert is_binary(jpeg) is True


def test_utf8_text_is_not_binary():
    assert is_binary("Héllo wörld".encode()) is False


def test_max_bytes_respected():
    # Binary content after max_bytes should be ignored
    text = b"clean text " * 100
    binary_tail = b"\x00" * 1000
    assert is_binary(text + binary_tail, max_bytes=len(text)) is False
