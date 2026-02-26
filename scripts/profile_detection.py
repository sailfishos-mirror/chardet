#!/usr/bin/env python
"""Profile chardet detection on the full test suite."""

from __future__ import annotations

import cProfile
import pstats
from pathlib import Path

from utils import collect_test_files

import chardet
from chardet.enums import EncodingEra


def run_all_detections(data_dir: Path) -> None:
    test_files = collect_test_files(data_dir)
    for _enc, _lang, filepath in test_files:
        data = filepath.read_bytes()
        chardet.detect(data, encoding_era=EncodingEra.ALL)


if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parent.parent / "tests" / "data"
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
