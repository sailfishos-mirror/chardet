# Historical Performance Table

## Summary

Add a "Historical Performance" section to `docs/performance.rst` showing
accuracy and speed for every Python 3-compatible chardet release and its
predecessor charade, measured on the same 2,517-file test suite with the
same equivalence rules.

## Changes

### 1. Add charade support to `compare_detectors.py`

Add `"charade"` as a detector type. The only differences from chardet:

- **Package name:** `charade` (installed via `pip install charade==X.Y.Z`)
- **Import name:** `charade` (not `chardet`)
- **API:** identical — `charade.detect(data)` returns the same dict format

Changes required:

- Add `"charade"` to the module mapping in `_get_detector_version()`:
  ```python
  module = {
      "chardet": "chardet",
      "charset-normalizer": "charset_normalizer",
      "cchardet": "cchardet",
      "charade": "charade",
  }[detector_type]
  ```
- Add `--charade` CLI argument (repeatable, like `--chardet-version`):
  ```
  --charade VERSION   Charade version to include (repeatable)
  ```
- Add charade venv specs in `_run_for_python_version()`, analogous to
  how `--chardet-version` adds extra chardet venvs.
- Update `_resolve_version_without_venv()` to handle charade package name.
- Update the benchmark subprocess scripts (`benchmark_time.py`) to accept
  charade as a detector type. The subprocess import logic needs to handle
  `import charade` and use `charade.detect()`.

### 2. Run benchmarks in two passes

**Pass 1 — Pure Python (old versions):**
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

**Pass 2 — mypyc (v7+ versions):**
```bash
uv run python scripts/compare_detectors.py --mypyc
```

Results are cached in `.benchmark_results/` and keyed by version + build
tag, so the two passes don't conflict.

### 3. Add table to `performance.rst`

New section "Historical Performance" after the existing "Optional mypyc
Compilation" section and before "Performance Across Python Versions".

Single chronological table:

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
     - .../2517
     - ...%
     - ...
     - ...%
   ...
   * - **chardet 7.x.x (mypyc)**
     - 2026-03
     - **2499/2517**
     - **99.3%**
     - **551**
     - **95.7%**
```

After collecting results, prune rows where a patch version has identical
accuracy and speed to its adjacent version (e.g., if 3.0.1 and 3.0.2
are identical, keep only one and note "3.0.1–3.0.2" or just the latest).

### 4. Versions that might fail

- **chardet 2.2.1 and 2.3.0:** First Python 3 support, predates
  universal wheels. The sdist may have syntax issues on Python 3.10+.
  If they fail to install, skip them and note "not installable on
  Python 3.14" in the table or omit them.
- **charade 1.0.0–1.0.3:** sdist-only, targeted Python 2+3 in 2012.
  May have minor compatibility issues. Same approach — try, skip if broken.

## Out of scope

- Memory benchmarks for historical versions
- chardet 1.0, 1.0.1, 1.1, 2.1.1 (Python 2 only, not testable)
- Changes to existing benchmark tables (they remain as-is)
- Automating the two-pass run into a single command
