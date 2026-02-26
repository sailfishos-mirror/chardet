# Test Parallelism, Performance, and Accuracy Improvements — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Speed up the test feedback loop and push detection accuracy from 76.8% to 90%.

**Architecture:** Extract shared test-file collection into a utility, parametrize accuracy tests per-file with pytest-xdist for parallel execution, profile and optimize the detection pipeline, then iteratively improve accuracy using the faster feedback loop.

**Tech Stack:** pytest, pytest-xdist, cProfile, uv, ruff

---

### Task 1: Add pytest-xdist dependency

**Files:**
- Modify: `pyproject.toml:119-125`

**Step 1: Add pytest-xdist to dev dependencies**

In `pyproject.toml`, add `pytest-xdist` to the `[dependency-groups] dev` list:

```toml
[dependency-groups]
dev = [
    "datasets>=4.6.0",
    "pre-commit>=4.5.1",
    "pytest>=9.0.2",
    "pytest-cov>=7.0.0",
    "pytest-xdist>=3.5.0",
    "ruff>=0.15.2",
]
```

**Step 2: Install the new dependency**

Run: `uv sync`

Expected: Resolves and installs `pytest-xdist` and its dependency `execnet`.

**Step 3: Verify xdist is available**

Run: `uv run pytest --version`

Expected: Output includes pytest version. Then run:

Run: `uv run pytest -n 1 tests/test_api.py -v`

Expected: Tests run via xdist (shows `[gw0]` prefixes).

**Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add pytest-xdist for parallel test execution"
```

---

### Task 2: Extract shared _collect_test_files utility

**Files:**
- Create: `scripts/utils.py`
- Modify: `tests/conftest.py`
- Modify: `scripts/diagnose_accuracy.py`

**Step 1: Create scripts/utils.py with the shared function**

```python
"""Shared utilities for scripts and tests."""

from __future__ import annotations

from pathlib import Path


def collect_test_files(data_dir: Path) -> list[tuple[str, str, Path]]:
    """Collect (encoding, language, filepath) tuples from test data.

    Directory name format: "{encoding}-{language}" e.g. "utf-8-english",
    "iso-8859-1-french", "hz-gb-2312-chinese".

    Since all language names are single words (no hyphens), we can reliably
    split on the last hyphen to separate encoding from language.
    """
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
```

**Step 2: Update tests/conftest.py to use the shared utility and add a parametrize helper**

Replace the full contents of `tests/conftest.py` with:

```python
# tests/conftest.py
"""Shared test fixtures."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_TEST_DATA_REPO = "https://github.com/chardet/chardet.git"
_TEST_DATA_SUBDIR = "tests"

# Add scripts/ to sys.path so we can import utils
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from utils import collect_test_files  # noqa: E402


@pytest.fixture(scope="session")
def chardet_test_data_dir() -> Path:
    """Resolve chardet test data directory.

    1. If tests/data/ exists in repo, use it (post-merge scenario).
    2. Otherwise, clone from GitHub and cache locally.
    """
    repo_root = Path(__file__).parent.parent
    local_data = repo_root / "tests" / "data"
    if local_data.is_dir() and any(local_data.iterdir()):
        return local_data

    # Sparse checkout just the tests directory
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth=1",
                "--filter=blob:none",
                "--sparse",
                _TEST_DATA_REPO,
                tmp,
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "sparse-checkout", "set", _TEST_DATA_SUBDIR],
            cwd=tmp,
            check=True,
            capture_output=True,
        )
        src = Path(tmp) / _TEST_DATA_SUBDIR
        local_data.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if item.name in ("__pycache__", ".git"):
                continue
            dest = local_data / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    return local_data


def pytest_collect_file(parent, file_path):
    """Needed so xdist doesn't interfere with our custom parametrization."""


def _get_data_dir() -> Path:
    """Get the test data directory (for use at collection time, outside fixtures)."""
    repo_root = Path(__file__).parent.parent
    local_data = repo_root / "tests" / "data"
    if local_data.is_dir() and any(local_data.iterdir()):
        return local_data
    pytest.skip("No test data found — run accuracy tests once to clone data")
    return local_data  # unreachable, satisfies type checker


def pytest_generate_tests(metafunc):
    """Parametrize accuracy tests dynamically from test data on disk."""
    if "expected_encoding" in metafunc.fixturenames:
        data_dir = _get_data_dir()
        test_files = collect_test_files(data_dir)
        ids = [f"{enc}-{lang}/{fp.name}" for enc, lang, fp in test_files]
        metafunc.parametrize(
            ("expected_encoding", "language", "test_file_path"),
            test_files,
            ids=ids,
        )
```

**Step 3: Update scripts/diagnose_accuracy.py to import from utils**

Replace the `_collect_test_files` function in `scripts/diagnose_accuracy.py`
with an import. Remove lines 24-38 (the function definition) and add this
import after the existing imports:

```python
from utils import collect_test_files
```

Then replace all calls from `_collect_test_files(...)` to
`collect_test_files(...)` (one call on line 70).

**Step 4: Run existing tests to make sure nothing broke**

Run: `uv run pytest tests/test_api.py tests/test_models.py -v`

Expected: All existing tests pass.

**Step 5: Commit**

```bash
git add scripts/utils.py tests/conftest.py scripts/diagnose_accuracy.py
git commit -m "refactor: extract collect_test_files into shared scripts/utils.py"
```

---

### Task 3: Refactor test_accuracy.py for per-file parametrization

**Files:**
- Modify: `tests/test_accuracy.py`

**Step 1: Rewrite test_accuracy.py with parametrized tests**

Replace the full contents of `tests/test_accuracy.py` with:

```python
# tests/test_accuracy.py
"""Accuracy evaluation against the chardet test suite.

Each test file is parametrized as its own test case via conftest.py's
pytest_generate_tests hook. Run with `pytest -n auto` for parallel execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import chardet
from chardet.enums import EncodingEra
from chardet.equivalences import is_correct

if TYPE_CHECKING:
    from pathlib import Path


def test_detect(
    expected_encoding: str, language: str, test_file_path: Path
) -> None:
    """Detect encoding of a single test file and verify correctness."""
    data = test_file_path.read_bytes()
    result = chardet.detect(data, encoding_era=EncodingEra.ALL)
    detected = result["encoding"]

    assert is_correct(expected_encoding, detected), (
        f"expected={expected_encoding}, got={detected} "
        f"(confidence={result['confidence']:.2f}, "
        f"language={language}, file={test_file_path.name})"
    )
```

**Step 2: Run a quick sanity check (serial, limited)**

Run: `uv run pytest tests/test_accuracy.py -v --co 2>&1 | head -30`

Expected: Shows collected test IDs like
`tests/test_accuracy.py::test_detect[utf-8-english/somefile.txt]`.

**Step 3: Run accuracy tests in parallel**

Run: `uv run pytest tests/test_accuracy.py -n auto --tb=no -q 2>&1 | tail -10`

Expected: Shows `N passed, M failed` (expect ~1660 passed, ~501 failed).
Should complete significantly faster than the previous 169 seconds.

**Step 4: Verify --lf works for re-running failures**

Run: `uv run pytest tests/test_accuracy.py -n auto --lf --tb=no -q 2>&1 | tail -5`

Expected: Only the ~501 failures re-run (much faster).

**Step 5: Commit**

```bash
git add tests/test_accuracy.py
git commit -m "test: parametrize accuracy tests per-file for xdist parallelism"
```

---

### Task 4: Consolidate compare scripts

**Files:**
- Delete: `scripts/compare_strict.py`
- Delete: `scripts/compare_detectors.py`
- Create: `scripts/compare_detectors.py` (new merged version)

**Step 1: Create the merged compare_detectors.py**

Write `scripts/compare_detectors.py` combining the best parts of both
scripts. The full content:

```python
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
from utils import collect_test_files


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
# Thai encoding analysis
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
# Short input edge cases
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

    print(
        f"\n{'Input':<35} {'chardet-rewrite':<40} {'charset-normalizer':<40}"
    )
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
    all_encodings = sorted(
        set(list(chardet_per_enc.keys()) + list(cn_per_enc.keys()))
    )

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
    print(
        f"ENCODINGS WHERE charset-normalizer WINS ({len(cn_wins)} encodings)"
    )
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
```

**Step 2: Delete the old compare_strict.py**

Run: `git rm scripts/compare_strict.py`

**Step 3: Verify the merged script runs**

Run: `uv run python scripts/compare_detectors.py 2>&1 | head -20`

Expected: Shows "Found N test files" and the comparison output.

**Step 4: Commit**

```bash
git add scripts/compare_detectors.py
git commit -m "refactor: consolidate compare scripts into single compare_detectors.py"
```

---

### Task 5: Profile the detection pipeline

**Files:**
- Create: `scripts/profile_detection.py`

This is a research/profiling task. The script runs detection on all test
files under cProfile and reports the top functions by cumulative time.

**Step 1: Write the profiling script**

```python
#!/usr/bin/env python
"""Profile chardet detection on the full test suite."""

from __future__ import annotations

import cProfile
import pstats
from pathlib import Path

import chardet
from chardet.enums import EncodingEra
from utils import collect_test_files


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
```

**Step 2: Run the profiler**

Run: `uv run python scripts/profile_detection.py`

Expected: Profiling output showing the top functions by time. Study the
output to identify the actual bottlenecks.

**Step 3: Commit the profiling script**

```bash
git add scripts/profile_detection.py
git commit -m "feat: add detection profiling script"
```

---

### Task 6: Apply performance optimizations based on profiling results

**Files:**
- Likely modify: `src/chardet/models/__init__.py`
- Likely modify: `src/chardet/pipeline/statistical.py`
- Likely modify: `src/chardet/pipeline/validity.py`
- Likely modify: `src/chardet/pipeline/structural.py`

This task depends on Task 5's profiling results. The implementer should
study the profiling output and target the top bottlenecks. Based on code
inspection, the likely optimizations are:

**Candidate optimization A: Faster bigram scoring**

The current `score_bigrams` function (in `src/chardet/models/__init__.py`)
does Python-level dict lookups per byte pair. A lookup table (flat
`bytearray` or `bytes` of length 65536 indexed by `b1 << 8 | b2`) would
replace dict hash lookups with direct array indexing.

If applied, change `load_models` to build lookup tables instead of dicts:

```python
def load_models() -> dict[str, bytes]:
    """Load all bigram models as flat 64KB lookup tables."""
    # Each model is a bytes object of length 65536.
    # Index: (b1 << 8) | b2 -> weight (0-255).
    ...
```

And update `score_bigrams` to use direct indexing:

```python
def score_bigrams(data: bytes, encoding: str, models: dict[str, bytes]) -> float:
    model = models[encoding]
    score = 0
    weight_sum = 0
    for i in range(len(data) - 1):
        b1 = data[i]
        b2 = data[i + 1]
        w = 8 if (b1 > 0x7F or b2 > 0x7F) else 1
        score += model[(b1 << 8) | b2] * w
        weight_sum += 255 * w
    return score / weight_sum if weight_sum else 0.0
```

**Candidate optimization B: Remove ProcessPoolExecutor**

The `ProcessPoolExecutor` in `statistical.py` spawns worker processes that
each re-load the model file. For the typical case (fewer than ~50
candidates, small files), the spawn + IPC overhead dominates. Removing it
and scoring sequentially is likely faster.

If profiling confirms, simplify `score_candidates` to always score
sequentially:

```python
def score_candidates(
    data: bytes, candidates: tuple[EncodingInfo, ...]
) -> list[DetectionResult]:
    if not data or not candidates:
        return []
    models = load_models()
    scores = [(enc.name, score_bigrams(data, enc.name, models)) for enc in candidates]
    scores.sort(key=lambda x: x[1], reverse=True)
    max_score = scores[0][1] if scores else 0.0
    return [
        DetectionResult(encoding=name, confidence=s / max_score if max_score > 0 else 0.0, language=None)
        for name, s in scores
        if s > 0.0
    ]
```

**Candidate optimization C: Faster validity filtering**

`filter_by_validity` calls `data.decode(codec, errors="strict")` for every
candidate. This decodes the full input each time. Truncating to a prefix
(e.g., first 10KB) for validity checking would be faster for large inputs
without meaningfully changing accuracy.

**After applying optimizations:**

Run: `uv run python scripts/profile_detection.py`

Compare cumulative times to the Task 5 baseline. Then run the full accuracy
test to check no regressions:

Run: `uv run pytest tests/test_accuracy.py -n auto --tb=no -q 2>&1 | tail -5`

**Commit after each optimization that improves things:**

```bash
git add <modified files>
git commit -m "perf: <description of optimization>"
```

---

### Task 7: Accuracy iteration — diagnose and fix worst encodings

**Files:**
- Likely modify: `src/chardet/equivalences.py`
- Likely modify: `src/chardet/models/models.bin` (via retraining)
- Likely modify: `src/chardet/pipeline/orchestrator.py`
- Likely modify: `src/chardet/registry.py`
- Likely modify: `scripts/train.py` (if training changes needed)

This is an iterative task. Each iteration follows the same loop:

**Step 1: Diagnose failures**

Run: `uv run python scripts/diagnose_accuracy.py 2>&1 | head -80`

Study the output to find the worst-performing encodings. Look for:
- Encodings with 0% accuracy
- Encodings with many files where the wrong answer is consistent
  (e.g., "all cp037 files detected as cp500")
- Confusion pairs that can be resolved with equivalences

**Step 2: Fix the highest-impact encoding**

The fix depends on the failure mode:

- **Confusion between close relatives** (e.g., cp037 vs cp500): Add a
  superset or bidirectional equivalence in `src/chardet/equivalences.py`.
- **Wrong encoding family entirely** (e.g., cp437 detected as cp932):
  Retrain the model: `uv run python scripts/train.py --encodings cp437`
- **No model for encoding** (detected as None or windows-1252 fallback):
  Add training support in `scripts/train.py` and train.
- **Pipeline logic issue** (e.g., CJK false positive on Latin data):
  Tune thresholds in `src/chardet/pipeline/orchestrator.py`.

**Step 3: Verify improvement**

Run: `uv run pytest tests/test_accuracy.py -n auto --lf --tb=line -q 2>&1 | tail -10`

Check that the number of failures decreased and no new regressions appeared.

**Step 4: Commit each improvement**

```bash
git add <modified files>
git commit -m "feat: improve <encoding> accuracy — <what changed>"
```

**Step 5: Check overall progress**

Run: `uv run pytest tests/test_accuracy.py -n auto --tb=no -q 2>&1 | tail -3`

Count passed vs failed. Target: 1945+ passed (90% of 2161).

**Repeat steps 1-5 until the target is reached.** Focus on the
highest-impact encodings first (most files, worst accuracy). Common
strategies ordered by impact:

1. Add encoding equivalences (instant wins, no retraining).
2. Retrain confused encoding pairs with better language coverage.
3. Tune pipeline thresholds for systematic misclassification.
4. Add structural probing for encodings not yet covered.

---

### Task 8: Final verification and cleanup

**Files:**
- Modify: `pyproject.toml` (if any pytest config changes needed)
- Verify: all tests, scripts, profiling

**Step 1: Run full test suite**

Run: `uv run pytest -n auto --tb=short -q`

Expected: All non-accuracy tests pass. Accuracy tests show 90%+ pass rate.

**Step 2: Run comparison against charset-normalizer**

Run: `uv run python scripts/compare_detectors.py 2>&1 | grep "OVERALL"`

Expected: Shows overall accuracy numbers for both detectors.

**Step 3: Run linter**

Run: `uv run ruff check .`

Expected: No errors.

**Step 4: Final commit**

```bash
git add -u
git commit -m "chore: final cleanup after accuracy improvements"
```
