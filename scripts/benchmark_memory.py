#!/usr/bin/env python
"""Benchmark a single encoding detector: memory usage only.

Uses ``tracemalloc`` (started early) and RSS via ``resource.getrusage``.

Can be run standalone for human-readable output, or with ``--json-only`` for
machine-readable JSON (used by ``compare_detectors.py``).
"""

from __future__ import annotations

import json
import platform
import sys
import tracemalloc
from pathlib import Path

try:
    import resource

    _HAS_RESOURCE = True
except ImportError:
    _HAS_RESOURCE = False

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import format_bytes as _format_bytes

# Start tracemalloc as early as possible to capture baseline accurately.
tracemalloc.start()


def main() -> None:
    from utils import build_benchmark_parser, load_benchmark_data

    parser = build_benchmark_parser(
        "Benchmark a single encoding detector (memory only)."
    )
    args = parser.parse_args()
    all_data = load_benchmark_data(args)

    # Baseline: utils + file data loaded, detector library NOT yet imported
    baseline_current, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    rss_before = (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if _HAS_RESOURCE else 0
    )

    # Import detector and build detect function
    if args.detector == "chardet" and args.encoding_era != "none":
        import chardet
        from chardet.enums import EncodingEra

        after_import, _ = tracemalloc.get_traced_memory()
        era = EncodingEra.ALL if args.encoding_era == "all" else EncodingEra.MODERN_WEB

        def detect(data: bytes) -> str | None:
            return chardet.detect(data, encoding_era=era)["encoding"]

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

    rss_after = (
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if _HAS_RESOURCE else 0
    )
    # macOS reports ru_maxrss in bytes; Linux in KiB
    if _HAS_RESOURCE and platform.system() != "Darwin":
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
            print(f"  encoding_era: {args.encoding_era}")
        print(f"  Files:        {len(all_data)}")
        print()
        print("Memory:")
        print(f"  Traced import: {_format_bytes(traced_import)}")
        print(f"  Traced peak:   {_format_bytes(traced_peak_delta)}")
        print(f"  RSS before:    {_format_bytes(rss_before)}")
        print(f"  RSS after:     {_format_bytes(rss_after)}")


if __name__ == "__main__":
    main()
