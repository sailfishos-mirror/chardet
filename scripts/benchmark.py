# scripts/benchmark.py
"""Benchmark chardet detection speed and memory usage."""

from __future__ import annotations

import argparse
import statistics
import time
import tracemalloc
from pathlib import Path

import chardet
from chardet.enums import EncodingEra


def benchmark_file(data: bytes, iterations: int = 100) -> dict:
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        chardet.detect(data, encoding_era=EncodingEra.ALL)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)
    return {
        "p50": statistics.median(times),
        "p95": sorted(times)[int(len(times) * 0.95)],
        "p99": sorted(times)[int(len(times) * 0.99)],
        "mean": statistics.mean(times),
    }


def benchmark_memory(data: bytes) -> int:
    tracemalloc.start()
    chardet.detect(data, encoding_era=EncodingEra.ALL)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def main():
    parser = argparse.ArgumentParser(description="Benchmark chardet")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("tests/data"),
        help="Path to test data directory",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=100,
        help="Iterations per file",
    )
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(f"Data dir {args.data_dir} not found. Run accuracy tests first.")
        return

    samples: list[tuple[str, bytes]] = []
    for enc_dir in sorted(args.data_dir.iterdir()):
        if not enc_dir.is_dir():
            continue
        for f in enc_dir.iterdir():
            if f.is_file():
                samples.append((enc_dir.name, f.read_bytes()))
                break

    print(
        f"Benchmarking {len(samples)} encoding samples,"
        f" {args.iterations} iterations each\n"
    )
    print(
        f"{'Encoding':<30} {'p50 (ms)':>10} {'p95 (ms)':>10}"
        f" {'p99 (ms)':>10} {'Mem (KB)':>10}"
    )
    print("-" * 75)

    all_p50s = []
    for name, data in samples:
        stats = benchmark_file(data, args.iterations)
        mem = benchmark_memory(data)
        all_p50s.append(stats["p50"])
        print(
            f"{name:<30} {stats['p50']:>10.2f} {stats['p95']:>10.2f}"
            f" {stats['p99']:>10.2f} {mem // 1024:>10}"
        )

    print("-" * 75)
    print(f"{'Overall median p50':<30} {statistics.median(all_p50s):>10.2f} ms")


if __name__ == "__main__":
    main()
