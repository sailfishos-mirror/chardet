# Historical Performance Table — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add charade support to `compare_detectors.py` and produce a historical performance table in `docs/performance.rst` covering every Python 3-compatible chardet/charade release.

**Architecture:** Extend `benchmark_time.py` and `compare_detectors.py` to handle `charade` as a detector type (different package/import name, same API). Fix old-chardet compatibility in `benchmark_time.py` so versions < 5.x work without `should_rename_legacy`. Run benchmarks in two passes (pure for old versions, mypyc for 7+), then assemble the table.

**Tech Stack:** Python, uv, Sphinx RST

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `scripts/benchmark_time.py` | Add charade detector branch, fix old-chardet compat |
| Modify | `scripts/compare_detectors.py` | Add `--charade` CLI flag and charade detector type support |
| Modify | `docs/performance.rst` | Add Historical Performance section |

---

### Task 1: Add charade and old-chardet support to `benchmark_time.py`

The benchmark subprocess script needs to handle `charade` as a detector
type and stop passing kwargs that don't exist on old chardet versions.

**Files:**
- Modify: `scripts/benchmark_time.py:42-64`

- [ ] **Step 1: Test that charade 1.0.3 fails with current benchmark_time.py**

Create a temp venv and verify the failure:

```bash
uv venv /tmp/charade-test --python 3.14 && uv pip install --python /tmp/charade-test/bin/python charade==1.0.3
/tmp/charade-test/bin/python scripts/benchmark_time.py --detector chardet --encoding-era none --json-only --data-dir tests/data 2>&1 | head -5
```

Expected: Fails because `charade` is not `chardet` (import error or wrong
kwargs). Clean up after:

```bash
rm -rf /tmp/charade-test
```

- [ ] **Step 2: Add charade detector branch and fix old-chardet compat**

In `scripts/benchmark_time.py`, replace the chardet/cchardet/charset-normalizer
detector branches (lines 42–83) with updated code that:
1. Adds a `"charade"` branch (same as old chardet — just `detect(data)`)
2. Fixes the `encoding_era == "none"` chardet branch to not pass
   `should_rename_legacy` (which doesn't exist on chardet < 5.x)

Replace this block in `scripts/benchmark_time.py` (lines 42–83):

```python
    if args.detector == "chardet" and args.encoding_era != "none":
        t0 = time.perf_counter()
        import chardet  # noqa: PLC0415
        from chardet.enums import EncodingEra  # noqa: PLC0415

        import_time = time.perf_counter() - t0
        era = EncodingEra.ALL if args.encoding_era == "all" else EncodingEra.MODERN_WEB

        # Use should_rename_legacy for backward compat with older chardet
        # versions in compare_detectors (prefer_superset doesn't exist in 7.0.1).
        def detect(data: bytes) -> tuple[str | None, str | None]:
            r = chardet.detect(data, encoding_era=era, should_rename_legacy=True)
            return r["encoding"], r["language"]

    elif args.detector == "chardet":
        t0 = time.perf_counter()
        import chardet  # noqa: PLC0415

        import_time = time.perf_counter() - t0

        def detect(data: bytes) -> tuple[str | None, str | None]:
            r = chardet.detect(data, should_rename_legacy=True)
            return r["encoding"], r["language"]

    elif args.detector == "cchardet":
        t0 = time.perf_counter()
        import cchardet  # noqa: PLC0415

        import_time = time.perf_counter() - t0

        def detect(data: bytes) -> tuple[str | None, str | None]:
            return cchardet.detect(data)["encoding"], None

    else:
        t0 = time.perf_counter()
        import charset_normalizer  # noqa: PLC0415

        import_time = time.perf_counter() - t0

        def detect(data: bytes) -> tuple[str | None, str | None]:
            r = charset_normalizer.detect(data)
            return r["encoding"], r["language"]
```

With:

```python
    if args.detector == "chardet" and args.encoding_era != "none":
        t0 = time.perf_counter()
        import chardet  # noqa: PLC0415
        from chardet.enums import EncodingEra  # noqa: PLC0415

        import_time = time.perf_counter() - t0
        era = EncodingEra.ALL if args.encoding_era == "all" else EncodingEra.MODERN_WEB

        # Use should_rename_legacy for backward compat with older chardet
        # versions in compare_detectors (prefer_superset doesn't exist in 7.0.1).
        def detect(data: bytes) -> tuple[str | None, str | None]:
            r = chardet.detect(data, encoding_era=era, should_rename_legacy=True)
            return r["encoding"], r["language"]

    elif args.detector == "chardet":
        # Old chardet (< 6.0) — no encoding_era support.
        # Try should_rename_legacy (5.x+), fall back to plain detect (3.x/4.x).
        t0 = time.perf_counter()
        import chardet  # noqa: PLC0415

        import_time = time.perf_counter() - t0

        import inspect  # noqa: PLC0415

        _has_rename = "should_rename_legacy" in inspect.signature(chardet.detect).parameters

        def detect(data: bytes) -> tuple[str | None, str | None]:
            if _has_rename:
                r = chardet.detect(data, should_rename_legacy=True)
            else:
                r = chardet.detect(data)
            return r["encoding"], r.get("language")

    elif args.detector == "charade":
        t0 = time.perf_counter()
        import charade  # noqa: PLC0415

        import_time = time.perf_counter() - t0

        def detect(data: bytes) -> tuple[str | None, str | None]:
            r = charade.detect(data)
            return r["encoding"], r.get("language")

    elif args.detector == "cchardet":
        t0 = time.perf_counter()
        import cchardet  # noqa: PLC0415

        import_time = time.perf_counter() - t0

        def detect(data: bytes) -> tuple[str | None, str | None]:
            return cchardet.detect(data)["encoding"], None

    else:
        t0 = time.perf_counter()
        import charset_normalizer  # noqa: PLC0415

        import_time = time.perf_counter() - t0

        def detect(data: bytes) -> tuple[str | None, str | None]:
            r = charset_normalizer.detect(data)
            return r["encoding"], r["language"]
```

Key changes:
- `charade` branch: imports `charade` instead of `chardet`, uses plain
  `detect(data)` with `r.get("language")` (charade may not always return it).
- Old chardet branch: uses `inspect.signature` to check if
  `should_rename_legacy` exists before passing it. Uses `r.get("language")`
  since old chardet may not include it.

- [ ] **Step 3: Add charade to `--detector` choices in utils.py**

In `scripts/utils.py:216-220`, add `"charade"` to the choices list:

```python
        "--detector",
        choices=["chardet", "charset-normalizer", "cchardet", "charade"],
        default="chardet",
        help="Detector library to benchmark (default: chardet)",
    )
```

- [ ] **Step 4: Verify charade works with benchmark_time.py**

```bash
uv venv /tmp/charade-test --python 3.14 && uv pip install --python /tmp/charade-test/bin/python charade==1.0.3
/tmp/charade-test/bin/python scripts/benchmark_time.py --detector charade --encoding-era none --json-only --data-dir tests/data 2>&1 | head -5
rm -rf /tmp/charade-test
```

Expected: JSON output lines with detection results (may have low accuracy,
that's fine — we just need it to not crash).

- [ ] **Step 5: Lint and commit**

```bash
uv run ruff check scripts/benchmark_time.py
uv run ruff format scripts/benchmark_time.py
git add scripts/benchmark_time.py scripts/utils.py
git commit -m "feat: add charade support and old-chardet compat to benchmark_time.py"
```

---

### Task 2: Add charade support to `compare_detectors.py`

Add `--charade` CLI flag and wire up charade as a detector type through the
venv creation, version resolution, and benchmark pipelines.

**Files:**
- Modify: `scripts/compare_detectors.py`

- [ ] **Step 1: Add charade to module mappings**

In `_get_detector_version()` (line ~213), add charade to the module dict:

```python
    module = {
        "chardet": "chardet",
        "charset-normalizer": "charset_normalizer",
        "cchardet": "cchardet",
        "charade": "charade",
    }[detector_type]
```

In `_get_build_tag()` (line ~265), add charade to the module dict:

```python
    module = {
        "chardet": "chardet",
        "charset-normalizer": "charset_normalizer",
        "cchardet": "cchardet",
        "charade": "charade",
    }[detector_type]
```

- [ ] **Step 2: Add charade to `_resolve_version_without_venv()`**

In the PyPI package name mapping (line ~331), add charade:

```python
    pkg_name = {
        "charset-normalizer": "charset-normalizer",
        "cchardet": "faust-cchardet",
        "chardet": "chardet",
        "charade": "charade",
    }.get(detector_type, detector_type)
```

- [ ] **Step 3: Add charade to encoding_era logic**

In the detector list building section (line ~1503), charade should always
use `encoding_era="none"` since it predates encoding era support. Update
the condition:

```python
            if det_type == "chardet":
                try:
                    era = "all" if int(version.split(".")[0]) >= 6 else "none"
                except ValueError:
                    era = "all"
            else:
                era = "none"
```

No change needed — charade already falls into the `else: era = "none"` branch
since `det_type` will be `"charade"`, not `"chardet"`.

- [ ] **Step 4: Add `--charade` CLI argument**

After the `--cchardet` argument (line ~1553), add:

```python
    parser.add_argument(
        "--charade",
        action="append",
        default=[],
        metavar="VERSION",
        help="Charade version to include (repeatable, e.g. --charade 1.0.3)",
    )
```

- [ ] **Step 5: Add charade venv specs in `_run_for_python_version()`**

After the `args.chardet_version` loop (line ~1354), add the charade loop:

```python
    for version in args.charade:
        venv_specs.append(
            (f"charade {version}", [f"charade=={version}"], None, "charade", python_version)
        )
```

- [ ] **Step 6: Add charade to `_predict_build_tag()`**

In `_predict_build_tag()` (line ~353), charade is always pure Python. Add
it before the return statement. The existing logic already returns `"pure"`
for unknown detector types, but to be explicit, add charade to the docstring
and ensure it returns `"pure"`:

After the `if pure: return "pure"` block, add:

```python
    if detector_type == "charade":
        return "pure"
```

- [ ] **Step 7: Handle charade in `_run_timing_subprocess` docstring**

Update the docstring for `_run_timing_subprocess()` (line ~523) to mention
charade:

```python
        One of ``"chardet"``, ``"charset-normalizer"``, ``"cchardet"``, or ``"charade"``.
```

- [ ] **Step 8: Lint and commit**

```bash
uv run ruff check scripts/compare_detectors.py
uv run ruff format scripts/compare_detectors.py
git add scripts/compare_detectors.py
git commit -m "feat: add --charade flag to compare_detectors.py"
```

---

### Task 3: Run the benchmarks

Run the two-pass benchmarks to collect all historical data. This task is
mostly running commands and waiting.

- [ ] **Step 1: Run Pass 1 — pure Python (old versions)**

```bash
uv run python scripts/compare_detectors.py \
  --charade 1.0.0 --charade 1.0.1 --charade 1.0.2 --charade 1.0.3 \
  -c 2.2.1 -c 2.3.0 \
  -c 3.0.0 -c 3.0.1 -c 3.0.2 -c 3.0.3 -c 3.0.4 \
  -c 4.0.0 \
  -c 5.0.0 -c 5.1.0 -c 5.2.0 \
  -c 6.0.0 \
  --pure
```

This will take a while — old chardet is slow (~12 files/s for 6.0.0,
potentially slower for older versions). Monitor output for any failures.

If chardet 2.2.1 or 2.3.0 fail to install, remove them from the command
and note they're not testable.

- [ ] **Step 2: Run Pass 2 — mypyc (v7+)**

```bash
uv run python scripts/compare_detectors.py --mypyc
```

This benchmarks the current local chardet with mypyc compilation.

- [ ] **Step 3: Record all results**

Results are cached in `.benchmark_results/`. Collect accuracy and speed
numbers from the terminal output for each version. Record in a temporary
file for the next task:

For each version, note:
- Correct count (e.g., 2219/2517)
- Accuracy percentage
- Files/s throughput
- Language accuracy (if available — old versions may return `None`)

- [ ] **Step 4: Identify versions to prune**

Compare adjacent patch versions. If accuracy AND speed are identical
(or within noise), keep only the latest of the group and note the range
in the table (e.g., "3.0.1–3.0.4" if they're all the same).

---

### Task 4: Add the historical table to `performance.rst`

**Files:**
- Modify: `docs/performance.rst`

- [ ] **Step 1: Add the Historical Performance section**

Insert after the "Optional mypyc Compilation" section (after line 275)
and before "Performance Across Python Versions" (line 277). Use the
actual numbers collected in Task 3.

The section structure:

```rst
Historical Performance
----------------------

Accuracy and speed of every Python 3-compatible chardet release and its
predecessor charade_, measured on the same 2,517-file test suite with the
same equivalence rules. Pure Python on CPython 3.14 for versions before
7.0; mypyc-compiled for 7.0+, matching what ``pip install chardet``
delivers.

.. _charade: https://pypi.org/project/charade/

.. list-table::
   :header-rows: 1
   :widths: 20 12 10 10 10 10

   * - Version
     - Date
     - Correct
     - Accuracy
     - Files/s
     - Language
   * - charade 1.0.0
     - 2012-12
     - ???/2517
     - ???%
     - ???
     - ???%
```

Fill in the actual numbers from the benchmark run. The date column uses
YYYY-MM format. Language column shows "—" if the version doesn't support
language detection.

For the current chardet version, bold it and add "(mypyc)" suffix.

- [ ] **Step 2: Build docs to verify rendering**

```bash
uv run sphinx-build -W docs docs/_build
```

Expected: No warnings, table renders correctly.

- [ ] **Step 3: Commit**

```bash
git add docs/performance.rst
git commit -m "docs: add historical performance table to performance.rst"
```

---

### Task 5: Clean up spec/plan files

Remove the spec and plan from the docs directory (preserved in git history).

- [ ] **Step 1: Remove spec and plan**

```bash
git rm docs/superpowers/specs/2026-03-26-historical-performance-table-design.md
git rm docs/superpowers/plans/2026-03-26-historical-performance-table.md
git commit -m "docs: remove historical performance table spec/plan (preserved in git history)"
```
