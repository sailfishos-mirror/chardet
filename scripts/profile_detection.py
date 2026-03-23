#!/usr/bin/env python
"""Profile chardet detection on the full test suite.

Two modes:

1. **Aggregate** (default): cProfile over all files, showing top functions
   by cumulative and self time.

2. **Per-file** (``--slow N``): time each ``detect()`` call individually,
   then show the N slowest files with per-stage breakdowns so you can see
   *which* files are expensive and *where* the time goes.
"""

from __future__ import annotations

import argparse
import cProfile
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import collect_test_files

import chardet
from chardet._utils import DEFAULT_MAX_BYTES
from chardet.enums import EncodingEra
from chardet.pipeline import PipelineContext
from chardet.pipeline.ascii import detect_ascii
from chardet.pipeline.binary import is_binary
from chardet.pipeline.bom import detect_bom
from chardet.pipeline.confusion import resolve_confusion_groups
from chardet.pipeline.escape import detect_escape_encoding
from chardet.pipeline.magic import detect_magic
from chardet.pipeline.markup import detect_markup_charset
from chardet.pipeline.statistical import score_candidates
from chardet.pipeline.structural import compute_structural_score
from chardet.pipeline.utf8 import detect_utf8
from chardet.pipeline.utf1632 import detect_utf1632_patterns
from chardet.pipeline.validity import filter_by_validity
from chardet.registry import get_candidates


def run_all_detections(data_dir: Path) -> None:
    test_files = collect_test_files(data_dir)
    for _enc, _lang, filepath in test_files:
        data = filepath.read_bytes()
        chardet.detect(data, encoding_era=EncodingEra.ALL)


def run_per_file_timing(data_dir: Path, slow_count: int) -> None:
    """Time each detection individually and report the slowest files."""
    test_files = collect_test_files(data_dir)

    # Warm up (first detect triggers lazy model loading)
    if test_files:
        warmup_data = test_files[0][2].read_bytes()
        chardet.detect(warmup_data, encoding_era=EncodingEra.ALL)

    results: list[tuple[float, str, str, str | None, int, dict[str, float]]] = []

    candidates = get_candidates(EncodingEra.ALL, None, None)

    for enc, lang, filepath in test_files:
        data = filepath.read_bytes()
        data_truncated = data[:DEFAULT_MAX_BYTES]
        file_label = f"{enc}-{lang}/{filepath.name}"
        stages: dict[str, float] = {}

        t_total_start = time.perf_counter()

        # BOM
        t0 = time.perf_counter()
        bom_result = detect_bom(data_truncated)
        stages["bom"] = time.perf_counter() - t0
        if bom_result is not None:
            stages["exit_stage"] = "bom"
            t_total = time.perf_counter() - t_total_start
            results.append(
                (t_total, file_label, enc or "None", None, len(data), stages)
            )
            continue

        # UTF-16/32
        t0 = time.perf_counter()
        utf1632_result = detect_utf1632_patterns(data_truncated)
        stages["utf1632"] = time.perf_counter() - t0
        if utf1632_result is not None:
            stages["exit_stage"] = "utf1632"
            t_total = time.perf_counter() - t_total_start
            results.append(
                (t_total, file_label, enc or "None", None, len(data), stages)
            )
            continue

        # Escape
        t0 = time.perf_counter()
        escape_result = detect_escape_encoding(data_truncated)
        stages["escape"] = time.perf_counter() - t0
        if escape_result is not None and escape_result.encoding is not None:
            stages["exit_stage"] = "escape"
            t_total = time.perf_counter() - t_total_start
            results.append(
                (t_total, file_label, enc or "None", None, len(data), stages)
            )
            continue

        # Magic
        t0 = time.perf_counter()
        magic_result = detect_magic(data_truncated)
        stages["magic"] = time.perf_counter() - t0
        if magic_result is not None:
            stages["exit_stage"] = "magic"
            t_total = time.perf_counter() - t_total_start
            results.append(
                (t_total, file_label, enc or "None", None, len(data), stages)
            )
            continue

        # UTF-8 precheck
        t0 = time.perf_counter()
        utf8_precheck = detect_utf8(data_truncated)
        stages["utf8"] = time.perf_counter() - t0

        # ASCII precheck
        t0 = time.perf_counter()
        ascii_precheck = detect_ascii(data_truncated)
        stages["ascii"] = time.perf_counter() - t0

        # Binary
        t0 = time.perf_counter()
        binary = (
            utf8_precheck is None
            and ascii_precheck is None
            and is_binary(data_truncated)
        )
        stages["binary"] = time.perf_counter() - t0
        if binary:
            stages["exit_stage"] = "binary"
            t_total = time.perf_counter() - t_total_start
            results.append(
                (t_total, file_label, enc or "None", None, len(data), stages)
            )
            continue

        # Markup
        t0 = time.perf_counter()
        markup_result = detect_markup_charset(data_truncated)
        stages["markup"] = time.perf_counter() - t0
        if markup_result is not None:
            stages["exit_stage"] = "markup"
            t_total = time.perf_counter() - t_total_start
            results.append(
                (t_total, file_label, enc or "None", None, len(data), stages)
            )
            continue

        # ASCII / UTF-8 return
        if ascii_precheck is not None:
            stages["exit_stage"] = "ascii"
            t_total = time.perf_counter() - t_total_start
            results.append(
                (t_total, file_label, enc or "None", None, len(data), stages)
            )
            continue
        if utf8_precheck is not None:
            stages["exit_stage"] = "utf8"
            t_total = time.perf_counter() - t_total_start
            results.append(
                (t_total, file_label, enc or "None", None, len(data), stages)
            )
            continue

        # Validity filtering
        t0 = time.perf_counter()
        valid_candidates = filter_by_validity(data_truncated, candidates)
        stages["validity"] = time.perf_counter() - t0

        # Structural scoring (for multibyte candidates)
        t0 = time.perf_counter()
        for enc_info in valid_candidates:
            if enc_info.is_multibyte:
                ctx = PipelineContext()
                compute_structural_score(data_truncated, enc_info, ctx)
        stages["structural"] = time.perf_counter() - t0

        # Statistical scoring
        t0 = time.perf_counter()
        stat_results = list(score_candidates(data_truncated, tuple(valid_candidates)))
        stages["statistical"] = time.perf_counter() - t0

        # Confusion resolution
        t0 = time.perf_counter()
        if stat_results:
            resolve_confusion_groups(data_truncated, stat_results)
        stages["confusion"] = time.perf_counter() - t0

        # Full detect for the actual result
        detected = chardet.detect(data, encoding_era=EncodingEra.ALL)
        stages["exit_stage"] = "statistical"
        stages["detected"] = detected.get("encoding") or "None"

        t_total = time.perf_counter() - t_total_start
        results.append(
            (
                t_total,
                file_label,
                enc or "None",
                detected.get("encoding"),
                len(data),
                stages,
            )
        )

    # Sort by total time descending
    results.sort(key=lambda x: x[0], reverse=True)

    # Summary stats
    times = [r[0] for r in results]
    total = sum(times)
    times_sorted = sorted(times)
    n = len(times_sorted)
    p90 = times_sorted[int(n * 0.90)] if n else 0
    p95 = times_sorted[int(n * 0.95)] if n else 0
    p99 = times_sorted[int(n * 0.99)] if n else 0

    print("=" * 100)
    print("TIMING DISTRIBUTION")
    print("=" * 100)
    print(f"  Files: {n}")
    print(f"  Total: {total * 1000:.1f}ms")
    print(f"  Mean:  {(total / n) * 1000:.2f}ms" if n else "  Mean:  N/A")
    print(f"  p90:   {p90 * 1000:.2f}ms")
    print(f"  p95:   {p95 * 1000:.2f}ms")
    print(f"  p99:   {p99 * 1000:.2f}ms")
    print(f"  Max:   {times_sorted[-1] * 1000:.2f}ms" if n else "  Max:   N/A")
    print()

    # Exit stage distribution
    exit_stages: dict[str, int] = {}
    for _, _, _, _, _, stages in results:
        stage = stages.get("exit_stage", "unknown")
        exit_stages[stage] = exit_stages.get(stage, 0) + 1
    print("=" * 100)
    print("EXIT STAGE DISTRIBUTION")
    print("=" * 100)
    for stage, count in sorted(exit_stages.items(), key=lambda x: -x[1]):
        print(f"  {stage:<15s} {count:>5d}  ({count / n * 100:.1f}%)")
    print()

    # Slowest files
    print("=" * 100)
    print(f"SLOWEST {slow_count} FILES")
    print("=" * 100)
    for i, (t_total, label, expected, _detected, size, stages) in enumerate(
        results[:slow_count]
    ):
        print(f"\n  #{i + 1}: {label}")
        print(
            f"       Total: {t_total * 1000:.2f}ms  |  Size: {size:,} bytes  |  Expected: {expected}  |  Exit: {stages.get('exit_stage', '?')}"
        )
        # Show per-stage times, skipping near-zero
        stage_parts = []
        for stage_name in [
            "bom",
            "utf1632",
            "escape",
            "magic",
            "utf8",
            "ascii",
            "binary",
            "markup",
            "validity",
            "structural",
            "statistical",
            "confusion",
        ]:
            if stage_name in stages:
                ms = stages[stage_name] * 1000
                if ms >= 0.01:
                    stage_parts.append(f"{stage_name}={ms:.2f}ms")
        print(f"       Stages: {', '.join(stage_parts)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--slow",
        type=int,
        default=0,
        metavar="N",
        help="Show the N slowest files with per-stage timing (skips cProfile)",
    )
    args = parser.parse_args()

    data_dir = Path(__file__).resolve().parent.parent / "tests" / "data"

    if args.slow > 0:
        run_per_file_timing(data_dir, args.slow)
    else:
        profiler = cProfile.Profile()
        profiler.enable()
        run_all_detections(data_dir)
        profiler.disable()

        stats = pstats.Stats(profiler)
        stats.sort_stats("cumulative")
        print("=" * 80)
        print("TOP 40 BY CUMULATIVE TIME")
        print("=" * 80)
        stats.print_stats(40)

        print("=" * 80)
        print("TOP 40 BY TOTAL (SELF) TIME")
        print("=" * 80)
        stats.sort_stats("tottime")
        stats.print_stats(40)


if __name__ == "__main__":
    main()
