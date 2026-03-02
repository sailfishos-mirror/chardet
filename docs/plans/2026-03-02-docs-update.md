# Documentation Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix stale data, fill parameter gaps, and add contributing + changelog pages to the chardet docs.

**Architecture:** Surgical edits to four existing rst files, plus two new rst files. No structural reorganization. Source of truth for benchmark numbers is `docs/rewrite_performance.md`. Source of truth for changelog entries is GitHub release notes.

**Tech Stack:** Sphinx + reStructuredText, Furo theme, autodoc

---

### Task 1: Enrich `index.rst` landing page

**Files:**
- Modify: `docs/index.rst`

**Step 1: Edit `docs/index.rst`**

Replace the current content with an enriched version that adds MIT license, Python 3.10+, PyPy, zero-dependency, and GitHub/PyPI links. Add `contributing` and `changelog` to the toctree.

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

chardet 7.0 is a ground-up, MIT-licensed rewrite — same package name, same
public API, drop-in replacement for chardet 5.x/6.x. Python 3.10+, zero
runtime dependencies, works on PyPy.

- **96.8% accuracy** on 2,179 test files
- **28x faster** than chardet 6.0.0
- **Language detection** for every result (90.5% accuracy)
- **99 encodings** across six encoding eras
- **Thread-safe** ``detect()`` and ``detect_all()``

.. toctree::
   :maxdepth: 2
   :caption: Contents

   usage
   supported-encodings
   how-it-works
   performance
   faq
   api/index
   contributing
   changelog
```

**Step 2: Verify the build**

Run: `uv run sphinx-build -W docs docs/_build 2>&1 | tail -5`
Expected: Build succeeds (it will fail until contributing.rst and changelog.rst exist — that's fine, we'll create them in later tasks)

**Step 3: Commit**

```bash
git add docs/index.rst
git commit -m "docs: enrich index.rst landing page with highlights and new toctree entries"
```

---

### Task 2: Fill parameter gaps in `usage.rst`

**Files:**
- Modify: `docs/usage.rst`

**Step 1: Edit `docs/usage.rst`**

Add three new sections after the existing "Encoding Eras" section and before "Limiting Bytes":

1. A "Legacy Renaming" section documenting `should_rename_legacy`
2. Expand the "Streaming Detection" section to mention `encoding_era` and `max_bytes` constructor params
3. Add a "Deprecated Parameters" section for `chunk_size` and `LanguageFilter`

The final file should be:

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

The constructor accepts the same tuning parameters as :func:`~chardet.detect`:

.. code-block:: python

   detector = UniversalDetector(
       encoding_era=EncodingEra.MODERN_WEB,  # restrict candidate encodings
       max_bytes=50_000,                      # stop buffering after 50 KB
   )

Encoding Eras
-------------

By default, chardet considers all supported encodings for maximum
accuracy. Use the ``encoding_era`` parameter to restrict the search to a
specific subset:

.. code-block:: python

   from chardet import detect, EncodingEra

   # Default: all encodings considered
   result = detect(data)

   # Restrict to modern web encodings only
   result = detect(data, encoding_era=EncodingEra.MODERN_WEB)

   # Only legacy ISO encodings
   result = detect(data, encoding_era=EncodingEra.LEGACY_ISO)

Available eras (can be combined with ``|``):

- :attr:`~chardet.EncodingEra.ALL` — All supported encodings (default)
- :attr:`~chardet.EncodingEra.MODERN_WEB` — UTF-8, Windows codepages,
  CJK encodings
- :attr:`~chardet.EncodingEra.LEGACY_ISO` — ISO-8859 family
- :attr:`~chardet.EncodingEra.LEGACY_MAC` — Mac encodings
- :attr:`~chardet.EncodingEra.LEGACY_REGIONAL` — Regional codepages
  (KOI8-T, KZ-1048, etc.)
- :attr:`~chardet.EncodingEra.DOS` — DOS codepages (CP437, CP850, etc.)
- :attr:`~chardet.EncodingEra.MAINFRAME` — EBCDIC encodings

Legacy Renaming
---------------

By default, chardet remaps legacy encoding names to their modern
equivalents (e.g., ``"gb2312"`` becomes ``"gb18030"``). Set
``should_rename_legacy=False`` to get the raw detection name:

.. code-block:: python

   # Default: legacy names are remapped
   chardet.detect(data)
   # {'encoding': 'gb18030', ...}

   # Disable renaming to get the original detection name
   chardet.detect(data, should_rename_legacy=False)
   # {'encoding': 'gb2312', ...}

This applies to :func:`~chardet.detect`, :func:`~chardet.detect_all`,
and :class:`~chardet.UniversalDetector`.

Limiting Bytes
--------------

By default, chardet examines up to 200,000 bytes. Use ``max_bytes`` to
adjust:

.. code-block:: python

   # Examine only the first 10 KB
   result = chardet.detect(data, max_bytes=10_000)

Smaller values are faster but may reduce accuracy for encodings that
require more data to distinguish.

Deprecated Parameters
---------------------

The following parameters are accepted for backward compatibility with
chardet 5.x/6.x but have no effect:

- ``chunk_size`` on :func:`~chardet.detect` and
  :func:`~chardet.detect_all` — previously controlled how data was
  chunked for streaming probers. A deprecation warning is emitted if a
  non-default value is passed.
- ``lang_filter`` on :class:`~chardet.UniversalDetector` — previously
  restricted detection to specific language groups via
  :class:`~chardet.LanguageFilter`. A deprecation warning is emitted if
  set to anything other than :attr:`~chardet.LanguageFilter.ALL`.

Command-Line Tool
-----------------

chardet includes a ``chardetect`` command:

.. code-block:: bash

   # Detect encoding of files
   chardetect somefile.txt anotherfile.csv

   # Output only the encoding name
   chardetect --minimal somefile.txt

   # Specific encoding era
   chardetect -e dos somefile.txt

   # Read from stdin
   cat somefile.txt | chardetect
```

**Step 2: Verify the build**

Run: `uv run sphinx-build -W docs docs/_build 2>&1 | tail -5`
Expected: Build succeeds (may still fail on missing contributing/changelog — that's OK)

**Step 3: Commit**

```bash
git add docs/usage.rst
git commit -m "docs: document should_rename_legacy, UniversalDetector params, and deprecated parameters"
```

---

### Task 3: Fix stale data in `faq.rst`

**Files:**
- Modify: `docs/faq.rst`

**Step 1: Fix chardet 5.2.0 accuracy**

In `docs/faq.rst`, find:
```
68.0% in chardet 5.2.0
```
Replace with:
```
68.2% in chardet 5.2.0
```

**Step 2: Fix charset-normalizer link**

In `docs/faq.rst`, find:
```
`charset-normalizer <https://github.com/Ousret/charset_normalizer>`_
```
Replace with:
```
`charset-normalizer <https://github.com/jawah/charset_normalizer>`_
```

**Step 3: Commit**

```bash
git add docs/faq.rst
git commit -m "docs: fix stale accuracy number and charset-normalizer link in FAQ"
```

---

### Task 4: Reconcile `performance.rst` with benchmark data

**Files:**
- Modify: `docs/performance.rst`

**Step 1: Review discrepancies**

Compare `docs/performance.rst` against `docs/rewrite_performance.md` (the source of truth). Key discrepancies to check:

- Accuracy table: chardet shows 96.8% and 2110/2179 in performance.rst — matches rewrite_performance.md. OK.
- Speed table: check files/s, mean, median, p90, p95 against rewrite_performance.md.
- Memory table: check all values against rewrite_performance.md.
- Language detection table: check values.
- Prose comparisons (e.g., "28x faster", "5.2x faster") — verify against the tables.

Read both files carefully. The current `performance.rst` numbers appear to already be aligned with `rewrite_performance.md` from commit `2ba1356`. If all numbers match, no changes needed — just verify and skip to the commit step (or skip this task entirely).

**Step 2: If changes needed, edit `docs/performance.rst`**

Make targeted edits to fix any mismatched numbers. Use `rewrite_performance.md` values.

**Step 3: Commit (only if changes made)**

```bash
git add docs/performance.rst
git commit -m "docs: reconcile performance.rst numbers with benchmark data"
```

---

### Task 5: Create `contributing.rst`

**Files:**
- Create: `docs/contributing.rst`

**Step 1: Write `docs/contributing.rst`**

Content sourced from `CLAUDE.md`. Cover: dev setup, testing, linting, training, benchmarks, docs, architecture overview, mypyc. Keep it practical — commands a contributor can copy-paste.

```rst
Contributing
============

Development Setup
-----------------

chardet uses `uv <https://docs.astral.sh/uv/>`_ for dependency management:

.. code-block:: bash

   git clone https://github.com/chardet/chardet.git
   cd chardet
   uv sync                    # install dependencies
   prek install               # set up pre-commit hooks (ruff lint+format, etc.)

Running Tests
-------------

Tests use pytest. Test data is auto-cloned from the
`chardet/test-data <https://github.com/chardet/test-data>`_ repo on
first run (cached in ``tests/data/``, gitignored).

.. code-block:: bash

   uv run python -m pytest                              # run all tests
   uv run python -m pytest tests/test_api.py            # single file
   uv run python -m pytest tests/test_api.py::test_detect_empty  # single test
   uv run python -m pytest -x                           # stop on first failure

Accuracy tests are dynamically parametrized from the test data via
``conftest.py``.

Linting and Formatting
----------------------

chardet uses `Ruff <https://docs.astral.sh/ruff/>`_ with
``select = ["ALL"]`` and targeted ignores (see ``pyproject.toml``):

.. code-block:: bash

   uv run ruff check .        # lint
   uv run ruff check --fix .  # lint with auto-fix
   uv run ruff format .       # format

Pre-commit hooks run ruff automatically on each commit.

Training Models
---------------

Bigram frequency models are trained from Wikipedia/HTML data (separate
from the evaluation test suite):

.. code-block:: bash

   uv run python scripts/train.py

Training data is cached in ``data/`` (gitignored). Models are saved to
``src/chardet/models/models.bin``.

Benchmarks and Diagnostics
--------------------------

.. code-block:: bash

   uv run python scripts/benchmark_time.py     # latency benchmarks
   uv run python scripts/benchmark_memory.py   # memory usage benchmarks
   uv run python scripts/diagnose_accuracy.py  # detailed accuracy diagnostics
   uv run python scripts/compare_detectors.py  # compare against other detectors

Building Documentation
----------------------

.. code-block:: bash

   uv sync --group docs                          # install Sphinx, Furo, etc.
   uv run sphinx-build docs docs/_build          # build HTML docs
   uv run sphinx-build -W docs docs/_build       # build with warnings as errors

Docs are published to `ReadTheDocs <https://chardet.readthedocs.io>`_
on tag push.

Architecture Overview
---------------------

All detection flows through ``run_pipeline()`` in
``src/chardet/pipeline/orchestrator.py``, which runs stages in order —
each stage either returns a definitive result or passes to the next:

1. **BOM** (``bom.py``) — byte order mark
2. **UTF-16/32 patterns** (``utf1632.py``) — null-byte patterns
3. **Escape sequences** (``escape.py``) — ISO-2022-JP/KR, HZ-GB-2312
4. **Binary detection** (``binary.py``) — null bytes / control chars
5. **Markup charset** (``markup.py``) — ``<meta charset>`` / ``<?xml encoding>``
6. **ASCII** (``ascii.py``) — pure 7-bit check
7. **UTF-8** (``utf8.py``) — structural multi-byte validation
8. **Byte validity** (``validity.py``) — eliminate invalid encodings
9. **CJK gating** (in orchestrator) — eliminate spurious CJK candidates
10. **Structural probing** (``structural.py``) — multi-byte encoding fit
11. **Statistical scoring** (``statistical.py``) — bigram frequency models
12. **Post-processing** (orchestrator) — confusion groups, niche demotion

Key types:

- ``DetectionResult`` — frozen dataclass: ``encoding``, ``confidence``,
  ``language``
- ``EncodingInfo`` (``registry.py``) — frozen dataclass: ``name``,
  ``aliases``, ``era``, ``is_multibyte``, ``python_codec``
- ``EncodingEra`` (``enums.py``) — IntFlag for filtering candidates
- ``BigramProfile`` (``models/__init__.py``) — pre-computed bigram
  frequencies

Model format: binary file ``src/chardet/models/models.bin`` — sparse
bigram tables loaded via ``struct.unpack``. Each model is a 65,536-byte
lookup table indexed by ``(b1 << 8) | b2``.

Optional mypyc Compilation
--------------------------

Hot-path modules can be compiled to C extensions with
`mypyc <https://mypyc.readthedocs.io>`_:

.. code-block:: bash

   HATCH_BUILD_HOOK_ENABLE_MYPYC=true uv build

Compiled modules: ``models/__init__.py``, ``pipeline/structural.py``,
``pipeline/validity.py``, ``pipeline/statistical.py``,
``pipeline/utf1632.py``, ``pipeline/utf8.py``, ``pipeline/escape.py``.

These modules cannot use ``from __future__ import annotations``
(``FA100`` is ignored for them in ruff config).

Versioning
----------

Version is derived from git tags via ``hatch-vcs``. The tag is the
single source of truth — no hardcoded version strings. The generated
``src/chardet/_version.py`` is gitignored and should never be committed.

Conventions
-----------

- ``from __future__ import annotations`` in all source files (except
  mypyc-compiled modules)
- Frozen dataclasses with ``slots=True`` for data types
- Ruff with ``select = ["ALL"]`` and targeted ignores
- Training data (Wikipedia/HTML) is never the same as evaluation data
  (chardet test suite)
```

**Step 2: Verify the build**

Run: `uv run sphinx-build -W docs docs/_build 2>&1 | tail -5`
Expected: May still fail on missing changelog.rst — OK.

**Step 3: Commit**

```bash
git add docs/contributing.rst
git commit -m "docs: add contributing.rst with dev setup, architecture, and conventions"
```

---

### Task 6: Create `changelog.rst`

**Files:**
- Create: `docs/changelog.rst`

**Step 1: Write `docs/changelog.rst`**

Comprehensive changelog from GitHub releases. Use concise bullet points, group by features/fixes/breaking changes for major releases, single line for minor ones.

```rst
Changelog
=========

7.0.0 (unreleased)
-------------------

Ground-up, MIT-licensed rewrite of chardet. Same package name, same
public API — drop-in replacement for chardet 5.x/6.x.

**Highlights:**

- **MIT license** (previous versions were LGPL)
- **96.8% accuracy** on 2,179 test files (+2.3pp vs chardet 6.0.0,
  +7.7pp vs charset-normalizer)
- **28x faster** than chardet 6.0.0, 5x faster than charset-normalizer
- **Language detection** for every result (90.5% accuracy across 49
  languages)
- **99 encodings** across six eras (MODERN_WEB, LEGACY_ISO, LEGACY_MAC,
  LEGACY_REGIONAL, DOS, MAINFRAME)
- **12-stage detection pipeline** — BOM, UTF-16/32 patterns, escape
  sequences, binary detection, markup charset, ASCII, UTF-8 validation,
  byte validity, CJK gating, structural probing, statistical scoring,
  post-processing
- **Bigram frequency models** trained on Wikipedia/HTML data for all
  supported language/encoding pairs
- **Optional mypyc compilation** — 1.49x additional speedup on CPython
- **Thread-safe** ``detect()`` and ``detect_all()`` with no measurable
  overhead; scales on free-threaded Python 3.13t+
- **Negligible import memory** (96 B)
- **Zero runtime dependencies**

**Breaking changes vs 6.0.0:**

- ``detect()`` and ``detect_all()`` now default to
  ``encoding_era=EncodingEra.ALL`` (6.0.0 defaulted to ``MODERN_WEB``)
- Internal architecture is completely different (probers replaced by
  pipeline stages). Only the public API is preserved.
- ``LanguageFilter`` is accepted but ignored (deprecation warning
  emitted)
- ``chunk_size`` is accepted but ignored (deprecation warning emitted)

6.0.0 (2026-02-22)
-------------------

**Features:**

- Unified single-byte charset detection with proper language-specific
  bigram models for all single-byte encodings (replaces ``Latin1Prober``
  and ``MacRomanProber`` heuristics)
- 38 new languages: Arabic, Belarusian, Breton, Croatian, Czech, Danish,
  Dutch, English, Esperanto, Estonian, Farsi, Finnish, French, German,
  Icelandic, Indonesian, Irish, Italian, Kazakh, Latvian, Lithuanian,
  Macedonian, Malay, Maltese, Norwegian, Polish, Portuguese, Romanian,
  Scottish Gaelic, Serbian, Slovak, Slovene, Spanish, Swedish, Tajik,
  Ukrainian, Vietnamese, Welsh
- ``EncodingEra`` filtering via new ``encoding_era`` parameter
- ``max_bytes`` and ``chunk_size`` parameters for ``detect()``,
  ``detect_all()``, and ``UniversalDetector``
- ``-e``/``--encoding-era`` CLI flag
- EBCDIC detection (CP037, CP500)
- Direct GB18030 support (replaces redundant GB2312 prober)
- Binary file detection
- Python 3.12, 3.13, and 3.14 support

**Breaking changes:**

- Dropped Python 3.7, 3.8, and 3.9 (requires Python 3.10+)
- Removed ``Latin1Prober`` and ``MacRomanProber``
- Removed EUC-TW support
- Removed ``LanguageFilter.NONE``
- ``detect()`` default changed to ``encoding_era=EncodingEra.MODERN_WEB``

**Fixes:**

- Fixed CP949 state machine
- Fixed SJIS distribution analysis (second-byte range >= 0x80)
- Fixed UTF-16/32 detection for non-ASCII-heavy text
- Fixed GB18030 ``char_len_table``
- Fixed UTF-8 state machine
- Fixed ``detect_all()`` returning inactive probers
- Fixed early cutoff bug

5.2.0 (2023-08-01)
-------------------

- Added support for running the CLI via ``python -m chardet``

5.1.0 (2022-12-01)
-------------------

- Added ``should_rename_legacy`` argument to remap legacy encoding names
  to modern equivalents
- Added MacRoman encoding prober
- Added ``--minimal`` flag to ``chardetect`` CLI
- Added type annotations and mypy CI
- Added support for Python 3.11
- Removed support for Python 3.6

5.0.0 (2022-06-25)
-------------------

- Added Johab Korean prober
- Added UTF-16/32 BE/LE probers
- Added test data for Croatian, Czech, Hungarian, Polish, Slovak,
  Slovene, Greek, Turkish
- Improved XML tag filtering
- Made ``detect_all`` return child prober confidences
- Dropped Python 2.7, 3.4, 3.5 (requires Python 3.6+)

4.0.0 (2020-12-10)
-------------------

- Added ``detect_all()`` function returning all candidate encodings
- Converted single-byte charset probers to nested dicts (performance)
- ``CharsetGroupProber`` now short-circuits on definite matches
  (performance)
- Added ``language`` field to ``detect_all`` output
- Dropped Python 2.6, 3.4, 3.5

3.0.4 (2017-06-08)
-------------------

- Fixed packaging issue with ``pytest_runner``
- Updated old URLs in README and docs

3.0.3 (2017-05-16)
-------------------

- Fixed crash when debug logging was enabled

3.0.2 (2017-04-12)
-------------------

- Fixed ``detect`` sometimes returning ``None`` instead of a result dict

3.0.1 (2017-04-11)
-------------------

- Fixed crash in EUC-TW prober with certain strings

3.0.0 (2017-04-11)
-------------------

- Added Turkish ISO-8859-9 detection
- Modernized naming conventions (``typical_positive_ratio`` instead of
  ``mTypicalPositiveRatio``)
- Added ``language`` property to probers and results
- Switched from Travis to GitHub Actions
- Fixed ``CharsetGroupProber.state`` not being set to ``FOUND_IT``

2.3.0 (2014-10-07)
-------------------

- Added CP932 detection
- Fixed UTF-8 BOM not detected as UTF-8-SIG
- Switched ``chardetect`` to use ``argparse``

2.2.1 (2013-12-18)
-------------------

- Fixed missing parenthesis in ``chardetect.py``

2.2.0 (2013-12-16)
-------------------

- First release after merger with charade (Python 3 support)
```

**Step 2: Verify the full docs build**

Run: `uv run sphinx-build -W docs docs/_build 2>&1 | tail -10`
Expected: Build succeeds with no warnings.

**Step 3: Commit**

```bash
git add docs/changelog.rst
git commit -m "docs: add comprehensive changelog covering all releases"
```

---

### Task 7: Final verification

**Step 1: Full docs build**

Run: `uv run sphinx-build -W docs docs/_build`
Expected: Build succeeds with no warnings.

**Step 2: Full test suite**

Run: `uv run python -m pytest -x`
Expected: All tests pass.

**Step 3: Lint**

Run: `uv run ruff check docs/conf.py`
Expected: No errors.

**Step 4: Verify no stale references to `--legacy`**

Run: `grep -r "\-\-legacy" docs/`
Expected: No matches.

**Step 5: Spot-check cross-references**

Open `docs/_build/index.html` in a browser (or just verify the build had no warnings in step 1).
