# tests/test_accuracy.py
"""Accuracy evaluation against the chardet test suite.

Each test file is parametrized as its own test case via conftest.py's
pytest_generate_tests hook. Run with `pytest -n auto` for parallel execution.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import chardet
from chardet.enums import EncodingEra
from chardet.equivalences import is_correct, is_equivalent_detection

if TYPE_CHECKING:
    from pathlib import Path


def test_detect(expected_encoding: str, language: str, test_file_path: Path) -> None:
    """Detect encoding of a single test file and verify correctness."""
    data = test_file_path.read_bytes()
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    detected = result["encoding"]

    assert is_correct(expected_encoding, detected) or is_equivalent_detection(
        data, expected_encoding, detected
    ), (
        f"expected={expected_encoding}, got={detected} "
        f"(confidence={result['confidence']:.2f}, "
        f"language={language}, file={test_file_path.name})"
    )

    # Language accuracy: warn but don't fail
    detected_language = result["language"]
    if detected_language is None or detected_language.lower() != language.lower():
        warnings.warn(
            f"Language mismatch: expected={language}, got={detected_language} "
            f"(encoding={expected_encoding}, file={test_file_path.name})",
            stacklevel=1,
        )
