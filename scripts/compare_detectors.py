#!/usr/bin/env python
"""Compare chardet-rewrite vs charset-normalizer accuracy on the chardet test suite.

Includes:
- Rich per-encoding comparison with directional equivalences and winner column
- Pairwise win/loss/tie breakdowns per opponent
- Memory usage comparison (peak traced allocations)

All detectors — including chardet-rewrite — run in isolated temporary venvs
created with ``uv`` for fair, consistent measurement.  Use ``--pure`` to
guarantee the chardet-rewrite venv contains no mypyc extensions.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import collect_test_files
from utils import format_bytes as _format_bytes

from chardet.equivalences import (
    BIDIRECTIONAL_GROUPS,
    SUPERSETS,
    is_correct,
    is_equivalent_detection,
)

# ---------------------------------------------------------------------------
# Venv management for isolated detectors
# ---------------------------------------------------------------------------


def _create_detector_venv(
    label: str,
    pip_args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> tuple[Path, Path]:
    """Create a temporary venv with a detector package installed.

    Parameters
    ----------
    label : str
        Human-readable label used for the temp dir prefix and log messages.
    pip_args : list[str]
        Arguments passed directly to ``uv pip install --python <venv_python>``.
    env : dict[str, str] | None
        Environment variables for the pip install step.  ``None`` inherits the
        parent process environment.

    Returns
    -------
    tuple[Path, Path]
        ``(venv_dir, python_executable)``

    """
    safe_prefix = label.replace(" ", "-").replace("/", "-")
    venv_dir = Path(tempfile.mkdtemp(prefix=f"{safe_prefix}-"))
    print(f"  Creating venv for {label} at {venv_dir} ...")
    subprocess.run(
        ["uv", "venv", "--python", sys.executable, str(venv_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    venv_python = venv_dir / "bin" / "python"
    print(f"  Installing {label} ...")
    subprocess.run(
        ["uv", "pip", "install", "--python", str(venv_python), *pip_args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return venv_dir, venv_python


def _cleanup_venv(venv_dir: Path) -> None:
    """Remove a temporary venv directory."""
    shutil.rmtree(venv_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Subprocess detection (for isolated detector versions)
# ---------------------------------------------------------------------------


def _run_timing_subprocess(
    python_executable: str,
    data_dir: str,
    *,
    detector_type: str = "chardet",
    encoding_era: str = "all",
    pure: bool = False,
) -> tuple[
    list[tuple[str, str, str, str | None, str | None]], float, list[float], float
]:
    """Run detection timing in an isolated subprocess via ``benchmark_time.py``.

    Parameters
    ----------
    python_executable : str
        Path to the Python interpreter in the target venv.
    data_dir : str
        Path to the test data directory.
    detector_type : str
        One of ``"chardet"``, ``"charset-normalizer"``, or ``"cchardet"``.
    encoding_era : str
        For ``"chardet"`` only -- ``"all"``, ``"modern_web"``, or ``"none"``.
    pure : bool
        Abort if mypyc .so/.pyd files are found (chardet only).

    Returns
    -------
    tuple
        ``(results, elapsed, file_times, import_time)`` where *results* is a
        list of ``(expected_encoding, expected_language, filepath_str,
        detected_encoding, detected_language)`` tuples, *file_times* is a list of per-file
        durations in seconds, and *import_time* is the detector import time.

    """
    benchmark_script = str(Path(__file__).resolve().parent / "benchmark_time.py")
    cmd = [
        python_executable,
        benchmark_script,
        "--detector",
        detector_type,
        "--data-dir",
        data_dir,
        "--json-only",
    ]
    cmd.extend(["--encoding-era", encoding_era])
    if pure:
        cmd.append("--pure")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(
            f"  WARNING: subprocess detection failed:\n  {result.stderr.strip()}",
            file=sys.stderr,
        )
        return [], 0.0, [], 0.0

    results: list[tuple[str, str, str, str | None, str | None]] = []
    file_times: list[float] = []
    timing = 0.0
    import_time = 0.0
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        obj = json.loads(line)
        if "__timing__" in obj:
            timing = obj["__timing__"]
            import_time = obj["import_time"]
        else:
            results.append(
                (
                    obj["expected"],
                    obj["language"],
                    obj["path"],
                    obj["detected"],
                    obj.get("detected_language"),
                )
            )
            file_times.append(obj["elapsed"])
    return results, timing, file_times, import_time


# ---------------------------------------------------------------------------
# Subprocess-isolated measurement (memory + import time)
# ---------------------------------------------------------------------------


def _measure_memory_subprocess(
    detector: str,
    data_dir: str,
    *,
    python_executable: str,
    encoding_era: str = "all",
    pure: bool = False,
) -> dict[str, int]:
    """Measure memory by running ``benchmark_memory.py`` in a subprocess."""
    benchmark_script = str(Path(__file__).resolve().parent / "benchmark_memory.py")
    cmd = [
        python_executable,
        benchmark_script,
        "--detector",
        detector,
        "--data-dir",
        data_dir,
        "--json-only",
    ]
    cmd.extend(["--encoding-era", encoding_era])
    if pure:
        cmd.append("--pure")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"  WARNING: {detector} memory benchmark failed:", file=sys.stderr)
        print(f"  {result.stderr.strip()}", file=sys.stderr)
        return {
            "traced_import": 0,
            "traced_peak": 0,
            "rss_before": 0,
            "rss_after": 0,
        }
    return json.loads(result.stdout.strip().split("\n")[0])


# ---------------------------------------------------------------------------
# Result recording helper
# ---------------------------------------------------------------------------


def _record_result(  # noqa: PLR0913
    detector_stats: dict,
    expected_encoding: str,
    expected_language: str,
    filepath: Path,
    detected: str | None,
    detected_language: str | None,
) -> None:
    """Update a detector's stats dict with one detection result."""
    detector_stats["total"] += 1
    detector_stats["per_enc"][expected_encoding]["total"] += 1
    if is_correct(expected_encoding, detected) or (
        detected is not None
        and is_equivalent_detection(filepath.read_bytes(), expected_encoding, detected)
    ):
        detector_stats["correct"] += 1
        detector_stats["per_enc"][expected_encoding]["correct"] += 1
    else:
        detector_stats["failures"].append(
            f"  {filepath.parent.name}/{filepath.name}: "
            f"expected={expected_encoding}, got={detected}"
        )

    # Language tracking (independent of encoding accuracy)
    detector_stats["lang_total"] += 1
    detector_stats["per_enc"][expected_encoding]["lang_total"] += 1
    if (
        detected_language is not None
        and detected_language.lower() == expected_language.lower()
    ):
        detector_stats["lang_correct"] += 1
        detector_stats["per_enc"][expected_encoding]["lang_correct"] += 1
    else:
        detector_stats["lang_failures"].append(
            f"  {filepath.parent.name}/{filepath.name}: "
            f"expected={expected_language}, got={detected_language}"
        )


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------


def run_comparison(
    data_dir: Path,
    detectors: list[tuple[str, str, str, str]],
    *,
    pure: bool = False,
) -> None:
    """Run accuracy and performance comparison across detectors.

    Parameters
    ----------
    data_dir : Path
        Path to the test data directory.
    detectors : list[tuple[str, str, str, str]]
        Each tuple is ``(label, detector_type, python_executable, encoding_era)``.
    pure : bool
        Propagate ``--pure`` to chardet subprocess scripts.

    """
    test_files = collect_test_files(data_dir)
    if not test_files:
        print("ERROR: No test files found!")
        sys.exit(1)

    detector_labels = [label for label, *_ in detectors]

    print(f"Found {len(test_files)} test files")
    print(f"Detectors: {', '.join(detector_labels)}")
    print()
    print("Equivalences used:")
    print("  Superset relationships (detected superset of expected is correct):")
    for subset, supersets in SUPERSETS.items():
        print(f"    {subset} -> {', '.join(sorted(supersets))}")
    print("  Bidirectional groups (byte-order variants):")
    for group in BIDIRECTIONAL_GROUPS:
        print(f"    {' = '.join(group)}")
    print("  Decoded-output equivalence (base-letter matching after NFKD")
    print("    normalization and currency/euro symbol equivalence)")
    print()

    # Initialize per-detector stats
    stats: dict[str, dict] = {}
    for label in detector_labels:
        stats[label] = {
            "correct": 0,
            "total": 0,
            "lang_correct": 0,
            "lang_total": 0,
            "per_enc": defaultdict(
                lambda: {
                    "correct": 0,
                    "total": 0,
                    "lang_correct": 0,
                    "lang_total": 0,
                }
            ),
            "failures": [],
            "lang_failures": [],
            "time": 0.0,
            "file_times": [],
        }

    data_dir_str = str(data_dir)

    # --- Subprocess detection for all detectors ---
    import_times: dict[str, float] = {}
    for label, detector_type, python_exe, era in detectors:
        print(f"  Running detection for {label} ...")
        results, elapsed, file_times, import_time = _run_timing_subprocess(
            python_exe,
            data_dir_str,
            detector_type=detector_type,
            encoding_era=era,
            pure=pure and detector_type == "chardet",
        )
        stats[label]["time"] = elapsed
        stats[label]["file_times"] = file_times
        import_times[label] = import_time
        for expected, exp_lang, path_str, detected, det_lang in results:
            _record_result(
                stats[label], expected, exp_lang, Path(path_str), detected, det_lang
            )

    total = stats[detectors[0][0]]["total"]

    # --- Subprocess-isolated memory measurement ---
    print("Measuring memory (isolated subprocesses)...")
    memory: dict[str, dict] = {}
    for label, detector_type, python_exe, era in detectors:
        print(f"  Measuring memory for {label} ...")
        memory[label] = _measure_memory_subprocess(
            detector_type,
            data_dir_str,
            python_executable=python_exe,
            encoding_era=era,
            pure=pure and detector_type == "chardet",
        )

    # ===================================================================
    # Report
    # ===================================================================

    # -- Overall accuracy --
    print()
    print("=" * 100)
    print("OVERALL ACCURACY (directional equivalences)")
    print("=" * 100)
    max_label = max(len(label) for label in detector_labels)
    for label in detector_labels:
        s = stats[label]
        acc = s["correct"] / total if total else 0
        print(
            f"  {label + ':':<{max_label + 1}} "
            f"{s['correct']:>4}/{total} = {acc:.1%}  ({s['time']:.2f}s)"
        )

    # -- Detection runtime distribution --
    print()
    print("=" * 100)
    print("DETECTION RUNTIME DISTRIBUTION (per-file, milliseconds)")
    print("=" * 100)
    print(
        f"  {'':>{max_label}}  {'total':>10}  {'mean':>10}  "
        f"{'median':>10}  {'p90':>10}  {'p95':>10}"
    )
    print(
        f"  {'-' * max_label}  {'-' * 10}  {'-' * 10}  "
        f"{'-' * 10}  {'-' * 10}  {'-' * 10}"
    )
    for label in detector_labels:
        ft = stats[label]["file_times"]
        if ft:
            total_ms = sum(ft) * 1000
            mean_ms = statistics.mean(ft) * 1000
            median_ms = statistics.median(ft) * 1000
            if len(ft) >= 20:
                q = statistics.quantiles(ft, n=20)
                p90_ms = q[17] * 1000  # 18/20 = 90th percentile
                p95_ms = q[18] * 1000  # 19/20 = 95th percentile
            else:
                p90_ms = p95_ms = 0.0
        else:
            total_ms = mean_ms = median_ms = p90_ms = p95_ms = 0.0
        print(
            f"  {label:<{max_label}} "
            f"{total_ms:>9.0f}ms "
            f"{mean_ms:>9.2f}ms "
            f"{median_ms:>9.2f}ms "
            f"{p90_ms:>9.2f}ms "
            f"{p95_ms:>9.2f}ms"
        )

    # -- Startup & memory --
    print()
    print("=" * 100)
    print("STARTUP & MEMORY (isolated subprocesses)")
    print("=" * 100)
    print(
        f"  {'':>{max_label}}  {'import time':>12}  "
        f"{'traced import':>14} {'traced peak':>14}  "
        f"{'RSS before':>12} {'RSS after':>12}"
    )
    print(
        f"  {'-' * max_label}  {'-' * 12}  {'-' * 14} {'-' * 14}  {'-' * 12} {'-' * 12}"
    )
    for label in detector_labels:
        sub = memory[label]
        print(
            f"  {label:<{max_label}} "
            f"{import_times[label]:>11.3f}s  "
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

    # -- Per-encoding table --
    all_encodings = sorted(
        {enc for label in detector_labels for enc in stats[label]["per_enc"]}
    )
    col_w = max(18, *(len(label) + 2 for label in detector_labels))

    print("=" * 100)
    print("PER-ENCODING ACCURACY (directional)")
    print("=" * 100)

    header = f"  {'Encoding':<25} {'Files':>5}"
    for label in detector_labels:
        header += f"  {label:>{col_w}}"
    header += f"  {'Best':>{col_w}}"
    print(header)
    sep = f"  {'-' * 25} {'-' * 5}"
    for _ in detector_labels:
        sep += f"  {'-' * col_w}"
    sep += f"  {'-' * col_w}"
    print(sep)

    # Pairwise comparison data (each other detector vs the reference detector)
    ref_label = detector_labels[0]
    pairwise: dict[str, dict[str, list]] = {}
    for label in detector_labels[1:]:
        pairwise[label] = {"ref_wins": [], "other_wins": [], "ties": []}

    for enc in all_encodings:
        t_enc = stats[ref_label]["per_enc"][enc]["total"]
        if t_enc == 0:
            continue

        row = f"  {enc:<25} {t_enc:>5}"
        best_acc = -1.0
        best_label = ""
        tied = False

        for label in detector_labels:
            s = stats[label]["per_enc"][enc]
            acc = s["correct"] / t_enc if t_enc else 0
            row += f"  {s['correct']:>{col_w - 12}}/{t_enc} = {acc:>6.1%} "
            if acc > best_acc:
                best_acc = acc
                best_label = label
                tied = False
            elif acc == best_acc:
                tied = True

        winner = "TIE" if tied else best_label
        row += f"  {winner:>{col_w}}"
        print(row)

        # Record pairwise data
        ref_acc = stats[ref_label]["per_enc"][enc]["correct"] / t_enc if t_enc else 0
        for label in detector_labels[1:]:
            other_acc = stats[label]["per_enc"][enc]["correct"] / t_enc if t_enc else 0
            if ref_acc > other_acc:
                pairwise[label]["ref_wins"].append((enc, ref_acc, other_acc, t_enc))
            elif other_acc > ref_acc:
                pairwise[label]["other_wins"].append((enc, other_acc, ref_acc, t_enc))
            else:
                pairwise[label]["ties"].append((enc, ref_acc, t_enc))

    # -- Pairwise comparisons vs reference detector --
    for label in detector_labels[1:]:
        pw = pairwise[label]

        print()
        print("=" * 100)
        print(f"PAIRWISE: {ref_label} vs {label}")
        print("=" * 100)

        rw = sorted(pw["ref_wins"], key=lambda x: x[1] - x[2], reverse=True)
        print(f"\n  {ref_label} wins ({len(rw)} encodings):")
        for enc, r_acc, o_acc, t_enc in rw:
            diff = r_acc - o_acc
            print(
                f"    {enc:<25} {ref_label}={r_acc:>6.1%}  "
                f"{label}={o_acc:>6.1%}  delta={diff:>+6.1%}  ({t_enc} files)"
            )

        ow = sorted(pw["other_wins"], key=lambda x: x[1] - x[2], reverse=True)
        print(f"\n  {label} wins ({len(ow)} encodings):")
        for enc, o_acc, r_acc, t_enc in ow:
            diff = o_acc - r_acc
            print(
                f"    {enc:<25} {label}={o_acc:>6.1%}  "
                f"{ref_label}={r_acc:>6.1%}  delta={diff:>+6.1%}  ({t_enc} files)"
            )

        ti = pw["ties"]
        print(f"\n  Tied ({len(ti)} encodings):")
        for enc, acc, t_enc in ti:
            print(f"    {enc:<25} both={acc:>6.1%}  ({t_enc} files)")

    # -- Failure details --
    for label in detector_labels:
        failures = stats[label]["failures"]
        print()
        print("=" * 100)
        print(f"{label.upper()} FAILURES ({len(failures)} total)")
        print("=" * 100)
        for f in failures[:80]:
            print(f)
        if len(failures) > 80:
            print(f"  ... and {len(failures) - 80} more")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare chardet-rewrite vs charset-normalizer "
        "(and optionally old chardet versions) on the chardet test suite.",
    )
    parser.add_argument(
        "-c",
        "--chardet-version",
        action="append",
        default=[],
        metavar="X.Y.Z",
        help="Old chardet version to include (repeatable, e.g. -c 6.0.0 -c 5.2.0)",
    )
    parser.add_argument(
        "--cchardet",
        action="store_true",
        default=False,
        help="Include cchardet (faust-cchardet) in the comparison",
    )
    parser.add_argument(
        "--cn-variants",
        action="store_true",
        default=False,
        help="Include charset-normalizer pure-Python subprocess variant",
    )
    parser.add_argument(
        "--pure",
        action="store_true",
        default=False,
        help="Ensure chardet-rewrite venv is pure Python (strips HATCH_BUILD_HOOK_ENABLE_MYPYC, "
        "propagates --pure to subprocesses to abort if .so/.pyd files are found)",
    )
    args = parser.parse_args()

    # Force line-buffered stdout so progress is visible when piped (e.g. tee).
    sys.stdout.reconfigure(line_buffering=True)

    data_dir = Path(__file__).resolve().parent.parent / "tests" / "data"
    if not data_dir.is_dir():
        print(f"ERROR: Test data directory not found: {data_dir}")
        sys.exit(1)

    project_root = str(Path(__file__).resolve().parent.parent)

    # When --pure, strip the mypyc build hook env var so the chardet-rewrite
    # venv is guaranteed to be pure Python even if the caller has it set.
    install_env: dict[str, str] | None = None
    if args.pure:
        install_env = {
            k: v for k, v in os.environ.items() if k != "HATCH_BUILD_HOOK_ENABLE_MYPYC"
        }

    # Create temporary venvs for ALL detectors (including chardet-rewrite)
    # so every detector runs in an isolated subprocess under identical conditions.
    # label -> (venv_dir, python_path)
    venvs: dict[str, tuple[Path, Path]] = {}
    try:
        print("Setting up chardet-rewrite venv ...")
        venv_dir, python_path = _create_detector_venv(
            "chardet-rewrite", [project_root], env=install_env
        )
        venvs["chardet-rewrite"] = (venv_dir, python_path)

        if args.chardet_version:
            print("Setting up external chardet venvs ...")
        for version in args.chardet_version:
            venv_dir, python_path = _create_detector_venv(
                f"chardet {version}", [f"chardet=={version}"]
            )
            venvs[f"chardet {version}"] = (venv_dir, python_path)

        # extra_detectors: list of (label, detector_type, venv_python)
        extra_detectors: list[tuple[str, str, Path]] = []

        # Always create an isolated charset-normalizer (mypyc) venv
        print("Setting up charset-normalizer venv ...")
        cn_label = "charset-normalizer"
        try:
            venv_dir, python_path = _create_detector_venv(
                cn_label, ["charset-normalizer"]
            )
            venvs[cn_label] = (venv_dir, python_path)
        except subprocess.CalledProcessError as exc:
            print(f"  WARNING: failed to create venv for {cn_label}: {exc}")

        if args.cn_variants:
            print("Setting up charset-normalizer pure-Python venv ...")
            label = "charset-normalizer (pure)"
            try:
                venv_dir, python_path = _create_detector_venv(
                    label,
                    ["charset-normalizer", "--no-binary", "charset-normalizer"],
                )
                venvs[label] = (venv_dir, python_path)
                extra_detectors.append((label, "charset-normalizer", python_path))
            except subprocess.CalledProcessError as exc:
                print(f"  WARNING: failed to create venv for {label}: {exc}")

        if args.cchardet:
            print("Setting up cchardet venv ...")
            label = "cchardet"
            try:
                venv_dir, python_path = _create_detector_venv(label, ["faust-cchardet"])
                venvs[label] = (venv_dir, python_path)
                extra_detectors.append((label, "cchardet", python_path))
            except subprocess.CalledProcessError as exc:
                print(f"  WARNING: failed to create venv for {label}: {exc}")

        # Build unified detector list: (label, detector_type, python_exe, encoding_era)
        detectors: list[tuple[str, str, str, str]] = [
            ("chardet-rewrite", "chardet", str(venvs["chardet-rewrite"][1]), "all"),
        ]
        if cn_label in venvs:
            detectors.append(
                (cn_label, "charset-normalizer", str(venvs[cn_label][1]), "none")
            )
        for version in args.chardet_version:
            label = f"chardet {version}"
            if label in venvs:
                era = "all" if int(version.split(".")[0]) >= 6 else "none"
                detectors.append((label, "chardet", str(venvs[label][1]), era))
        for label, det_type, python_path in extra_detectors:
            detectors.append((label, det_type, str(python_path), "none"))

        run_comparison(data_dir, detectors, pure=args.pure)
    finally:
        for label, (venv_dir, _) in venvs.items():
            print(f"  Cleaning up venv for {label} ...")
            _cleanup_venv(venv_dir)
