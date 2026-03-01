# tests/test_api.py
from __future__ import annotations

import warnings

import pytest

import chardet
from chardet.enums import EncodingEra, LanguageFilter


def test_detect_returns_dict():
    result = chardet.detect(b"Hello world")
    assert isinstance(result, dict)
    assert "encoding" in result
    assert "confidence" in result
    assert "language" in result


def test_detect_ascii():
    result = chardet.detect(b"Hello world")
    # Default encoding_era=MODERN_WEB resolves should_rename_legacy to True,
    # so ascii is reported as its superset Windows-1252.
    assert result["encoding"] == "Windows-1252"
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
    assert result["encoding"] == "utf-8"
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


# --- should_rename_legacy tests ---


def test_rename_legacy_default_modern_web():
    """Default (None) with MODERN_WEB era renames ascii to Windows-1252."""
    result = chardet.detect(b"Hello world")
    assert result["encoding"] == "Windows-1252"


def test_rename_legacy_false():
    """Explicit False returns the raw encoding name."""
    result = chardet.detect(b"Hello world", should_rename_legacy=False)
    assert result["encoding"] == "ascii"


def test_rename_legacy_true():
    """Explicit True renames regardless of era."""
    result = chardet.detect(
        b"Hello world",
        should_rename_legacy=True,
        encoding_era=EncodingEra.ALL,
    )
    assert result["encoding"] == "Windows-1252"


def test_rename_legacy_none_non_modern_era():
    """None with non-MODERN_WEB era does not rename."""
    result = chardet.detect(b"Hello world", encoding_era=EncodingEra.ALL)
    assert result["encoding"] == "ascii"


def test_rename_legacy_detect_all():
    """should_rename_legacy applies to detect_all() results too."""
    results = chardet.detect_all(b"Hello world", should_rename_legacy=True)
    assert results[0]["encoding"] == "Windows-1252"


def test_rename_legacy_detector():
    """UniversalDetector applies rename on close()."""
    from chardet.detector import UniversalDetector

    det = UniversalDetector(should_rename_legacy=True)
    det.feed(b"Hello world, this is enough ASCII data for detection. " * 2)
    det.close()
    assert det.result["encoding"] == "Windows-1252"


def test_rename_legacy_detector_false():
    """UniversalDetector with False returns raw name."""
    from chardet.detector import UniversalDetector

    det = UniversalDetector(should_rename_legacy=False)
    det.feed(b"Hello world, this is enough ASCII data for detection. " * 2)
    det.close()
    assert det.result["encoding"] == "ascii"


# --- ignore_threshold tests ---


def test_ignore_threshold_false_filters():
    """Default ignore_threshold=False filters low-confidence results."""
    data = "Héllo wörld café résumé".encode()
    results_all = chardet.detect_all(data, ignore_threshold=True)
    results_filtered = chardet.detect_all(data, ignore_threshold=False)
    assert len(results_filtered) <= len(results_all)
    for r in results_filtered:
        assert r["confidence"] > 0.20


def test_ignore_threshold_true_returns_all():
    """ignore_threshold=True returns all candidates."""
    data = "Héllo wörld café résumé".encode()
    results = chardet.detect_all(data, ignore_threshold=True)
    assert len(results) >= 1


def test_ignore_threshold_fallback():
    """If all results filtered, fall back to top result."""
    results = chardet.detect_all(b"", ignore_threshold=False)
    assert len(results) >= 1


# --- lang_filter DeprecationWarning test ---


def test_lang_filter_warning():
    """Non-ALL lang_filter emits DeprecationWarning."""
    from chardet.detector import UniversalDetector

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        UniversalDetector(lang_filter=LanguageFilter.CJK)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "lang_filter" in str(w[0].message)


def test_lang_filter_all_no_warning():
    """ALL lang_filter does not warn."""
    from chardet.detector import UniversalDetector

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        UniversalDetector(lang_filter=LanguageFilter.ALL)
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 0


# --- max_bytes validation tests ---


def test_detect_max_bytes_zero_raises():
    with pytest.raises(ValueError, match="max_bytes"):
        chardet.detect(b"Hello", max_bytes=0)


def test_detect_max_bytes_negative_raises():
    with pytest.raises(ValueError, match="max_bytes"):
        chardet.detect(b"Hello", max_bytes=-1)


def test_detect_all_max_bytes_zero_raises():
    with pytest.raises(ValueError, match="max_bytes"):
        chardet.detect_all(b"Hello", max_bytes=0)


def test_detect_all_max_bytes_negative_raises():
    with pytest.raises(ValueError, match="max_bytes"):
        chardet.detect_all(b"Hello", max_bytes=-1)


# --- chunk_size deprecation tests ---


def test_chunk_size_deprecation_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        chardet.detect(b"Hello", chunk_size=1024)
        dep = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep) == 1
        assert "chunk_size" in str(dep[0].message)


def test_default_chunk_size_no_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        chardet.detect(b"Hello")
        dep = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep) == 0


# --- bytearray input tests ---


def test_detect_bytearray_input():
    result = chardet.detect(bytearray(b"Hello world"))
    assert result["encoding"] is not None


def test_detect_all_bytearray_input():
    results = chardet.detect_all(bytearray(b"Hello world"))
    assert len(results) >= 1


# --- New encoding tests ---


def test_detect_utf7():
    data = "Hello, 世界!".encode("utf-7")
    result = chardet.detect(data)
    assert result["encoding"] == "utf-7"


def test_detect_cp273():
    data = "Grüße aus Deutschland".encode("cp273")
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    assert result["encoding"] is not None


def test_detect_hp_roman8():
    data = "café résumé naïve".encode("hp-roman8")
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    assert result["encoding"] is not None
