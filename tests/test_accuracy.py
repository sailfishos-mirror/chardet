# tests/test_accuracy.py
"""Accuracy evaluation against the chardet test suite.

Each test function is independently parametrized with its own xfail set.
Run with ``pytest -n auto`` for parallel execution.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
from utils import collect_test_files, get_data_dir, normalize_language

import chardet
from chardet.detector import UniversalDetector
from chardet.enums import EncodingEra
from chardet.equivalences import is_correct, is_equivalent_detection
from chardet.registry import REGISTRY

# ---------------------------------------------------------------------------
# Known accuracy failures — marked xfail so they don't block CI but are
# tracked for future improvement.  Kept sorted for easy diffing.
# ---------------------------------------------------------------------------

_KNOWN_FAILURES: frozenset[str] = frozenset(
    {
        "cp037-dutch/culturax_mC4_107675.txt",
        "cp037-english/_ude_1.txt",
        "cp437-dutch/culturax_00000.txt",
        "cp437-english/culturax_00000.txt",
        "cp437-english/culturax_00001.txt",
        "cp437-english/culturax_00002.txt",
        "cp437-finnish/culturax_00000.txt",
        "cp437-finnish/culturax_00001.txt",
        "cp437-finnish/culturax_00002.txt",
        "cp437-irish/culturax_mC4_63473.txt",
        "cp500-spanish/culturax_mC4_87070.txt",
        "cp850-danish/culturax_00002.txt",
        "cp850-dutch/culturax_00000.txt",
        "cp850-dutch/culturax_00001.txt",
        "cp850-english/culturax_00000.txt",
        "cp850-english/culturax_00001.txt",
        "cp850-finnish/culturax_00000.txt",
        "cp850-finnish/culturax_00001.txt",
        "cp850-finnish/culturax_00002.txt",
        "cp850-icelandic/culturax_00000.txt",
        "cp850-icelandic/culturax_00001.txt",
        "cp850-icelandic/culturax_00002.txt",
        "cp850-indonesian/culturax_00000.txt",
        "cp850-malay/culturax_00000.txt",
        "cp852-romanian/culturax_mC4_78976.txt",
        "cp852-romanian/culturax_mC4_78978.txt",
        "cp852-romanian/culturax_mC4_78979.txt",
        "cp852-romanian/culturax_OSCAR-2019_78977.txt",
        "cp858-english/culturax_00000.txt",
        "cp858-finnish/culturax_mC4_80362.txt",
        "cp858-icelandic/culturax_00000.txt",
        "cp858-icelandic/culturax_00001.txt",
        "cp858-icelandic/culturax_00002.txt",
        "cp858-indonesian/culturax_00000.txt",
        "cp858-irish/culturax_mC4_63469.txt",
        "cp858-malay/culturax_00000.txt",
        "cp863-french/culturax_00002.txt",
        "cp864-arabic/culturax_00000.txt",
        "cp866-ukrainian/culturax_mC4_95020.txt",
        "cp866-ukrainian/culturax_mC4_95021.txt",
        "cp932-japanese/hardsoft.at.webry.info.xml",
        "cp932-japanese/y-moto.com.xml",
        "cp1006-urdu/culturax_00000.txt",
        "cp1006-urdu/culturax_00001.txt",
        "cp1006-urdu/culturax_00002.txt",
        "gb2312-chinese/_mozilla_bug171813_text.html",
        "hp-roman8-italian/culturax_00002.txt",
        "iso-8859-1-english/ioreg_output.txt",
        "iso-8859-10-finnish/culturax_00002.txt",
        "iso-8859-13-estonian/culturax_00002.txt",
        "iso-8859-15-irish/culturax_mC4_63469.txt",
        "iso-8859-16-romanian/_ude_1.txt",
        "maclatin2-slovene/culturax_mC4_66688.txt",
        "maclatin2-slovene/culturax_mC4_66690.txt",
        "macroman-breton/culturax_OSCAR-2019_43764.txt",
        "macroman-english/culturax_mC4_84512.txt",
        "macroman-indonesian/culturax_mC4_114889.txt",
        "macroman-irish/culturax_mC4_63468.txt",
        "macroman-irish/culturax_mC4_63469.txt",
        "macroman-irish/culturax_mC4_63470.txt",
        "macroman-welsh/culturax_mC4_78727.txt",
        "macroman-welsh/culturax_mC4_78729.txt",
        "utf-8-english/finnish-utf-8-latin-1-confusion.html",
    }
)

# Known failures when testing with era-filtered detection.
# Some overlap with _KNOWN_FAILURES (hard files that fail either way),
# some are unique (disambiguation is harder with fewer candidates),
# and many _KNOWN_FAILURES are absent (era filtering actually helps).
_KNOWN_ERA_FILTERED_FAILURES: frozenset[str] = frozenset(
    {
        "cp037-dutch/culturax_mC4_107675.txt",
        "cp037-english/_ude_1.txt",
        "cp437-english/culturax_00002.txt",
        "cp500-spanish/culturax_mC4_87070.txt",
        "cp850-danish/culturax_00002.txt",
        "cp850-dutch/culturax_00000.txt",
        "cp850-finnish/culturax_00001.txt",
        "cp850-icelandic/culturax_00000.txt",
        "cp850-icelandic/culturax_00001.txt",
        "cp850-icelandic/culturax_00002.txt",
        "cp852-romanian/culturax_OSCAR-2019_78977.txt",
        "cp852-romanian/culturax_mC4_78976.txt",
        "cp852-romanian/culturax_mC4_78978.txt",
        "cp852-romanian/culturax_mC4_78979.txt",
        "cp858-english/culturax_00000.txt",
        "cp858-finnish/culturax_mC4_80362.txt",
        "cp858-icelandic/culturax_00000.txt",
        "cp858-icelandic/culturax_00001.txt",
        "cp858-icelandic/culturax_00002.txt",
        "cp858-irish/culturax_mC4_63469.txt",
        "cp863-french/culturax_00002.txt",
        "cp864-arabic/culturax_00000.txt",
        "cp932-japanese/hardsoft.at.webry.info.xml",
        "cp932-japanese/y-moto.com.xml",
        "cp1006-urdu/culturax_00000.txt",
        "cp1006-urdu/culturax_00001.txt",
        "cp1006-urdu/culturax_00002.txt",
        "gb2312-chinese/_mozilla_bug171813_text.html",
        "hp-roman8-italian/culturax_00002.txt",
        "iso-8859-10-finnish/culturax_00002.txt",
        "iso-8859-13-estonian/culturax_00002.txt",
        "iso-8859-15-irish/culturax_mC4_63469.txt",
        "iso-8859-16-hungarian/culturax_OSCAR-2019_82421.txt",
        "iso-8859-16-romanian/_ude_1.txt",
        "macroman-danish/culturax_mC4_83469.txt",
        "macroman-finnish/culturax_mC4_80362.txt",
        "utf-8-english/finnish-utf-8-latin-1-confusion.html",
    }
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encoding_era(name: str | None) -> EncodingEra:
    """Look up the encoding era for a test-data encoding name."""
    if name is None:
        return EncodingEra.ALL
    if name in REGISTRY:
        return REGISTRY[name].era
    lower = name.lower()
    for info in REGISTRY.values():
        if lower in (a.lower() for a in info.aliases):
            return info.era
    return EncodingEra.ALL


def _make_params(
    known_failures: frozenset[str],
) -> list[pytest.param]:
    """Build parametrize params from test data, marking known failures as xfail."""
    data_dir = get_data_dir()
    test_files = collect_test_files(data_dir)
    params = []
    for enc, lang, fp in test_files:
        test_id = f"{enc}-{lang}/{fp.name}"
        marks = []
        if test_id in known_failures:
            marks.append(pytest.mark.xfail(reason="known accuracy gap"))
        params.append(pytest.param(enc, lang, fp, marks=marks, id=test_id))
    return params


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("expected_encoding", "language", "test_file_path"),
    _make_params(_KNOWN_FAILURES),
)
def test_detect(
    expected_encoding: str | None, language: str | None, test_file_path: Path
) -> None:
    """Detect encoding of a single test file and verify correctness."""
    data = test_file_path.read_bytes()
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    detected = result["encoding"]

    # Binary files: expect encoding=None
    if expected_encoding is None:
        assert detected is None, (
            f"expected binary (None), got={detected} "
            f"(confidence={result['confidence']:.2f}, file={test_file_path.name})"
        )
        return

    assert is_correct(expected_encoding, detected) or is_equivalent_detection(
        data, expected_encoding, detected
    ), (
        f"expected={expected_encoding}, got={detected} "
        f"(confidence={result['confidence']:.2f}, "
        f"language={language}, file={test_file_path.name})"
    )

    # Language accuracy: warn but don't fail
    detected_language = normalize_language(result["language"])
    if detected_language is None or detected_language != language.lower():
        warnings.warn(
            f"Language mismatch: expected={language}, got={detected_language} "
            f"(encoding={expected_encoding}, file={test_file_path.name})",
            stacklevel=1,
        )


@pytest.mark.parametrize(
    ("expected_encoding", "language", "test_file_path"),
    _make_params(_KNOWN_ERA_FILTERED_FAILURES),
)
def test_detect_era_filtered(
    expected_encoding: str | None, language: str | None, test_file_path: Path
) -> None:
    """Detect encoding using only the expected encoding's own era."""
    era = _encoding_era(expected_encoding)
    data = test_file_path.read_bytes()
    result = chardet.detect(data, encoding_era=era)
    detected = result["encoding"]

    # Binary files: expect encoding=None
    if expected_encoding is None:
        assert detected is None, (
            f"expected binary (None), got={detected} "
            f"(era={era!r}, confidence={result['confidence']:.2f}, "
            f"file={test_file_path.name})"
        )
        return

    assert is_correct(expected_encoding, detected) or is_equivalent_detection(
        data, expected_encoding, detected
    ), (
        f"expected={expected_encoding}, got={detected} "
        f"(era={era!r}, confidence={result['confidence']:.2f}, "
        f"language={language}, file={test_file_path.name})"
    )


@pytest.mark.parametrize(
    ("expected_encoding", "language", "test_file_path"),
    _make_params(frozenset()),
)
def test_detect_streaming_parity(
    expected_encoding: str | None, language: str | None, test_file_path: Path
) -> None:
    """UniversalDetector.feed/close must match chardet.detect (GH-296)."""
    data = test_file_path.read_bytes()
    direct = chardet.detect(data, encoding_era=EncodingEra.ALL)

    detector = UniversalDetector()
    detector.feed(data)
    streaming = detector.close()

    assert direct == streaming, (
        f"detect() != UniversalDetector for {test_file_path.name}: "
        f"detect={direct}, streaming={streaming}"
    )
