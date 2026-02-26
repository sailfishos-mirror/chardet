#!/usr/bin/env python
"""Compare chardet-rewrite vs charset-normalizer using directional equivalences.

Uses the same directional superset/bidirectional logic as the test framework
in test_accuracy.py to determine correctness.
"""

from __future__ import annotations

import sys
import time
from collections import defaultdict
from pathlib import Path

from charset_normalizer import from_bytes

import chardet
from chardet.enums import EncodingEra
from chardet.equivalences import BIDIRECTIONAL_GROUPS, SUPERSETS, is_correct

# ---------------------------------------------------------------------------
# Collect test files
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
# Special cp874/tis-620/iso-8859-11 analysis
# ---------------------------------------------------------------------------


def analyze_thai_encodings(data_dir: Path) -> None:
    """Detailed analysis of cp874 vs tis-620 vs iso-8859-11 test files."""
    print()
    print("=" * 100)
    print("DETAILED ANALYSIS: cp874 / tis-620 / iso-8859-11 TEST FILES")
    print("=" * 100)

    thai_dirs = ["cp874-thai", "tis-620-thai", "iso-8859-11-thai"]

    for dir_name in thai_dirs:
        dir_path = data_dir / dir_name
        if not dir_path.is_dir():
            print(f"\n  Directory {dir_name} not found, skipping.")
            continue

        files = sorted(f for f in dir_path.iterdir() if f.is_file())
        print(f"\n  --- {dir_name} ({len(files)} files) ---")
        print(f"  {'File':<30} {'chardet-rewrite':<25} {'charset-normalizer':<25}")
        print(f"  {'-' * 30} {'-' * 25} {'-' * 25}")

        chardet_results: dict[str, int] = defaultdict(int)
        cn_results: dict[str, int] = defaultdict(int)

        for filepath in files:
            data = filepath.read_bytes()

            cr = detect_chardet(data)
            cn = detect_charset_normalizer(data)

            cr_str = cr if cr else "None"
            cn_str = cn if cn else "None"

            chardet_results[cr_str] += 1
            cn_results[cn_str] += 1

            print(f"  {filepath.name:<30} {cr_str:<25} {cn_str:<25}")

        print(f"\n  Summary for {dir_name}:")
        print(f"    chardet-rewrite detections: {dict(chardet_results)}")
        print(f"    charset-normalizer detections: {dict(cn_results)}")


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------


def run_comparison(data_dir: Path) -> None:
    test_files = _collect_test_files(data_dir)
    if not test_files:
        print("ERROR: No test files found!")
        sys.exit(1)

    print(f"Found {len(test_files)} test files")
    print()
    print("Directional equivalences used:")
    print("  Superset relationships (detected superset of expected is correct):")
    for subset, supersets in SUPERSETS.items():
        print(f"    {subset} -> {', '.join(sorted(supersets))}")
    print("  Bidirectional groups (byte-order variants):")
    for group in BIDIRECTIONAL_GROUPS:
        print(f"    {' = '.join(group)}")
    print()

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

    # Detailed failures
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

    print("=" * 100)
    print("OVERALL ACCURACY (directional equivalences)")
    print("=" * 100)
    print(
        f"  chardet-rewrite:      {chardet_correct}/{total} = {chardet_acc:.1%}  ({chardet_time:.2f}s)"
    )
    print(
        f"  charset-normalizer:   {cn_correct}/{total} = {cn_acc:.1%}  ({cn_time:.2f}s)"
    )
    print()

    # Per-encoding table
    all_encodings = sorted(set(list(chardet_per_enc.keys()) + list(cn_per_enc.keys())))

    print("=" * 100)
    print("PER-ENCODING ACCURACY (directional)")
    print("=" * 100)
    print(
        f"  {'Encoding':<25} {'Files':>5}  {'chardet-rewrite':>18}  {'charset-normalizer':>20}  {'Winner'}"
    )
    print(f"  {'-' * 25} {'-' * 5}  {'-' * 18}  {'-' * 20}  {'-' * 20}")

    chardet_wins: list[tuple[str, float, float, int]] = []
    cn_wins: list[tuple[str, float, float, int]] = []
    ties: list[tuple[str, float, int]] = []

    for enc in all_encodings:
        c_stats = chardet_per_enc[enc]
        n_stats = cn_per_enc[enc]
        t = c_stats["total"]
        c_acc = c_stats["correct"] / t if t else 0
        n_acc = n_stats["correct"] / t if t else 0

        if c_acc > n_acc:
            winner = "chardet-rewrite"
            chardet_wins.append((enc, c_acc, n_acc, t))
        elif n_acc > c_acc:
            winner = "charset-normalizer"
            cn_wins.append((enc, n_acc, c_acc, t))
        else:
            winner = "TIE"
            ties.append((enc, c_acc, t))

        print(
            f"  {enc:<25} {t:>5}  "
            f"{c_stats['correct']:>3}/{t:<3} = {c_acc:>6.1%}  "
            f"{n_stats['correct']:>5}/{t:<3} = {n_acc:>6.1%}  "
            f"{winner}"
        )

    # Summary: chardet wins
    print()
    print("=" * 100)
    print(f"ENCODINGS WHERE chardet-rewrite WINS ({len(chardet_wins)} encodings)")
    print("=" * 100)
    chardet_wins.sort(key=lambda x: x[1] - x[2], reverse=True)
    for enc, c_acc, n_acc, t in chardet_wins:
        diff = c_acc - n_acc
        print(
            f"  {enc:<25} chardet={c_acc:>6.1%}  cn={n_acc:>6.1%}  delta={diff:>+6.1%}  ({t} files)"
        )

    # Summary: cn wins
    print()
    print("=" * 100)
    print(f"ENCODINGS WHERE charset-normalizer WINS ({len(cn_wins)} encodings)")
    print("=" * 100)
    cn_wins.sort(key=lambda x: x[1] - x[2], reverse=True)
    for enc, n_acc, c_acc, t in cn_wins:
        diff = n_acc - c_acc
        print(
            f"  {enc:<25} cn={n_acc:>6.1%}  chardet={c_acc:>6.1%}  delta={diff:>+6.1%}  ({t} files)"
        )

    # Ties
    print()
    print("=" * 100)
    print(f"ENCODINGS WHERE BOTH ARE TIED ({len(ties)} encodings)")
    print("=" * 100)
    for enc, acc, t in ties:
        print(f"  {enc:<25} both={acc:>6.1%}  ({t} files)")

    # Failure details
    print()
    print("=" * 100)
    print(f"CHARDET-REWRITE FAILURES ({len(chardet_failures)} total)")
    print("=" * 100)
    for f in chardet_failures[:80]:
        print(f)
    if len(chardet_failures) > 80:
        print(f"  ... and {len(chardet_failures) - 80} more")

    print()
    print("=" * 100)
    print(f"CHARSET-NORMALIZER FAILURES ({len(cn_failures)} total)")
    print("=" * 100)
    for f in cn_failures[:80]:
        print(f)
    if len(cn_failures) > 80:
        print(f"  ... and {len(cn_failures) - 80} more")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent / "tests" / "data"
    if not data_dir.is_dir():
        print(f"ERROR: Test data directory not found: {data_dir}")
        sys.exit(1)

    run_comparison(data_dir)
    analyze_thai_encodings(data_dir)
