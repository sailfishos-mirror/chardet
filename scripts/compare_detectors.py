#!/usr/bin/env python
"""Compare chardet-rewrite vs charset-normalizer accuracy on the chardet test suite."""

from __future__ import annotations

import sys
import time
from collections import defaultdict
from pathlib import Path

from charset_normalizer import from_bytes

import chardet
from chardet.enums import EncodingEra
from chardet.equivalences import is_correct

# ---------------------------------------------------------------------------
# Collect test files (same logic as test_accuracy.py)
# ---------------------------------------------------------------------------


def _collect_test_files(data_dir: Path) -> list[tuple[str, str, Path]]:
    test_files: list[tuple[str, str, Path]] = []
    for encoding_dir in sorted(data_dir.iterdir()):
        if not encoding_dir.is_dir():
            continue
        parts = encoding_dir.name.rsplit("-", 1)
        if len(parts) != 2:
            continue
        encoding_name, language = parts
        test_files.extend(
            (encoding_name, language, filepath)
            for filepath in sorted(encoding_dir.iterdir())
            if filepath.is_file()
        )
    return test_files


# ---------------------------------------------------------------------------
# Detection wrappers
# ---------------------------------------------------------------------------


def detect_chardet(data: bytes) -> str | None:
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    return result["encoding"]


def detect_charset_normalizer(data: bytes) -> str | None:
    result = from_bytes(data)
    best = result.best()
    if best is None:
        return None
    return best.encoding


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------


def run_comparison(data_dir: Path) -> None:
    test_files = _collect_test_files(data_dir)
    if not test_files:
        print("ERROR: No test files found!")
        sys.exit(1)

    print(f"Found {len(test_files)} test files\n")

    # Per-encoding stats
    chardet_per_enc: dict[str, dict[str, int]] = defaultdict(
        lambda: {"correct": 0, "total": 0}
    )
    cn_per_enc: dict[str, dict[str, int]] = defaultdict(
        lambda: {"correct": 0, "total": 0}
    )

    chardet_correct = 0
    cn_correct = 0
    total = 0

    # Detailed failures for reporting
    chardet_failures: list[str] = []
    cn_failures: list[str] = []

    # Timing
    chardet_time = 0.0
    cn_time = 0.0

    for expected_encoding, _language, filepath in test_files:
        data = filepath.read_bytes()
        total += 1

        # --- chardet rewrite ---
        t0 = time.perf_counter()
        chardet_detected = detect_chardet(data)
        chardet_time += time.perf_counter() - t0
        chardet_match = is_correct(expected_encoding, chardet_detected)

        chardet_per_enc[expected_encoding]["total"] += 1
        if chardet_match:
            chardet_correct += 1
            chardet_per_enc[expected_encoding]["correct"] += 1
        else:
            chardet_failures.append(
                f"  {filepath.parent.name}/{filepath.name}: "
                f"expected={expected_encoding}, got={chardet_detected}"
            )

        # --- charset-normalizer ---
        t0 = time.perf_counter()
        cn_detected = detect_charset_normalizer(data)
        cn_time += time.perf_counter() - t0
        cn_match = is_correct(expected_encoding, cn_detected)

        cn_per_enc[expected_encoding]["total"] += 1
        if cn_match:
            cn_correct += 1
            cn_per_enc[expected_encoding]["correct"] += 1
        else:
            cn_failures.append(
                f"  {filepath.parent.name}/{filepath.name}: "
                f"expected={expected_encoding}, got={cn_detected}"
            )

    # ---------------------------------------------------------------------------
    # Report
    # ---------------------------------------------------------------------------

    chardet_acc = chardet_correct / total if total else 0
    cn_acc = cn_correct / total if total else 0

    print("=" * 80)
    print("OVERALL ACCURACY")
    print("=" * 80)
    print(
        f"  chardet-rewrite:      {chardet_correct}/{total} = {chardet_acc:.1%}  ({chardet_time:.2f}s)"
    )
    print(
        f"  charset-normalizer:   {cn_correct}/{total} = {cn_acc:.1%}  ({cn_time:.2f}s)"
    )
    print()

    # Per-encoding table
    all_encodings = sorted(set(list(chardet_per_enc.keys()) + list(cn_per_enc.keys())))

    print("=" * 80)
    print("PER-ENCODING ACCURACY")
    print("=" * 80)
    print(
        f"{'Encoding':<25} {'Files':>5}  {'chardet-rewrite':>18}  {'charset-normalizer':>20}"
    )
    print("-" * 80)

    chardet_worse: list[tuple[str, float, float, int]] = []
    cn_worse: list[tuple[str, float, float, int]] = []

    for enc in all_encodings:
        c_stats = chardet_per_enc[enc]
        n_stats = cn_per_enc[enc]
        t = c_stats["total"]  # same for both
        c_acc = c_stats["correct"] / t if t else 0
        n_acc = n_stats["correct"] / t if t else 0
        marker = ""
        if c_acc > n_acc:
            marker = " <-- chardet better"
        elif n_acc > c_acc:
            marker = " <-- cn better"
        print(
            f"  {enc:<23} {t:>5}  {c_stats['correct']:>3}/{t:<3} = {c_acc:>6.1%}  {n_stats['correct']:>5}/{t:<3} = {n_acc:>6.1%}{marker}"
        )

        if c_acc < 1.0:
            chardet_worse.append((enc, c_acc, n_acc, t))
        if n_acc < 1.0:
            cn_worse.append((enc, n_acc, c_acc, t))

    # Worst performers
    print()
    print("=" * 80)
    print("WORST-PERFORMING ENCODINGS FOR charset-normalizer (accuracy < 100%)")
    print("=" * 80)
    cn_worse.sort(key=lambda x: x[1])
    for enc, acc, other_acc, t in cn_worse:
        print(f"  {enc:<25} {acc:>6.1%}  (chardet-rewrite: {other_acc:.1%}, {t} files)")

    print()
    print("=" * 80)
    print("WORST-PERFORMING ENCODINGS FOR chardet-rewrite (accuracy < 100%)")
    print("=" * 80)
    chardet_worse.sort(key=lambda x: x[1])
    for enc, acc, other_acc, t in chardet_worse:
        print(
            f"  {enc:<25} {acc:>6.1%}  (charset-normalizer: {other_acc:.1%}, {t} files)"
        )

    # Show some failure details
    print()
    print("=" * 80)
    print(f"CHARDET-REWRITE FAILURES ({len(chardet_failures)} total)")
    print("=" * 80)
    for f in chardet_failures[:50]:
        print(f)
    if len(chardet_failures) > 50:
        print(f"  ... and {len(chardet_failures) - 50} more")

    print()
    print("=" * 80)
    print(f"CHARSET-NORMALIZER FAILURES ({len(cn_failures)} total)")
    print("=" * 80)
    for f in cn_failures[:50]:
        print(f)
    if len(cn_failures) > 50:
        print(f"  ... and {len(cn_failures) - 50} more")


# ---------------------------------------------------------------------------
# Edge-case tests with short inputs
# ---------------------------------------------------------------------------


def test_short_inputs() -> None:
    print()
    print("=" * 80)
    print("SHORT INPUT EDGE CASES")
    print("=" * 80)

    test_cases = [
        (b"", "empty bytes"),
        (b"A", "single ASCII byte"),
        (b"\xe4", "single high byte 0xe4"),
        (b"\x80", "single byte 0x80"),
        (b"\xff\xfe", "UTF-16 LE BOM (2 bytes)"),
        (b"\xc3\xa4", "UTF-8 for 'a-umlaut' (2 bytes)"),
        (b"\xe4\xb8\xad", "UTF-8 for CJK char (3 bytes)"),
        (b"Hi", "ASCII 'Hi' (2 bytes)"),
        (b"\x1b$B", "ISO-2022-JP escape (3 bytes)"),
    ]

    print(f"\n{'Input':<35} {'chardet-rewrite':<40} {'charset-normalizer':<40}")
    print("-" * 115)

    for data, description in test_cases:
        # chardet-rewrite
        try:
            cr = chardet.detect(data, encoding_era=EncodingEra.ALL)
            cr_str = f"{cr['encoding']} ({cr['confidence']:.2f})"
        except Exception as e:
            cr_str = f"ERROR: {e}"

        # charset-normalizer
        try:
            cn_result = from_bytes(data)
            cn_best = cn_result.best()
            if cn_best is None:
                cn_str = "None"
            else:
                cn_str = f"{cn_best.encoding} ({cn_best.encoding})"
        except Exception as e:
            cn_str = f"ERROR: {e}"

        print(f"  {description:<33} {cr_str:<40} {cn_str:<40}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent / "tests" / "data"
    if not data_dir.is_dir():
        print(f"ERROR: Test data directory not found: {data_dir}")
        sys.exit(1)

    run_comparison(data_dir)
    test_short_inputs()
