# tests/test_benchmark.py
"""Performance regression tests. Run with: ``pytest -m benchmark``."""

import time

import pytest

import chardet

pytestmark = pytest.mark.benchmark


def test_ascii_detection_speed():
    data = b"Hello world, this is a plain ASCII text." * 100
    start = time.perf_counter()
    for _ in range(1000):
        chardet.detect(data)
    elapsed = time.perf_counter() - start
    per_call_ms = (elapsed / 1000) * 1000
    assert per_call_ms < 1.0, f"ASCII detection too slow: {per_call_ms:.2f}ms"


def test_utf8_detection_speed():
    data = "Héllo wörld café résumé naïve".encode() * 100
    start = time.perf_counter()
    for _ in range(1000):
        chardet.detect(data)
    elapsed = time.perf_counter() - start
    per_call_ms = (elapsed / 1000) * 1000
    assert per_call_ms < 5.0, f"UTF-8 detection too slow: {per_call_ms:.2f}ms"


def test_bom_detection_speed():
    data = b"\xef\xbb\xbfHello world" * 100
    start = time.perf_counter()
    for _ in range(1000):
        chardet.detect(data)
    elapsed = time.perf_counter() - start
    per_call_ms = (elapsed / 1000) * 1000
    assert per_call_ms < 1.0, f"BOM detection too slow: {per_call_ms:.2f}ms"
