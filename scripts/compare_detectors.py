#!/usr/bin/env python
"""Compare chardet-rewrite vs charset-normalizer accuracy on the chardet test suite.

Includes:
- Rich per-encoding comparison with directional equivalences and winner column
- Win/loss/tie summaries
- Memory usage comparison (peak traced allocations)
- Thai encoding deep-dive (cp874 / tis-620 / iso-8859-11)
- Short-input edge cases
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import time
from collections import defaultdict
from pathlib import Path

from charset_normalizer import from_bytes
from utils import collect_test_files

import chardet
from chardet.enums import EncodingEra
from chardet.equivalences import BIDIRECTIONAL_GROUPS, SUPERSETS, is_correct

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
# Subprocess-isolated measurement (memory + import time)
# ---------------------------------------------------------------------------


def _format_bytes(n: int) -> str:
    """Format byte count as human-readable string."""
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MiB"
    if n >= 1 << 10:
        return f"{n / (1 << 10):.1f} KiB"
    return f"{n} B"


def _measure_in_subprocess(
    detector: str,
    scripts_dir: str,
    data_dir: str,
) -> dict[str, int | float]:
    """Measure import time and memory in an isolated subprocess.

    Two memory metrics are reported so they can cross-check each other:

    * **tracemalloc** (``traced_*``) -- only CPython-allocated objects; precise
      but blind to C-extension allocations.
    * **RSS** (``rss_*``) -- resident set size via ``resource.getrusage``;
      captures *all* memory (C extensions, mmap, etc.) but includes the
      interpreter and test-data overhead shared by both subprocesses.

    ``tracemalloc.reset_peak()`` is called right before the library import so
    the reported peak covers only import + detection, not file loading.
    """
    code = textwrap.dedent(f"""\
        import json, platform, resource, sys, time, tracemalloc
        from pathlib import Path

        tracemalloc.start()

        sys.path.insert(0, {scripts_dir!r})
        from utils import collect_test_files

        test_files = collect_test_files(Path({data_dir!r}))
        all_data = [fp.read_bytes() for _, _, fp in test_files]

        # Baseline: utils + file data loaded, detector library NOT yet imported.
        baseline_current, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()          # peak now tracks only import+detect
        rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        if {detector!r} == "chardet":
            t0 = time.perf_counter()
            import chardet
            from chardet.enums import EncodingEra
            import_time = time.perf_counter() - t0
            after_import, _ = tracemalloc.get_traced_memory()
            for d in all_data:
                chardet.detect(d, encoding_era=EncodingEra.ALL)
        else:
            t0 = time.perf_counter()
            from charset_normalizer import from_bytes
            import_time = time.perf_counter() - t0
            after_import, _ = tracemalloc.get_traced_memory()
            for d in all_data:
                r = from_bytes(d)
                r.best()

        _, traced_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # macOS reports ru_maxrss in bytes; Linux in KiB.
        if platform.system() != "Darwin":
            rss_before *= 1024
            rss_after *= 1024

        print(json.dumps({{
            "import_time": import_time,
            "traced_import": after_import - baseline_current,
            "traced_peak": traced_peak - baseline_current,
            "rss_before": rss_before,
            "rss_after": rss_after,
        }}))
    """)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"  WARNING: {detector} subprocess failed:", file=sys.stderr)
        print(f"  {result.stderr.strip()}", file=sys.stderr)
        return {
            "import_time": 0.0,
            "traced_import": 0,
            "traced_peak": 0,
            "rss_before": 0,
            "rss_after": 0,
        }
    return json.loads(result.stdout.strip())


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

            cr_str = cr or "None"
            cn_str = cn or "None"

            chardet_results[cr_str] += 1
            cn_results[cn_str] += 1

            print(f"  {filepath.name:<30} {cr_str:<25} {cn_str:<25}")

        print(f"\n  Summary for {dir_name}:")
        print(f"    chardet-rewrite detections: {dict(chardet_results)}")
        print(f"    charset-normalizer detections: {dict(cn_results)}")


# ---------------------------------------------------------------------------
# Edge-case tests with short inputs
# ---------------------------------------------------------------------------


def test_short_inputs() -> None:
    print()
    print("=" * 100)
    print("SHORT INPUT EDGE CASES")
    print("=" * 100)

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

    print(f"\n  {'Input':<35} {'chardet-rewrite':<40} {'charset-normalizer':<40}")
    print(f"  {'-' * 115}")

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
# Main comparison
# ---------------------------------------------------------------------------


def run_comparison(data_dir: Path) -> None:
    test_files = collect_test_files(data_dir)
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

    # Pre-read all file data so I/O doesn't affect timing or memory measurement.
    test_entries = [(enc, lang, fp, fp.read_bytes()) for enc, lang, fp in test_files]

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

    for expected_encoding, _language, filepath, data in test_entries:
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
    # Subprocess-isolated measurement (memory + import time)
    # ---------------------------------------------------------------------------

    scripts_dir = str(Path(__file__).resolve().parent)
    data_dir_str = str(data_dir)
    print("Measuring import time & memory (isolated subprocesses)...")
    chardet_sub = _measure_in_subprocess("chardet", scripts_dir, data_dir_str)
    cn_sub = _measure_in_subprocess("charset-normalizer", scripts_dir, data_dir_str)

    # ---------------------------------------------------------------------------
    # Report
    # ---------------------------------------------------------------------------

    chardet_acc = chardet_correct / total if total else 0
    cn_acc = cn_correct / total if total else 0

    print()
    print("=" * 100)
    print("OVERALL ACCURACY (directional equivalences)")
    print("=" * 100)
    print(
        f"  chardet-rewrite:      {chardet_correct}/{total} = {chardet_acc:.1%}  "
        f"({chardet_time:.2f}s)"
    )
    print(
        f"  charset-normalizer:   {cn_correct}/{total} = {cn_acc:.1%}  ({cn_time:.2f}s)"
    )
    print()
    print("=" * 100)
    print("STARTUP & MEMORY (isolated subprocesses)")
    print("=" * 100)
    print(
        f"  {'':25} {'import time':>12}  "
        f"{'traced import':>14} {'traced peak':>14}  "
        f"{'RSS before':>12} {'RSS after':>12}"
    )
    print(f"  {'-' * 25} {'-' * 12}  {'-' * 14} {'-' * 14}  {'-' * 12} {'-' * 12}")
    for label, sub in [
        ("chardet-rewrite", chardet_sub),
        ("charset-normalizer", cn_sub),
    ]:
        print(
            f"  {label:<25} "
            f"{sub['import_time']:>11.3f}s  "
            f"{_format_bytes(sub['traced_import']):>14} "
            f"{_format_bytes(sub['traced_peak']):>14}  "
            f"{_format_bytes(sub['rss_before']):>12} "
            f"{_format_bytes(sub['rss_after']):>12}"
        )
    print()
    print("  traced = tracemalloc (CPython allocations only)")
    print(
        "  RSS    = resident set size (all memory incl. C extensions; shared baseline)"
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
    test_short_inputs()
