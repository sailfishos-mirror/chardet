# tests/test_accuracy.py
"""Accuracy evaluation against the chardet test suite."""

from __future__ import annotations

import codecs
from pathlib import Path

import pytest

import chardet
from chardet.enums import EncodingEra

_MIN_OVERALL_ACCURACY = 0.30  # Current baseline ~31.6%; raise as detection improves


def _normalize_encoding_name(name: str) -> str:
    """Normalize encoding name for comparison."""
    try:
        return codecs.lookup(name).name
    except LookupError:
        return name.lower().replace("-", "").replace("_", "")


def _collect_test_files(data_dir: Path) -> list[tuple[str, str, Path]]:
    """Collect (encoding, language, filepath) tuples from test data.

    Directory name format: "{encoding}-{language}" e.g. "utf-8-english",
    "iso-8859-1-french", "hz-gb-2312-chinese".

    Since all language names are single words (no hyphens), we can reliably
    split on the last hyphen to separate encoding from language.
    """
    test_files: list[tuple[str, str, Path]] = []
    for encoding_dir in sorted(data_dir.iterdir()):
        if not encoding_dir.is_dir():
            continue
        # Split on last hyphen: encoding may contain hyphens, language never does
        parts = encoding_dir.name.rsplit("-", 1)
        if len(parts) != 2:
            # Directories without a hyphen (e.g. "ascii", "None") are skipped
            continue
        encoding_name, language = parts
        for filepath in sorted(encoding_dir.iterdir()):
            if filepath.is_file():
                test_files.append((encoding_name, language, filepath))
    return test_files


def test_overall_accuracy(chardet_test_data_dir: Path) -> None:
    """Test overall detection accuracy across all test files."""
    test_files = _collect_test_files(chardet_test_data_dir)
    if not test_files:
        pytest.skip("No test data found")

    correct = 0
    total = 0
    failures: list[str] = []

    for expected_encoding, _language, filepath in test_files:
        data = filepath.read_bytes()
        result = chardet.detect(data, encoding_era=EncodingEra.ALL)
        detected = result["encoding"]

        total += 1
        # Normalize both names for comparison (e.g., "iso-8859-1" vs "iso8859-1")
        expected_norm = _normalize_encoding_name(expected_encoding)
        detected_norm = _normalize_encoding_name(detected) if detected else ""

        if expected_norm == detected_norm:
            correct += 1
        else:
            failures.append(
                f"  {filepath.parent.name}/{filepath.name}: "
                f"expected={expected_encoding}, got={detected} "
                f"(confidence={result['confidence']:.2f})"
            )

    accuracy = correct / total if total > 0 else 0.0
    print(f"\nAccuracy: {correct}/{total} = {accuracy:.1%}")
    if failures:
        print(f"Failures ({len(failures)}):")
        for f in failures[:30]:
            print(f)
        if len(failures) > 30:
            print(f"  ... and {len(failures) - 30} more")

    assert accuracy >= _MIN_OVERALL_ACCURACY, (
        f"Overall accuracy {accuracy:.1%} below threshold {_MIN_OVERALL_ACCURACY:.0%}"
    )
