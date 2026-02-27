#!/usr/bin/env python
"""Benchmark a single encoding detector: memory usage only.

Uses ``tracemalloc`` (started early) and RSS via ``resource.getrusage``.

Can be run standalone for human-readable output, or with ``--json-only`` for
machine-readable JSON (used by ``compare_detectors.py``).
"""

from __future__ import annotations

import argparse
import json
import platform
import resource
import sys
import tracemalloc
from pathlib import Path

# Start tracemalloc as early as possible to capture baseline accurately.
tracemalloc.start()


def _format_bytes(n: int) -> str:
    """Format byte count as human-readable string."""
    if n >= 1 << 20:
        return f"{n / (1 << 20):.1f} MiB"
    if n >= 1 << 10:
        return f"{n / (1 << 10):.1f} KiB"
    return f"{n} B"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark a single encoding detector (memory only).",
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

    # Make scripts/ importable for utils.collect_test_files
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from utils import collect_test_files

    test_files = collect_test_files(data_dir)
    if not test_files:
        print("ERROR: no test files found!", file=sys.stderr)
        sys.exit(1)

    # Pre-read all file data so I/O doesn't affect measurement
    all_data = [(enc, lang, fp, fp.read_bytes()) for enc, lang, fp in test_files]

    # Baseline: utils + file data loaded, detector library NOT yet imported
    baseline_current, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    # Import detector and build detect function
    if args.detector == "chardet" and args.use_encoding_era:
        import chardet
        from chardet.enums import EncodingEra

        after_import, _ = tracemalloc.get_traced_memory()

        def detect(data: bytes) -> str | None:
            return chardet.detect(data, encoding_era=EncodingEra.ALL)["encoding"]

    elif args.detector == "chardet":
        import chardet

        after_import, _ = tracemalloc.get_traced_memory()

        def detect(data: bytes) -> str | None:
            return chardet.detect(data)["encoding"]

    elif args.detector == "cchardet":
        import cchardet

        after_import, _ = tracemalloc.get_traced_memory()

        def detect(data: bytes) -> str | None:
            return cchardet.detect(data)["encoding"]

    else:
        from charset_normalizer import from_bytes

        after_import, _ = tracemalloc.get_traced_memory()

        def detect(data: bytes) -> str | None:
            r = from_bytes(data)
            best = r.best()
            return best.encoding if best else None

    # Run detection over all files (slow under tracemalloc, but needed for peak)
    for _enc, _lang, _fp, data in all_data:
        detect(data)

    _, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports ru_maxrss in bytes; Linux in KiB
    if platform.system() != "Darwin":
        rss_before *= 1024
        rss_after *= 1024

    traced_import = after_import - baseline_current
    traced_peak_delta = traced_peak - baseline_current

    if args.json_only:
        print(
            json.dumps(
                {
                    "traced_import": traced_import,
                    "traced_peak": traced_peak_delta,
                    "rss_before": rss_before,
                    "rss_after": rss_after,
                }
            )
        )
    else:
        print(f"Detector: {args.detector}")
        if args.detector == "chardet":
            print(f"  encoding_era: {args.use_encoding_era}")
        print(f"  Files:        {len(all_data)}")
        print()
        print("Memory:")
        print(f"  Traced import: {_format_bytes(traced_import)}")
        print(f"  Traced peak:   {_format_bytes(traced_peak_delta)}")
        print(f"  RSS before:    {_format_bytes(rss_before)}")
        print(f"  RSS after:     {_format_bytes(rss_after)}")


if __name__ == "__main__":
    main()
