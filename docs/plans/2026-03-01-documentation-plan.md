# Documentation Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up Sphinx documentation for chardet with Furo theme, auto-published to ReadTheDocs on tag push.

**Architecture:** Sphinx with autodoc/autosummary generates API reference from existing `:param:` docstrings. Hand-written RST pages for Usage, Supported Encodings, How It Works, Performance, and FAQ. ReadTheDocs builds on tag push via `.readthedocs.yaml` v2.

**Tech Stack:** Sphinx, Furo theme, sphinx-copybutton, autodoc + autosummary, ReadTheDocs

---

### Task 1: Add docs dependencies to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add docs dependency group**

In `pyproject.toml`, add a `docs` group to `[dependency-groups]` (after the existing `dev` group):

```toml
docs = [
    "sphinx>=8.0",
    "furo>=2024.1.29",
    "sphinx-copybutton>=0.5.2",
]
```

**Step 2: Add ruff ignores for docs/conf.py**

In `[tool.ruff.lint.per-file-ignores]`, add:

```toml
"docs/conf.py" = [
    "INP001",  # not a package
    "A001",    # copyright shadows builtin
]
```

**Step 3: Add Documentation URL to project.urls**

In `[project.urls]`, add:

```toml
Documentation = "https://chardet.readthedocs.io"
```

**Step 4: Install dependencies**

Run: `uv sync --group docs`
Expected: Sphinx, Furo, and sphinx-copybutton installed successfully.

**Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "Add docs dependency group (Sphinx, Furo, sphinx-copybutton)"
```

---

### Task 2: Create Sphinx configuration and ReadTheDocs config

**Files:**
- Create: `docs/conf.py`
- Create: `.readthedocs.yaml`
- Create: `docs/requirements.txt`
- Modify: `.gitignore`

**Step 1: Create docs/conf.py**

```python
"""Sphinx configuration for chardet documentation."""

import chardet

project = "chardet"
copyright = "2025, chardet contributors"  # noqa: A001
author = "chardet contributors"
release = chardet.__version__
version = ".".join(release.split(".")[:2])

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
]

autosummary_generate = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "plans"]

html_theme = "furo"
html_static_path = ["_static"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

autodoc_member_order = "bysource"
autodoc_typehints = "description"
```

**Step 2: Create docs/requirements.txt**

This mirrors the docs dependency group for ReadTheDocs (RTD can't read
dependency-groups directly):

```
sphinx>=8.0
furo>=2024.1.29
sphinx-copybutton>=0.5.2
```

**Step 3: Create .readthedocs.yaml**

```yaml
version: 2

build:
  os: ubuntu-24.04
  tools:
    python: "3.12"

sphinx:
  configuration: docs/conf.py

python:
  install:
    - method: pip
      path: .
    - requirements: docs/requirements.txt
```

**Step 4: Add docs build artifacts to .gitignore**

Append to `.gitignore`:

```
docs/_build/
docs/_static/
docs/_templates/
docs/api/generated/
```

**Step 5: Create placeholder directories**

```bash
mkdir -p docs/_static docs/_templates
```

These empty directories are needed by Sphinx (referenced in conf.py). They
won't be committed (gitignored) but Sphinx needs them to exist locally. Add
a `.gitkeep` to `docs/_static/` if Sphinx complains, but typically the build
creates them.

Actually, on second thought: Sphinx won't error if these directories don't
exist, it just won't copy anything. Skip `.gitkeep`.

**Step 6: Commit**

```bash
git add docs/conf.py docs/requirements.txt .readthedocs.yaml .gitignore
git commit -m "Add Sphinx configuration and ReadTheDocs config"
```

---

### Task 3: Create index.rst and verify Sphinx builds

**Files:**
- Create: `docs/index.rst`

**Step 1: Create docs/index.rst**

```rst
chardet documentation
=====================

**chardet** is a universal character encoding detector for Python. It analyzes
byte strings and returns the detected encoding, confidence score, and language.

.. code-block:: python

   import chardet

   result = chardet.detect(b"\xc3\xa9\xc3\xa0\xc3\xbc")
   print(result)
   # {'encoding': 'utf-8', 'confidence': 0.99, 'language': 'French'}

chardet is a drop-in replacement for previous versions with the same package
name and public API. Python 3.10+, zero runtime dependencies.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   usage
   supported-encodings
   how-it-works
   performance
   faq
   api/index
```

**Step 2: Build docs to verify Sphinx works**

Run: `uv run sphinx-build -W docs docs/_build`

The `-W` flag turns warnings into errors. Expected: Build succeeds (the
toctree entries don't exist yet, so there will be warnings — remove the
`-W` for this first build).

Run: `uv run sphinx-build docs docs/_build`
Expected: Build completes. Warnings about missing toctree entries are OK.

**Step 3: Open docs/_build/index.html to verify it renders**

Run: `open docs/_build/index.html` (macOS) or visually inspect.

**Step 4: Commit**

```bash
git add docs/index.rst
git commit -m "Add docs landing page (index.rst)"
```

---

### Task 4: Write usage.rst

**Files:**
- Create: `docs/usage.rst`

**Step 1: Create docs/usage.rst**

```rst
Usage
=====

Installation
------------

.. code-block:: bash

   pip install chardet

Basic Detection
---------------

Use :func:`chardet.detect` to detect the encoding of a byte string:

.. code-block:: python

   import chardet

   result = chardet.detect(b"\xc3\xa9\xc3\xa0\xc3\xbc")
   print(result)
   # {'encoding': 'utf-8', 'confidence': 0.99, 'language': 'French'}

The result is a dictionary with three keys:

- ``"encoding"`` — the detected encoding name (e.g., ``"utf-8"``,
  ``"windows-1252"``), or ``None`` if detection failed
- ``"confidence"`` — a float between 0 and 1
- ``"language"`` — the detected language (e.g., ``"French"``), or ``None``

Multiple Candidates
~~~~~~~~~~~~~~~~~~~

Use :func:`chardet.detect_all` to get all candidate encodings ranked by
confidence:

.. code-block:: python

   results = chardet.detect_all(data)
   for r in results:
       print(f"{r['encoding']}: {r['confidence']:.2f}")

By default, results below the minimum confidence threshold (0.20) are
filtered out. Pass ``ignore_threshold=True`` to see all candidates.

Streaming Detection
-------------------

For large files or streaming data, use :class:`chardet.UniversalDetector`:

.. code-block:: python

   from chardet import UniversalDetector

   detector = UniversalDetector()
   with open("somefile.txt", "rb") as f:
       for line in f:
           detector.feed(line)
           if detector.done:
               break
   detector.close()
   print(detector.result)

Call :meth:`~chardet.UniversalDetector.reset` to reuse the detector for
another file.

Encoding Eras
-------------

By default, chardet only considers modern web encodings. Use the
``encoding_era`` parameter to broaden the search:

.. code-block:: python

   from chardet import detect, EncodingEra

   # Default: only modern web encodings
   result = detect(data)

   # Include legacy ISO, Mac, DOS, and mainframe encodings
   result = detect(data, encoding_era=EncodingEra.ALL)

   # Only legacy ISO encodings
   result = detect(data, encoding_era=EncodingEra.LEGACY_ISO)

Available eras (can be combined with ``|``):

- :attr:`~chardet.EncodingEra.MODERN_WEB` — UTF-8, Windows codepages,
  CJK encodings (default)
- :attr:`~chardet.EncodingEra.LEGACY_ISO` — ISO-8859 family
- :attr:`~chardet.EncodingEra.LEGACY_MAC` — Mac encodings
- :attr:`~chardet.EncodingEra.LEGACY_REGIONAL` — Regional codepages
  (KOI8-T, KZ-1048, etc.)
- :attr:`~chardet.EncodingEra.DOS` — DOS codepages (CP437, CP850, etc.)
- :attr:`~chardet.EncodingEra.MAINFRAME` — EBCDIC encodings
- :attr:`~chardet.EncodingEra.ALL` — All of the above

Limiting Bytes
--------------

By default, chardet examines up to 200,000 bytes. Use ``max_bytes`` to
adjust:

.. code-block:: python

   # Examine only the first 10 KB
   result = chardet.detect(data, max_bytes=10_000)

Smaller values are faster but may reduce accuracy for encodings that
require more data to distinguish.

Command-Line Tool
-----------------

chardet includes a ``chardetect`` command:

.. code-block:: bash

   # Detect encoding of files
   chardetect somefile.txt anotherfile.csv

   # Output only the encoding name
   chardetect --minimal somefile.txt

   # Include all encoding eras
   chardetect --legacy somefile.txt

   # Specific encoding era
   chardetect -e dos somefile.txt

   # Read from stdin
   cat somefile.txt | chardetect
```

**Step 2: Build and verify**

Run: `uv run sphinx-build docs docs/_build`
Expected: Build completes. usage.rst renders correctly.

**Step 3: Commit**

```bash
git add docs/usage.rst
git commit -m "Add usage documentation page"
```

---

### Task 5: Generate supported-encodings.rst

**Files:**
- Create: `scripts/generate_encoding_table.py`
- Create: `docs/supported-encodings.rst`

**Step 1: Write the generation script**

Create `scripts/generate_encoding_table.py`:

```python
#!/usr/bin/env python
"""Generate the supported encodings RST table from the registry."""

from __future__ import annotations

from chardet.enums import EncodingEra
from chardet.registry import REGISTRY

ERA_DISPLAY = {
    EncodingEra.MODERN_WEB: "Modern Web",
    EncodingEra.LEGACY_ISO: "Legacy ISO",
    EncodingEra.LEGACY_MAC: "Legacy Mac",
    EncodingEra.LEGACY_REGIONAL: "Legacy Regional",
    EncodingEra.DOS: "DOS",
    EncodingEra.MAINFRAME: "Mainframe (EBCDIC)",
}

ERA_ORDER = list(ERA_DISPLAY)


def main() -> None:
    """Print the supported encodings RST table to stdout."""
    total = len(REGISTRY)
    print("Supported Encodings")
    print("===================")
    print()
    print(f"chardet supports **{total} encodings** across six encoding eras.")
    print("The default :attr:`~chardet.EncodingEra.MODERN_WEB` era covers the")
    print("encodings most commonly found on the web today. Use")
    print(":attr:`~chardet.EncodingEra.ALL` to enable detection of all encodings.")
    print()

    for era in ERA_ORDER:
        entries = sorted(
            [e for e in REGISTRY if e.era == era],
            key=lambda e: e.name,
        )
        title = ERA_DISPLAY[era]
        print(title)
        print("-" * len(title))
        print()
        print(".. list-table::")
        print("   :header-rows: 1")
        print("   :widths: 25 50 15")
        print()
        print("   * - Encoding")
        print("     - Aliases")
        print("     - Multi-byte")
        for e in entries:
            aliases = ", ".join(e.aliases) if e.aliases else "\u2014"
            mb = "Yes" if e.is_multibyte else "No"
            print(f"   * - {e.name}")
            print(f"     - {aliases}")
            print(f"     - {mb}")
        print()


if __name__ == "__main__":
    main()
```

**Step 2: Run the script to generate the RST**

Run: `uv run python scripts/generate_encoding_table.py > docs/supported-encodings.rst`
Expected: RST file created with all encodings grouped by era.

**Step 3: Verify the generated file looks correct**

Read `docs/supported-encodings.rst` and check the tables are well-formed.

**Step 4: Build and verify**

Run: `uv run sphinx-build docs docs/_build`
Expected: Build completes. Tables render correctly.

**Step 5: Commit**

```bash
git add scripts/generate_encoding_table.py docs/supported-encodings.rst
git commit -m "Add supported encodings page (generated from registry)"
```

---

### Task 6: Write how-it-works.rst

**Files:**
- Create: `docs/how-it-works.rst`

**Step 1: Create docs/how-it-works.rst**

```rst
How It Works
============

chardet uses a multi-stage detection pipeline. Each stage either returns a
definitive result or passes to the next, progressing from cheap deterministic
checks to more expensive statistical analysis.

Detection Pipeline
------------------

When you call :func:`chardet.detect`, data flows through these stages in
order:

1. **BOM Detection** — Checks for a byte order mark at the start of the
   data. If found, returns the corresponding encoding (UTF-8-SIG,
   UTF-16-LE/BE, UTF-32-LE/BE) with confidence 1.0.

2. **UTF-16/32 Patterns** — Detects BOM-less UTF-16 and UTF-32 by
   analyzing null-byte patterns. Interleaved null bytes strongly indicate
   UTF-16; groups of three null bytes indicate UTF-32.

3. **Escape Sequences** — Identifies escape-based encodings like
   ISO-2022-JP, ISO-2022-KR, and HZ-GB-2312 by matching their
   characteristic escape byte sequences.

4. **Binary Detection** — If the data contains null bytes or a high
   proportion of control characters without matching any of the above,
   it is classified as binary (encoding ``None``).

5. **Markup Charset** — Extracts explicit charset declarations from
   ``<meta charset="...">`` tags or ``<?xml encoding="..."?>``
   processing instructions.

6. **ASCII Check** — If every byte is in the 7-bit ASCII range, returns
   ``ascii`` immediately.

7. **UTF-8 Validation** — Tests whether the data is valid UTF-8 by
   checking multi-byte sequence structure. UTF-8 has very distinctive
   byte patterns that are unlikely to occur in other encodings.

8. **Byte Validity Filtering** — Attempts to decode the data with each
   candidate encoding's Python codec. Any encoding that raises a decode
   error is eliminated.

9. **Structural Probing** — For multi-byte encodings (CJK), analyzes
   byte sequences to verify they follow the encoding's structural rules
   (lead byte / trail byte patterns, valid ranges).

10. **Statistical Scoring** — Scores remaining candidates using pre-trained
    bigram frequency models. Each model captures the characteristic byte
    pair frequencies of a language written in a specific encoding. The
    candidate with the highest score wins.

Confidence Scores
-----------------

The confidence score (0.0 to 1.0) reflects how the result was determined:

- **1.0** — BOM detected (definitive)
- **0.95** — Deterministic match (escape sequences, markup charset, ASCII,
  valid UTF-8)
- **< 0.95** — Statistical ranking. Higher scores mean the data better
  matches the encoding's expected byte pair frequencies.

A confidence of ``None`` with encoding ``None`` means the data appears to be
binary (not text).

Language Detection
------------------

chardet also returns the detected language alongside the encoding. Language
detection uses three tiers:

1. **Single-language encodings** — Encodings like Big5 (Chinese), EUC-JP
   (Japanese), or ISO-8859-7 (Greek) unambiguously identify the language.

2. **Multi-language encoding models** — For encodings shared across
   languages (e.g., windows-1252 is used for French, German, Spanish,
   etc.), the statistical scoring stage compares language-specific bigram
   models and picks the best-matching language.

3. **UTF-8 fallback** — For Unicode encodings (UTF-8, UTF-16, UTF-32),
   the detected text is scored against byte-level bigram models for 48
   languages.
```

**Step 2: Build and verify**

Run: `uv run sphinx-build docs docs/_build`
Expected: Build completes. Page renders correctly.

**Step 3: Commit**

```bash
git add docs/how-it-works.rst
git commit -m "Add 'How It Works' documentation page"
```

---

### Task 7: Write performance.rst

**Files:**
- Create: `docs/performance.rst`

Adapt from `docs/rewrite_performance.md`, keeping headline numbers and
dropping pairwise per-encoding breakdowns.

**Step 1: Create docs/performance.rst**

```rst
Performance
===========

Benchmarked against 2,161 test files from the
`chardet test suite <https://github.com/chardet/test-data>`_. All
detectors evaluated with the same equivalence rules. Numbers below are
pure Python (CPython 3.12) unless noted.

Accuracy
--------

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 15

   * - Detector
     - Correct
     - Accuracy
     - Time
   * - **chardet** (this version)
     - **2083/2161**
     - **96.4%**
     - **6.07s**
   * - chardet 6.0.0
     - 2042/2161
     - 94.5%
     - 175.79s
   * - charset-normalizer
     - 1924/2161
     - 89.0%
     - 33.81s
   * - cchardet
     - 1228/2161
     - 56.8%
     - 0.73s

chardet leads all detectors on accuracy: **+1.9pp** vs chardet 6.0.0,
**+7.4pp** vs charset-normalizer, and **+39.6pp** vs cchardet.

Speed
-----

.. list-table::
   :header-rows: 1
   :widths: 30 12 12 12 12 12

   * - Detector
     - Total
     - Mean
     - Median
     - p90
     - p95
   * - cchardet
     - 723ms
     - 0.33ms
     - 0.07ms
     - 0.68ms
     - 0.92ms
   * - **chardet** (this version)
     - **6,049ms**
     - **2.80ms**
     - **1.08ms**
     - **5.07ms**
     - **5.89ms**
   * - charset-normalizer
     - 33,783ms
     - 15.63ms
     - 4.74ms
     - 50.66ms
     - 72.64ms
   * - chardet 6.0.0
     - 175,757ms
     - 81.33ms
     - 16.10ms
     - 121.99ms
     - 307.29ms

chardet is **29x faster** than chardet 6.0.0 and **5.6x faster** than
charset-normalizer. Its median latency (1.08ms) is the lowest among all
pure-Python detectors.

Memory
------

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 15

   * - Detector
     - Import Memory
     - Peak Memory
     - RSS
   * - **chardet** (this version)
     - **96 B**
     - **20.4 MiB**
     - **91.9 MiB**
   * - chardet 6.0.0
     - 96 B
     - 16.4 MiB
     - 100.2 MiB
   * - charset-normalizer
     - 1.7 MiB
     - 102.2 MiB
     - 264.9 MiB
   * - cchardet
     - 23.6 KiB
     - 27.2 KiB
     - 59.8 MiB

chardet uses negligible import memory (96 B), **5x less peak memory** than
charset-normalizer, and **2.9x less RSS**.

Language Detection
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 20

   * - Detector
     - Correct
     - Accuracy
   * - **chardet** (this version)
     - **1965/2161**
     - **90.9%**
   * - chardet 6.0.0
     - 1016/2161
     - 47.0%
   * - charset-normalizer
     - 0/2161
     - 0.0%
   * - cchardet
     - 0/2161
     - 0.0%

chardet detects the language for every file. charset-normalizer and cchardet
do not report language.

Thread Safety
-------------

:func:`chardet.detect` and :func:`chardet.detect_all` are fully thread-safe.
Each call carries its own state with no shared mutable data between threads.
Thread safety adds no measurable overhead (< 0.1%).

On free-threaded Python (3.13t+, GIL disabled), detection scales with
threads:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20

   * - Threads
     - Time
     - Speedup
   * - 1
     - 4,361ms
     - baseline
   * - 2
     - 2,337ms
     - 1.9x
   * - 4
     - 1,930ms
     - 2.3x

Individual :class:`~chardet.UniversalDetector` instances are not thread-safe.
Create one instance per thread when using the streaming API.

Optional mypyc Compilation
--------------------------

chardet supports optional `mypyc <https://mypyc.readthedocs.io>`_
compilation on CPython:

.. code-block:: bash

   HATCH_BUILD_HOOK_ENABLE_MYPYC=true pip install chardet

.. list-table::
   :header-rows: 1
   :widths: 30 20 20

   * - Build
     - Total Time
     - Speedup
   * - Pure Python
     - 6,030ms
     - baseline
   * - mypyc compiled
     - 4,015ms
     - **1.50x**

Pure-Python wheels are always available for PyPy and platforms without
prebuilt binaries.
```

**Step 2: Build and verify**

Run: `uv run sphinx-build docs docs/_build`
Expected: Build completes. Tables render correctly.

**Step 3: Commit**

```bash
git add docs/performance.rst
git commit -m "Add performance benchmarks documentation page"
```

---

### Task 8: Write faq.rst

**Files:**
- Create: `docs/faq.rst`

**Step 1: Create docs/faq.rst**

```rst
Frequently Asked Questions
==========================

Why does detect() return None for encoding?
--------------------------------------------

chardet returns ``None`` when the data appears to be binary rather than
text. This happens when the data contains null bytes or a high proportion
of control characters that don't match any known text encoding.

.. code-block:: python

   result = chardet.detect(b"\x00\x01\x02\x03")
   # {'encoding': None, 'confidence': None, 'language': None}

How do I increase accuracy?
----------------------------

- **Provide more data.** The more bytes chardet can examine, the more
  accurate the result. The default limit is 200,000 bytes.
- **Broaden the encoding era.** By default, chardet only considers modern
  web encodings. If your data may use legacy encodings, pass
  ``encoding_era=EncodingEra.ALL``.
- **Use detect_all().** If the top result is wrong, the correct encoding
  may be the second candidate. :func:`chardet.detect_all` returns all
  candidates ranked by confidence.

What changed from chardet 5.x?
-------------------------------

chardet 6.x was a major rewrite:

- Dramatically improved accuracy (96.4% vs 68.0%)
- 29x faster than chardet 6.0.0, 5.5x faster than chardet 5.2.0
- Encoding era system (:class:`~chardet.EncodingEra`) for filtering
  candidates
- Language detection for every file (90.9% accuracy)
- Thread-safe :func:`~chardet.detect` and :func:`~chardet.detect_all`
- Free-threaded Python support (3.13t+)
- Negligible import memory (96 bytes)
- Zero runtime dependencies

The public API is backward-compatible. ``detect()``, ``detect_all()``,
and ``UniversalDetector`` work the same way.

How is chardet different from charset-normalizer?
--------------------------------------------------

`charset-normalizer <https://github.com/Ousret/charset_normalizer>`_ is
an alternative encoding detector. Key differences:

- **Accuracy:** chardet achieves 96.4% vs charset-normalizer's 89.0% on
  the same test suite.
- **Speed:** chardet is 5.6x faster (6s vs 34s for 2,161 files).
- **Memory:** chardet uses 5x less peak memory (20 MiB vs 102 MiB).
- **Language detection:** chardet reports the detected language;
  charset-normalizer does not.
- **Encoding breadth:** chardet supports EBCDIC, Mac, and DOS encodings
  that charset-normalizer does not.

How is chardet different from cchardet?
----------------------------------------

`cchardet <https://github.com/faust-streaming/faust-cchardet>`_ wraps
Mozilla's uchardet C/C++ library. Key differences:

- **Accuracy:** chardet achieves 96.4% vs cchardet's 56.8%.
- **Speed:** cchardet is faster (0.73s vs 6s) due to C implementation.
- **Encoding breadth:** chardet supports 49 more encodings than cchardet,
  including EBCDIC, Mac, Baltic, and BOM-less UTF-16/32.
- **Dependencies:** chardet is pure Python with zero dependencies.
  cchardet requires a C compiler to build from source.

Is chardet thread-safe?
-------------------------

:func:`chardet.detect` and :func:`chardet.detect_all` are fully
thread-safe and can be called concurrently from any number of threads.

:class:`~chardet.UniversalDetector` instances are **not** thread-safe.
Create one instance per thread when using the streaming API.

Does chardet work on PyPy?
---------------------------

Yes. chardet is pure Python and works on PyPy without modification.
The optional mypyc compilation is CPython-only; PyPy uses the pure-Python
code path automatically.
```

**Step 2: Build and verify**

Run: `uv run sphinx-build docs docs/_build`
Expected: Build completes.

**Step 3: Commit**

```bash
git add docs/faq.rst
git commit -m "Add FAQ documentation page"
```

---

### Task 9: Set up API reference with autosummary

**Files:**
- Create: `docs/api/index.rst`

**Step 1: Create docs/api/index.rst**

```rst
API Reference
=============

Top-level Functions
-------------------

.. autofunction:: chardet.detect

.. autofunction:: chardet.detect_all

UniversalDetector
-----------------

.. autoclass:: chardet.UniversalDetector
   :members:
   :undoc-members:

Enumerations
------------

.. autoclass:: chardet.EncodingEra
   :members:
   :undoc-members:

.. autoclass:: chardet.LanguageFilter
   :members:
   :undoc-members:
```

**Step 2: Build and verify API pages generate**

Run: `uv run sphinx-build docs docs/_build`
Expected: Build completes. API pages show the docstrings from source code.
The `:param:` and `:returns:` directives in the source render as
parameter/return documentation.

**Step 3: Verify cross-references work**

Check that `docs/_build/api/index.html` contains the full docstrings for
`detect()`, `detect_all()`, `UniversalDetector`, `EncodingEra`, and
`LanguageFilter`. Parameters should be rendered with descriptions.

**Step 4: Commit**

```bash
git add docs/api/index.rst
git commit -m "Add API reference page (autodoc from source docstrings)"
```

---

### Task 10: Final build verification and cleanup

**Files:**
- Possibly modify: any files with warnings

**Step 1: Clean build with warnings as errors**

Run: `rm -rf docs/_build && uv run sphinx-build -W docs docs/_build`

The `-W` flag turns warnings into errors. Fix any issues:
- Broken cross-references (`:func:`, `:class:`, `:attr:` targets)
- Malformed RST
- Missing files referenced in toctree

**Step 2: Verify all pages render**

Check each HTML page in `docs/_build/`:
- `index.html` — landing page with toctree
- `usage.html` — all code blocks render
- `supported-encodings.html` — tables render with all encodings
- `how-it-works.html` — pipeline stages
- `performance.html` — benchmark tables
- `faq.html` — all Q&A sections
- `api/index.html` — API docs with parameters

**Step 3: Run ruff on the new script**

Run: `uv run ruff check scripts/generate_encoding_table.py`
Expected: No errors.

**Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "Fix documentation build warnings"
```

Only if changes were made. Skip if the build was clean.

---

## ReadTheDocs Setup (Manual)

After all code is pushed, configure ReadTheDocs via their web interface:

1. Import the repository at https://readthedocs.org/dashboard/import/
2. Under **Admin > Advanced Settings**, set the default branch to `main`
3. Under **Admin > Automation Rules**, add a rule to activate versions
   matching tag pattern `v*`
4. Optionally disable building on branch pushes (since we only want
   tag builds)

This is a one-time manual step, not automatable via code.
