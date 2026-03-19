# Char-Dataset Accuracy Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `scripts/benchmark_char_dataset.py` — a standalone script that fairly compares chardet vs charset-normalizer accuracy on the char-dataset using 4 scoring tiers.

**Architecture:** Single script file with helper functions for data acquisition, detection, scoring, and reporting. chardet runs via direct import; charset-normalizer runs in an isolated `uv` venv subprocess. Scoring uses chardet's existing `equivalences.py` for both libraries.

**Tech Stack:** Python 3.10+, chardet (direct import), charset-normalizer (subprocess via uv venv), `codecs.lookup()` for encoding normalization.

**Spec:** `docs/superpowers/specs/2026-03-19-char-dataset-benchmark-design.md`

---

### Task 1: Add gitignore entries

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add `.char-dataset/` and `.char-dataset-results/` to `.gitignore`**

Append to `.gitignore`:

```
.char-dataset/
.char-dataset-results/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore char-dataset benchmark directories"
```

---

### Task 2: Data acquisition — clone and collect files

**Files:**
- Create: `scripts/benchmark_char_dataset.py`

- [ ] **Step 1: Write test for `collect_char_dataset_files()`**

Write to `/tmp/test_collect.py`:

```python
"""Quick smoke test for collect_char_dataset_files()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "repos" / "chardet" / "scripts"))
from benchmark_char_dataset import collect_char_dataset_files, clone_char_dataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "repos" / "chardet"
dataset_dir = PROJECT_ROOT / ".char-dataset"

# Clone if needed
clone_char_dataset(dataset_dir)
assert dataset_dir.is_dir(), "char-dataset not cloned"

# Collect
files = collect_char_dataset_files(dataset_dir)
assert len(files) > 400, f"Expected 400+ files, got {len(files)}"

# Check structure
for expected_enc, filepath in files:
    assert filepath.is_file(), f"Not a file: {filepath}"
    # None-encoding files come from the None directory
    if expected_enc is not None:
        assert isinstance(expected_enc, str), f"Bad encoding type: {type(expected_enc)}"

# Check that None directory is handled
none_files = [f for enc, f in files if enc is None]
assert len(none_files) > 0, "No None-directory files found"

print(f"OK: {len(files)} files collected, {len(none_files)} binary/None files")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python /tmp/test_collect.py`
Expected: FAIL with ImportError (module doesn't exist yet)

- [ ] **Step 3: Write the script skeleton with data acquisition**

Create `scripts/benchmark_char_dataset.py` with:

```python
#!/usr/bin/env python
"""Compare chardet vs charset-normalizer accuracy on the char-dataset.

The char-dataset (https://github.com/Ousret/char-dataset) is charset-normalizer's
own test corpus.  This script runs both libraries against it with four scoring
tiers to show how methodology choice affects reported accuracy numbers.

Tiers:
  1. Strict single-best — exact match after codec normalization
  2. Single-best with equivalences — chardet's is_correct() + is_equivalent_detection()
  3. All-candidates strict — expected encoding anywhere in candidate list
  4. All-candidates with equivalences — any candidate passes equivalence check
"""

from __future__ import annotations

import codecs
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CHAR_DATASET_REPO = "https://github.com/Ousret/char-dataset.git"


def clone_char_dataset(dest: Path) -> None:
    """Clone or update the char-dataset repository."""
    if dest.is_dir() and any(dest.iterdir()):
        # Pull latest
        subprocess.run(
            ["git", "-C", str(dest), "pull", "--ff-only"],
            check=False,
            capture_output=True,
        )
        return
    subprocess.run(
        ["git", "clone", "--depth=1", _CHAR_DATASET_REPO, str(dest)],
        check=True,
        capture_output=True,
    )


def _normalize_codec(name: str) -> str:
    """Normalize an encoding name to Python's canonical codec name."""
    return codecs.lookup(name).name


def collect_char_dataset_files(
    dataset_dir: Path,
) -> list[tuple[str | None, Path]]:
    """Collect (expected_encoding, filepath) tuples from char-dataset.

    Directory names are Python codec names (e.g., 'iso8859_1', 'utf_8').
    The 'None' directory contains binary files (expected_encoding=None).
    """
    files: list[tuple[str | None, Path]] = []
    for encoding_dir in sorted(dataset_dir.iterdir()):
        if not encoding_dir.is_dir() or encoding_dir.name.startswith("."):
            continue

        dirname = encoding_dir.name
        if dirname == "None":
            expected: str | None = None
        else:
            try:
                expected = _normalize_codec(dirname)
            except LookupError:
                print(
                    f"ERROR: Unknown encoding directory '{dirname}' — "
                    f"char-dataset structure may have changed",
                    file=sys.stderr,
                )
                sys.exit(1)

        files.extend(
            (expected, filepath)
            for filepath in sorted(encoding_dir.iterdir())
            if filepath.is_file()
        )
    return files
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python /tmp/test_collect.py`
Expected: PASS — prints "OK: NNN files collected, N binary/None files"

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmark_char_dataset.py
git commit -m "feat: add char-dataset benchmark script skeleton with data acquisition"
```

---

### Task 3: Chardet detection and Tier 1-2 scoring

**Files:**
- Modify: `scripts/benchmark_char_dataset.py`

- [ ] **Step 1: Write test for chardet scoring**

Write to `/tmp/test_chardet_scoring.py`:

```python
"""Smoke test: run chardet against char-dataset and print tier 1-2 scores."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "repos" / "chardet" / "scripts"))
from benchmark_char_dataset import (
    clone_char_dataset,
    collect_char_dataset_files,
    run_chardet,
    score_results,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "repos" / "chardet"
dataset_dir = PROJECT_ROOT / ".char-dataset"
clone_char_dataset(dataset_dir)
files = collect_char_dataset_files(dataset_dir)

results = run_chardet(files)
assert len(results) == len(files), f"Result count mismatch: {len(results)} vs {len(files)}"

scores = score_results(files, results)
print(f"Tier 1 (strict best):    {scores.tier1}/{scores.total} = {scores.tier1/scores.total:.1%}")
print(f"Tier 2 (best + equiv):   {scores.tier2}/{scores.total} = {scores.tier2/scores.total:.1%}")
print(f"Tier 3 (all strict):     {scores.tier3}/{scores.total} = {scores.tier3/scores.total:.1%}")
print(f"Tier 4 (all + equiv):    {scores.tier4}/{scores.total} = {scores.tier4/scores.total:.1%}")

# Tier 2 should be >= Tier 1 (equivalences can only help)
assert scores.tier2 >= scores.tier1
# Tier 3 should be >= Tier 1 (more candidates can only help)
assert scores.tier3 >= scores.tier1
# Tier 4 should be >= all others
assert scores.tier4 >= scores.tier3
assert scores.tier4 >= scores.tier2

print("OK: all tier ordering invariants hold")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python /tmp/test_chardet_scoring.py`
Expected: FAIL with ImportError for `run_chardet` / `score_results`

- [ ] **Step 3: Implement chardet detection and scoring**

Add to `scripts/benchmark_char_dataset.py`:

```python
import codecs
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chardet.equivalences import is_correct, is_equivalent_detection


@dataclass(slots=True)
class DetectionResult:
    """Detection result for a single file from one library."""

    best_encoding: str | None
    best_confidence: float
    all_encodings: list[str]  # all candidate encodings (normalized)


def _normalize_detected(encoding: str | None) -> str | None:
    """Normalize a detected encoding name, returning None if unknown."""
    if encoding is None:
        return None
    try:
        return codecs.lookup(encoding).name
    except LookupError:
        return encoding.lower()


def run_chardet(
    files: list[tuple[str | None, Path]],
) -> list[DetectionResult]:
    """Run chardet.detect_all() on each file, return normalized results."""
    import chardet
    from chardet.enums import EncodingEra

    results: list[DetectionResult] = []
    for _expected, filepath in files:
        data = filepath.read_bytes()
        all_results = chardet.detect_all(data, encoding_era=EncodingEra.ALL)
        if all_results:
            best = all_results[0]
            best_enc = _normalize_detected(best["encoding"])
            best_conf = best.get("confidence", 0.0)
            all_encs = [
                _normalize_detected(r["encoding"])
                for r in all_results
                if r["encoding"] is not None
            ]
            # Deduplicate while preserving order
            seen: set[str] = set()
            unique_encs: list[str] = []
            for e in all_encs:
                if e is not None and e not in seen:
                    seen.add(e)
                    unique_encs.append(e)
            results.append(DetectionResult(best_enc, best_conf, unique_encs))
        else:
            results.append(DetectionResult(None, 0.0, []))
    return results


@dataclass(slots=True)
class TierScores:
    """Scores across all 4 tiers for one library."""

    total: int = 0
    tier1: int = 0
    tier2: int = 0
    tier3: int = 0
    tier4: int = 0
    # Per-encoding breakdowns at tier 2
    per_encoding: dict[str, dict[str, int]] = field(default_factory=dict)
    # Failure details at tier 2
    failures: list[dict] = field(default_factory=list)


def score_results(
    files: list[tuple[str | None, Path]],
    results: list[DetectionResult],
) -> TierScores:
    """Score detection results across all 4 tiers."""
    scores = TierScores()

    for (expected, filepath), result in zip(files, results, strict=True):
        scores.total += 1
        data = filepath.read_bytes()

        best_norm = result.best_encoding
        expected_norm = expected  # Already normalized by collect_char_dataset_files

        # Initialize per-encoding tracking
        enc_key = expected_norm or "None"
        if enc_key not in scores.per_encoding:
            scores.per_encoding[enc_key] = {"total": 0, "tier1": 0, "tier2": 0}
        scores.per_encoding[enc_key]["total"] += 1

        # --- Tier 1: strict single-best ---
        if expected_norm is None:
            t1_pass = best_norm is None
        else:
            t1_pass = expected_norm == best_norm
        if t1_pass:
            scores.tier1 += 1
            scores.per_encoding[enc_key]["tier1"] += 1

        # --- Tier 2: single-best with equivalences ---
        # Check is_correct and is_equivalent_detection separately so we can
        # categorize failures: "superset" means is_correct passes (so the
        # detection is structurally acceptable) but strict name match failed.
        if expected_norm is None:
            t2_pass = best_norm is None
            t2_is_correct = t2_pass
        else:
            t2_is_correct = is_correct(expected_norm, best_norm)
            t2_pass = t2_is_correct or (
                best_norm is not None
                and is_equivalent_detection(data, expected_norm, best_norm)
            )
        if t2_pass:
            scores.tier2 += 1
            scores.per_encoding[enc_key]["tier2"] += 1
        else:
            # Categorize failure
            if best_norm is None:
                category = "none_result"
            else:
                category = "wrong_family"
            scores.failures.append(
                {
                    "file": str(filepath),
                    "expected": expected_norm,
                    "detected": best_norm,
                    "confidence": result.best_confidence,
                    "category": category,
                }
            )

        # Track Tier 1 failures that Tier 2 rescued (superset/equiv detections)
        if not t1_pass and t2_pass:
            scores.failures.append(
                {
                    "file": str(filepath),
                    "expected": expected_norm,
                    "detected": best_norm,
                    "confidence": result.best_confidence,
                    "category": "superset_rescued",
                }
            )

        # --- Tier 3: all-candidates strict ---
        if expected_norm is None:
            t3_pass = best_norm is None
        else:
            t3_pass = expected_norm in result.all_encodings
        if t3_pass:
            scores.tier3 += 1

        # --- Tier 4: all-candidates with equivalences ---
        if expected_norm is None:
            t4_pass = best_norm is None
        else:
            t4_pass = any(
                is_correct(expected_norm, enc)
                or is_equivalent_detection(data, expected_norm, enc)
                for enc in result.all_encodings
            )
        if t4_pass:
            scores.tier4 += 1

    return scores
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python /tmp/test_chardet_scoring.py`
Expected: PASS — prints tier scores and "OK: all tier ordering invariants hold"

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmark_char_dataset.py
git commit -m "feat: add chardet detection and 4-tier scoring to char-dataset benchmark"
```

---

### Task 4: charset-normalizer detection via isolated venv

**Files:**
- Modify: `scripts/benchmark_char_dataset.py`

- [ ] **Step 1: Write test for charset-normalizer venv creation and detection**

Write to `/tmp/test_cn_detection.py`:

```python
"""Smoke test: create charset-normalizer venv and run detection on a few files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "repos" / "chardet" / "scripts"))
from benchmark_char_dataset import (
    clone_char_dataset,
    collect_char_dataset_files,
    create_cn_venv,
    run_charset_normalizer,
    cleanup_venv,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "repos" / "chardet"
dataset_dir = PROJECT_ROOT / ".char-dataset"
clone_char_dataset(dataset_dir)
files = collect_char_dataset_files(dataset_dir)

# Only test first 10 files for speed
test_files = files[:10]

venv_dir, cn_python, cn_version = create_cn_venv()
print(f"charset-normalizer version: {cn_version}")
assert cn_version != "unknown"

try:
    results = run_charset_normalizer(test_files, cn_python)
    assert len(results) == len(test_files)
    for r in results:
        # Should have a best encoding (or None for binary)
        assert hasattr(r, "best_encoding")
        assert hasattr(r, "all_encodings")
        assert isinstance(r.all_encodings, list)
    print(f"OK: {len(results)} results, first best={results[0].best_encoding}")
finally:
    cleanup_venv(venv_dir)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python /tmp/test_cn_detection.py`
Expected: FAIL with ImportError for `create_cn_venv` / `run_charset_normalizer`

- [ ] **Step 3: Implement charset-normalizer venv + subprocess detection**

Add to `scripts/benchmark_char_dataset.py`:

```python
import json
import os
import shutil
import tempfile


def create_cn_venv() -> tuple[Path, Path, str]:
    """Create an isolated venv with charset-normalizer installed.

    Returns (venv_dir, python_executable, version).
    """
    venv_dir = Path(tempfile.mkdtemp(prefix="cn-benchmark-"))
    print(f"  Creating charset-normalizer venv at {venv_dir} ...")
    subprocess.run(
        ["uv", "venv", "--python", sys.executable, str(venv_dir)],
        check=True,
        capture_output=True,
        text=True,
    )
    venv_python = venv_dir / "bin" / "python"
    print("  Installing charset-normalizer ...")
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(venv_python),
            "charset-normalizer",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    # Get version
    fd, tmp_path = tempfile.mkstemp(suffix=".py")
    tmp = Path(tmp_path)
    try:
        os.close(fd)
        tmp.write_text(
            "import charset_normalizer; print(charset_normalizer.__version__)"
        )
        result = subprocess.run(
            [str(venv_python), str(tmp)],
            capture_output=True,
            text=True,
            check=True,
        )
        version = result.stdout.strip()
    except subprocess.CalledProcessError:
        version = "unknown"
    finally:
        tmp.unlink(missing_ok=True)

    return venv_dir, venv_python, version


def cleanup_venv(venv_dir: Path) -> None:
    """Remove a temporary venv directory."""
    shutil.rmtree(venv_dir, ignore_errors=True)


_CN_DETECT_SCRIPT = """\
import json
import sys
from pathlib import Path

from charset_normalizer import detect, from_bytes

for line in sys.stdin:
    filepath = line.strip()
    if not filepath:
        continue
    data = Path(filepath).read_bytes()

    # detect() returns a dict with "encoding" and "confidence" keys
    best_result = detect(data)
    # from_bytes() returns all candidates
    all_results = from_bytes(data)

    if best_result["encoding"] is None:
        obj = {"best": None, "candidates": []}
    else:
        obj = {
            "best": {
                "encoding": best_result["encoding"],
                "confidence": best_result.get("confidence", 0.0),
            },
            "candidates": [
                {"encoding": m.encoding}
                for m in all_results
            ],
        }
    print(json.dumps(obj), flush=True)
"""


def run_charset_normalizer(
    files: list[tuple[str | None, Path]],
    cn_python: Path,
) -> list[DetectionResult]:
    """Run charset-normalizer via subprocess, return normalized results."""
    # Write helper script to temp file
    fd, script_path = tempfile.mkstemp(suffix=".py")
    tmp_script = Path(script_path)
    try:
        os.close(fd)
        tmp_script.write_text(_CN_DETECT_SCRIPT)

        # Feed file paths via stdin, one per line
        file_paths = "\n".join(str(fp) for _, fp in files) + "\n"

        result = subprocess.run(
            [str(cn_python), str(tmp_script)],
            input=file_paths,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(
                f"WARNING: charset-normalizer subprocess failed:\n{result.stderr}",
                file=sys.stderr,
            )
            return [DetectionResult(None, 0.0, []) for _ in files]

        results: list[DetectionResult] = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            obj = json.loads(line)
            if obj["best"] is None:
                results.append(DetectionResult(None, 0.0, []))
            else:
                best_enc = _normalize_detected(obj["best"]["encoding"])
                best_conf = obj["best"].get("confidence", 0.0)
                all_encs: list[str] = []
                seen: set[str] = set()
                for c in obj["candidates"]:
                    norm = _normalize_detected(c["encoding"])
                    if norm is not None and norm not in seen:
                        seen.add(norm)
                        all_encs.append(norm)
                results.append(DetectionResult(best_enc, best_conf, all_encs))

        return results
    finally:
        tmp_script.unlink(missing_ok=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python /tmp/test_cn_detection.py`
Expected: PASS — prints version and "OK: N results"

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmark_char_dataset.py
git commit -m "feat: add charset-normalizer subprocess detection to char-dataset benchmark"
```

---

### Task 5: Report output (summary table, per-encoding breakdown, failures)

**Files:**
- Modify: `scripts/benchmark_char_dataset.py`

- [ ] **Step 1: Write test for report output**

Write to `/tmp/test_report.py`:

```python
"""Smoke test: generate a chardet-only report."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "repos" / "chardet" / "scripts"))
from benchmark_char_dataset import (
    clone_char_dataset,
    collect_char_dataset_files,
    run_chardet,
    score_results,
    print_summary,
    print_per_encoding,
    print_failures,
)

import chardet

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "repos" / "chardet"
dataset_dir = PROJECT_ROOT / ".char-dataset"
clone_char_dataset(dataset_dir)
files = collect_char_dataset_files(dataset_dir)

results = run_chardet(files)
scores = score_results(files, results)

print_summary({"chardet " + chardet.__version__: scores})
print_per_encoding({"chardet " + chardet.__version__: scores})
print_failures(scores, label="chardet")

print("\nOK: report generated without errors")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python /tmp/test_report.py`
Expected: FAIL with ImportError for `print_summary`

- [ ] **Step 3: Implement report functions**

Add to `scripts/benchmark_char_dataset.py`:

```python
def print_summary(
    all_scores: dict[str, TierScores],
    *,
    tier_filter: int | None = None,
) -> None:
    """Print the summary table showing all tiers for all libraries."""
    labels = list(all_scores.keys())
    total = next(iter(all_scores.values())).total
    col_w = max(20, *(len(label) + 2 for label in labels))

    print()
    print("=" * (30 + col_w * len(labels)))
    print("ACCURACY SUMMARY")
    print("=" * (30 + col_w * len(labels)))

    header = f"  {'Tier':<28}"
    for label in labels:
        header += f"  {label:>{col_w}}"
    print(header)
    print(f"  {'-' * 28}" + f"  {'-' * col_w}" * len(labels))

    all_tiers = [
        ("Tier 1 (strict best)", "tier1", 1),
        ("Tier 2 (best + equiv)", "tier2", 2),
        ("Tier 3 (all candidates)", "tier3", 3),
        ("Tier 4 (all + equiv)", "tier4", 4),
    ]

    for tier_name, tier_key, tier_num in all_tiers:
        if tier_filter is not None and tier_num != tier_filter:
            continue
        row = f"  {tier_name:<28}"
        for label in labels:
            s = all_scores[label]
            count = getattr(s, tier_key)
            pct = count / total if total else 0
            row += f"  {count:>{col_w - 10}}/{total} = {pct:>6.1%} "
        print(row)

    print(f"\n  Total files: {total}")


def print_per_encoding(all_scores: dict[str, TierScores]) -> None:
    """Print per-encoding breakdown at Tier 2."""
    labels = list(all_scores.keys())
    col_w = max(16, *(len(label) + 2 for label in labels))

    # Collect all encodings across all libraries
    all_encs: set[str] = set()
    for scores in all_scores.values():
        all_encs.update(scores.per_encoding.keys())

    # Sort by worst chardet failure count (first library)
    first_scores = next(iter(all_scores.values()))

    def sort_key(enc: str) -> tuple[int, str]:
        pe = first_scores.per_encoding.get(enc, {"total": 0, "tier2": 0})
        return (-(pe["total"] - pe["tier2"]), enc)

    sorted_encs = sorted(all_encs, key=sort_key)

    print()
    print("=" * (30 + col_w * len(labels)))
    print("PER-ENCODING ACCURACY (Tier 2: single-best with equivalences)")
    print("=" * (30 + col_w * len(labels)))

    header = f"  {'Encoding':<25} {'Files':>5}"
    for label in labels:
        header += f"  {label:>{col_w}}"
    print(header)
    print(f"  {'-' * 25} {'-' * 5}" + f"  {'-' * col_w}" * len(labels))

    for enc in sorted_encs:
        pe_first = first_scores.per_encoding.get(enc, {"total": 0, "tier2": 0})
        total = pe_first["total"]
        if total == 0:
            continue
        row = f"  {enc:<25} {total:>5}"
        for label in labels:
            pe = all_scores[label].per_encoding.get(enc, {"total": 0, "tier2": 0})
            correct = pe["tier2"]
            pct = correct / total if total else 0
            row += f"  {correct:>{col_w - 10}}/{total} = {pct:>6.1%} "
        print(row)


def print_failures(scores: TierScores, *, label: str) -> None:
    """Print failure details grouped by category."""
    if not scores.failures:
        print(f"\n  {label}: No Tier 2 failures!")
        return

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for f in scores.failures:
        cat = f["category"]
        by_category.setdefault(cat, []).append(f)

    category_labels = {
        "none_result": "None result (no detection)",
        "wrong_family": "Wrong encoding family",
        "superset_rescued": "Superset/equivalent detection (Tier 1 fail, Tier 2 pass)",
    }

    print()
    print("=" * 80)
    print(f"{label.upper()} TIER 2 FAILURES ({len(scores.failures)} total)")
    print("=" * 80)

    for cat, cat_failures in sorted(by_category.items()):
        cat_label = category_labels.get(cat, cat)
        print(f"\n  {cat_label} ({len(cat_failures)}):")
        for f in cat_failures:
            filepath = Path(f["file"])
            short = f"{filepath.parent.name}/{filepath.name}"
            print(
                f"    {short}: expected={f['expected']}, "
                f"detected={f['detected']}, conf={f['confidence']:.2f}"
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python /tmp/test_report.py`
Expected: PASS — prints formatted report and "OK: report generated without errors"

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmark_char_dataset.py
git commit -m "feat: add report output to char-dataset benchmark"
```

---

### Task 6: CLI entry point with argument parsing

**Files:**
- Modify: `scripts/benchmark_char_dataset.py`

- [ ] **Step 1: Write test for CLI**

Write to `/tmp/test_cli.py`:

```python
"""Smoke test: run the script via CLI with --chardet-only."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "--co", "-q"],  # dummy, just test the script runs
    capture_output=True,
    text=True,
)

# Actually run the benchmark script with --chardet-only
result = subprocess.run(
    ["uv", "run", "python", "scripts/benchmark_char_dataset.py", "--chardet-only"],
    capture_output=True,
    text=True,
    timeout=300,
)
print("STDOUT:")
print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
if result.returncode != 0:
    print("STDERR:")
    print(result.stderr)
assert result.returncode == 0, f"Script failed with return code {result.returncode}"
assert "ACCURACY SUMMARY" in result.stdout
assert "Tier 1" in result.stdout
assert "Tier 2" in result.stdout
print("\nOK: CLI --chardet-only works")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python /tmp/test_cli.py`
Expected: FAIL (no CLI entry point yet)

- [ ] **Step 3: Implement CLI entry point**

Add to `scripts/benchmark_char_dataset.py`:

```python
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare chardet vs charset-normalizer accuracy "
            "on the char-dataset corpus."
        ),
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="Force re-run of charset-normalizer (ignore cached results)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        dest="json_output",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--chardet-only",
        action="store_true",
        default=False,
        help="Skip charset-normalizer (no venv setup needed)",
    )
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        help="Show results for a specific tier only (default: all)",
    )
    parser.add_argument(
        "--failures",
        action="store_true",
        default=False,
        help="Print detailed failure list",
    )
    parser.add_argument(
        "--encoding",
        default=None,
        help="Filter to a single encoding directory",
    )
    args = parser.parse_args()

    # Force line-buffered stdout
    sys.stdout.reconfigure(line_buffering=True)

    # 1. Acquire data
    dataset_dir = _PROJECT_ROOT / ".char-dataset"
    print("Acquiring char-dataset ...")
    clone_char_dataset(dataset_dir)

    files = collect_char_dataset_files(dataset_dir)
    if not files:
        print("ERROR: No files found in char-dataset!", file=sys.stderr)
        sys.exit(1)

    # Filter by encoding if requested
    if args.encoding:
        filter_enc = _normalize_codec(args.encoding)
        files = [(enc, fp) for enc, fp in files if enc == filter_enc]
        if not files:
            print(f"ERROR: No files found for encoding '{args.encoding}'", file=sys.stderr)
            sys.exit(1)
        print(f"  Filtered to {len(files)} files for {filter_enc}")

    print(f"  {len(files)} files across {len({enc for enc, _ in files})} encodings")

    # 2. Run chardet
    import chardet as chardet_module

    print(f"\nRunning chardet {chardet_module.__version__} ...")
    chardet_results = run_chardet(files)
    chardet_scores = score_results(files, chardet_results)
    chardet_label = f"chardet {chardet_module.__version__}"

    all_scores: dict[str, TierScores] = {chardet_label: chardet_scores}

    # 3. Run charset-normalizer (unless --chardet-only)
    cn_label: str | None = None
    if not args.chardet_only:
        try:
            venv_dir, cn_python, cn_version = create_cn_venv()
            cn_label = f"charset-normalizer {cn_version}"
            print(f"\nRunning {cn_label} ...")
            cn_results = run_charset_normalizer(files, cn_python)
            cn_scores = score_results(files, cn_results)
            all_scores[cn_label] = cn_scores
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(
                f"WARNING: charset-normalizer setup failed ({exc}), "
                f"continuing chardet-only",
                file=sys.stderr,
            )
            cn_label = None
        finally:
            if "venv_dir" in locals():
                cleanup_venv(venv_dir)

    # 4. Output
    if args.json_output:
        print_json_report(all_scores)
    else:
        print_summary(all_scores, tier_filter=args.tier)
        print_per_encoding(all_scores)
        if args.failures:
            print_failures(chardet_scores, label=chardet_label)
            if cn_label and cn_label in all_scores:
                print_failures(all_scores[cn_label], label=cn_label)


def print_json_report(all_scores: dict[str, TierScores]) -> None:
    """Print machine-readable JSON output."""
    output: dict = {}
    for label, scores in all_scores.items():
        output[label] = {
            "total": scores.total,
            "tier1": scores.tier1,
            "tier2": scores.tier2,
            "tier3": scores.tier3,
            "tier4": scores.tier4,
            "per_encoding": scores.per_encoding,
            "failures": scores.failures,
        }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python /tmp/test_cli.py`
Expected: PASS — prints report with ACCURACY SUMMARY and "OK: CLI --chardet-only works"

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmark_char_dataset.py
git commit -m "feat: add CLI entry point to char-dataset benchmark"
```

---

### Task 7: Caching for charset-normalizer results

**Files:**
- Modify: `scripts/benchmark_char_dataset.py`

- [ ] **Step 1: Write test for caching**

Write to `/tmp/test_caching.py`:

```python
"""Test that charset-normalizer results are cached and reused."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "repos" / "chardet" / "scripts"))
from benchmark_char_dataset import (
    clone_char_dataset,
    collect_char_dataset_files,
    create_cn_venv,
    run_charset_normalizer,
    cleanup_venv,
    load_cn_cache,
    save_cn_cache,
    _PROJECT_ROOT,
)

dataset_dir = _PROJECT_ROOT / ".char-dataset"
clone_char_dataset(dataset_dir)
files = collect_char_dataset_files(dataset_dir)[:5]

venv_dir, cn_python, cn_version = create_cn_venv()
try:
    cache_dir = _PROJECT_ROOT / ".char-dataset-results"

    # Run and cache
    results = run_charset_normalizer(files, cn_python)
    save_cn_cache(cache_dir, cn_version, files, results)

    # Load from cache
    cached = load_cn_cache(cache_dir, cn_version, files)
    assert cached is not None, "Cache miss after save"
    assert len(cached) == len(results)
    for orig, cached_r in zip(results, cached):
        assert orig.best_encoding == cached_r.best_encoding
        assert orig.all_encodings == cached_r.all_encodings

    print("OK: cache save/load round-trips correctly")
finally:
    cleanup_venv(venv_dir)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run python /tmp/test_caching.py`
Expected: FAIL with ImportError for `load_cn_cache` / `save_cn_cache`

- [ ] **Step 3: Implement caching**

Add to `scripts/benchmark_char_dataset.py`:

```python
import hashlib


def _file_content_hash(filepath: Path) -> str:
    """SHA-256 (first 12 hex chars) of a file's contents."""
    return hashlib.sha256(filepath.read_bytes()).hexdigest()[:12]


def _cache_key(cn_version: str, files: list[tuple[str | None, Path]]) -> str:
    """Build a cache key from charset-normalizer version + file list hash."""
    h = hashlib.sha256(cn_version.encode())
    for _, fp in files:
        h.update(fp.name.encode())
        h.update(_file_content_hash(fp).encode())
    return f"cn_{cn_version}_{h.hexdigest()[:12]}.json"


def save_cn_cache(
    cache_dir: Path,
    cn_version: str,
    files: list[tuple[str | None, Path]],
    results: list[DetectionResult],
) -> None:
    """Save charset-normalizer results to cache."""
    cache_dir.mkdir(exist_ok=True)
    key = _cache_key(cn_version, files)
    data = [
        {
            "best_encoding": r.best_encoding,
            "best_confidence": r.best_confidence,
            "all_encodings": r.all_encodings,
        }
        for r in results
    ]
    (cache_dir / key).write_text(json.dumps(data))


def load_cn_cache(
    cache_dir: Path,
    cn_version: str,
    files: list[tuple[str | None, Path]],
) -> list[DetectionResult] | None:
    """Load cached charset-normalizer results, or return None on miss."""
    key = _cache_key(cn_version, files)
    cache_file = cache_dir / key
    if not cache_file.is_file():
        return None
    data = json.loads(cache_file.read_text())
    if len(data) != len(files):
        return None  # Stale cache
    return [
        DetectionResult(
            best_encoding=d["best_encoding"],
            best_confidence=d["best_confidence"],
            all_encodings=d["all_encodings"],
        )
        for d in data
    ]
```

Then update `main()` to use caching — wrap the charset-normalizer section:

```python
    # In main(), replace the charset-normalizer section with:
    if not args.chardet_only:
        cache_dir = _PROJECT_ROOT / ".char-dataset-results"

        # Try to resolve version without venv for cache check
        cn_version_for_cache = _resolve_cn_version()
        cached_results = None
        if not args.no_cache and cn_version_for_cache:
            cached_results = load_cn_cache(cache_dir, cn_version_for_cache, files)

        if cached_results is not None:
            cn_label = f"charset-normalizer {cn_version_for_cache}"
            print(f"\n  Using cached results for {cn_label}")
            cn_scores = score_results(files, cached_results)
            all_scores[cn_label] = cn_scores
        else:
            try:
                venv_dir, cn_python, cn_version = create_cn_venv()
                cn_label = f"charset-normalizer {cn_version}"
                print(f"\nRunning {cn_label} ...")
                cn_results = run_charset_normalizer(files, cn_python)
                save_cn_cache(cache_dir, cn_version, files, cn_results)
                cn_scores = score_results(files, cn_results)
                all_scores[cn_label] = cn_scores
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                print(
                    f"WARNING: charset-normalizer setup failed ({exc}), "
                    f"continuing chardet-only",
                    file=sys.stderr,
                )
            finally:
                if "venv_dir" in locals():
                    cleanup_venv(venv_dir)
```

Also add a helper to resolve charset-normalizer version without a venv:

```python
def _resolve_cn_version() -> str | None:
    """Resolve charset-normalizer version without creating a venv.

    Uses ``uv pip compile`` with explicit ``--python`` to avoid environment
    ambiguity.  Returns ``None`` on any failure (cache will be skipped and
    a full venv will be created instead).
    """
    try:
        result = subprocess.run(
            [
                "uv", "pip", "compile",
                "--no-deps",
                "--python", sys.executable,
                "-",
            ],
            input="charset-normalizer",
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and "==" in line:
                return line.split("==", 1)[1]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run python /tmp/test_caching.py`
Expected: PASS — prints "OK: cache save/load round-trips correctly"

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmark_char_dataset.py
git commit -m "feat: add charset-normalizer result caching to char-dataset benchmark"
```

---

### Task 8: Lint, full integration test, and final commit

**Files:**
- Modify: `scripts/benchmark_char_dataset.py` (lint fixes only)

- [ ] **Step 1: Run linter**

Run: `uv run ruff check scripts/benchmark_char_dataset.py`
Fix any issues.

- [ ] **Step 2: Run formatter**

Run: `uv run ruff format scripts/benchmark_char_dataset.py`

- [ ] **Step 3: Run full integration test with both libraries**

Run: `uv run python scripts/benchmark_char_dataset.py --failures`
Expected: Full report with both chardet and charset-normalizer scores, failure details. Verify:
- All 4 tiers show percentages
- Per-encoding breakdown appears
- Failure categories are populated
- No Python errors

- [ ] **Step 4: Run chardet-only with --json**

Run: `uv run python scripts/benchmark_char_dataset.py --chardet-only --json | python -m json.tool`
Expected: Valid JSON output with tier scores

- [ ] **Step 5: Run with --encoding filter**

Run: `uv run python scripts/benchmark_char_dataset.py --chardet-only --encoding utf_8`
Expected: Report filtered to UTF-8 files only

- [ ] **Step 6: Commit any lint fixes**

```bash
git add scripts/benchmark_char_dataset.py
git commit -m "chore: lint and format char-dataset benchmark script"
```

- [ ] **Step 7: Verify second run uses cache**

Run: `uv run python scripts/benchmark_char_dataset.py`
Expected: charset-normalizer results loaded from cache (faster run)
