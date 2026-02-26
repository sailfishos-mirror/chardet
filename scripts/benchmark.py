#!/usr/bin/env python
"""Benchmark a single encoding detector: import time, memory, and per-file speed.

Can be run standalone for human-readable output, or with ``--json-only`` for
machine-readable JSON (used by ``compare_detectors.py``).
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import statistics
import sys
import time
import tracemalloc
from pathlib import Path


def _format_bytes(n: int) -> str:
    """Format byte count as human-readable string."""
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MiB"
    if n >= 1 << 10:
        return f"{n / (1 << 10):.1f} KiB"
    return f"{n} B"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark a single encoding detector.",
    )
    parser.add_argument(
        "--detector",
        choices=["chardet", "charset-normalizer", "cchardet"],
        default="chardet",
        help="Detector library to benchmark (default: chardet)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("tests/data"),
        help="Path to test data directory (default: tests/data)",
    )
    parser.add_argument(
        "--use-encoding-era",
        action="store_true",
        default=False,
        help="Pass encoding_era=EncodingEra.ALL to chardet.detect (chardet 6.x+)",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        default=False,
        help="Print only JSON output (for consumption by other scripts)",
    )
    args = parser.parse_args()

    data_dir: Path = args.data_dir.resolve()
    if not data_dir.is_dir():
        print(f"ERROR: data directory not found: {data_dir}", file=sys.stderr)
        sys.exit(1)

    # Start tracemalloc early to capture baseline
    tracemalloc.start()

    # Make scripts/ importable for utils.collect_test_files
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from utils import collect_test_files

    test_files = collect_test_files(data_dir)
    if not test_files:
        print("ERROR: no test files found!", file=sys.stderr)
        sys.exit(1)

    # Pre-read all file data so I/O doesn't affect timing
    all_data = [(enc, lang, fp, fp.read_bytes()) for enc, lang, fp in test_files]

    # Baseline: utils + file data loaded, detector library NOT yet imported
    baseline_current, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()  # peak now tracks only import + detect
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # Import detector and build detect function
    t0 = time.perf_counter()
    if args.detector == "chardet" and args.use_encoding_era:
        import chardet
        from chardet.enums import EncodingEra

        import_time = time.perf_counter() - t0
        after_import, _ = tracemalloc.get_traced_memory()

        def detect(data: bytes) -> str | None:
            return chardet.detect(data, encoding_era=EncodingEra.ALL)["encoding"]

    elif args.detector == "chardet":
        import chardet

        import_time = time.perf_counter() - t0
        after_import, _ = tracemalloc.get_traced_memory()

        def detect(data: bytes) -> str | None:
            return chardet.detect(data)["encoding"]

    elif args.detector == "cchardet":
        import cchardet

        import_time = time.perf_counter() - t0
        after_import, _ = tracemalloc.get_traced_memory()

        def detect(data: bytes) -> str | None:
            return cchardet.detect(data)["encoding"]

    else:
        from charset_normalizer import from_bytes

        import_time = time.perf_counter() - t0
        after_import, _ = tracemalloc.get_traced_memory()

        def detect(data: bytes) -> str | None:
            r = from_bytes(data)
            best = r.best()
            return best.encoding if best else None

    # Run detection over all files, collect per-file times
    file_times: list[float] = []
    for _enc, _lang, _fp, data in all_data:
        ft0 = time.perf_counter()
        detect(data)
        file_times.append(time.perf_counter() - ft0)

    _, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports ru_maxrss in bytes; Linux in KiB
    if platform.system() != "Darwin":
        rss_before *= 1024
        rss_after *= 1024

    results = {
        "detector": args.detector,
        "use_encoding_era": args.use_encoding_era,
        "num_files": len(all_data),
        "import_time": import_time,
        "traced_import": after_import - baseline_current,
        "traced_peak": traced_peak - baseline_current,
        "rss_before": rss_before,
        "rss_after": rss_after,
    }

    # Always print JSON
    print(json.dumps(results))

    if not args.json_only:
        # Human-readable summary
        total_ms = sum(file_times) * 1000
        mean_ms = statistics.mean(file_times) * 1000 if file_times else 0.0
        median_ms = statistics.median(file_times) * 1000 if file_times else 0.0
        if len(file_times) >= 20:
            q = statistics.quantiles(file_times, n=20)
            p90_ms = q[17] * 1000
            p95_ms = q[18] * 1000
        else:
            p90_ms = p95_ms = 0.0

        print()
        print(f"Detector: {args.detector}")
        if args.detector == "chardet":
            print(f"  encoding_era: {args.use_encoding_era}")
        print(f"  Files:        {len(all_data)}")
        print()
        print("Timing:")
        print(f"  Import:       {import_time:.3f}s")
        print(f"  Detection:    {total_ms:.0f}ms total")
        print(
            f"  Per-file:     mean={mean_ms:.2f}ms  median={median_ms:.2f}ms"
            f"  p90={p90_ms:.2f}ms  p95={p95_ms:.2f}ms"
        )
        print()
        print("Memory:")
        print(f"  Traced import: {_format_bytes(after_import - baseline_current)}")
        print(f"  Traced peak:   {_format_bytes(traced_peak - baseline_current)}")
        print(f"  RSS before:    {_format_bytes(rss_before)}")
        print(f"  RSS after:     {_format_bytes(rss_after)}")


if __name__ == "__main__":
    main()
