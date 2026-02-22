# Documentation Update for chardet 6.0.0 — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update all ReadTheDocs documentation to reflect chardet 6.0.0's new API, architecture, and supported encodings.

**Architecture:** Seven files need updating: supported-encodings.rst (restructured by EncodingEra), usage.rst (new API parameters + detect_all), how-it-works.rst (full rewrite for 6.0 pipeline), api/chardet.rst (regenerated module list), faq.rst (minor update), README.rst (badges + encoding list), conf.py (deprecation fixes).

**Tech Stack:** reStructuredText, Sphinx, GitHub Actions badges

---

### Task 1: Update `docs/supported-encodings.rst`

**Files:**
- Modify: `docs/supported-encodings.rst`

**Step 1: Rewrite supported-encodings.rst**

Replace the entire file with encodings grouped by `EncodingEra` tier. Each section lists encodings alphabetically with their supported languages in parentheses (derived from prober registrations in `sbcsgroupprober.py` and `mbcsgroupprober.py`).

```rst
Supported encodings
===================

chardet supports over 70 character encodings, organized into tiers by
the ``EncodingEra`` enum. By default, ``detect()`` only considers
``MODERN_WEB`` encodings. Pass ``encoding_era=EncodingEra.ALL`` to
consider all tiers, or combine specific tiers with ``|``.

.. contents:: Encoding tiers
   :local:
   :depth: 1

MODERN_WEB
----------

Encodings widely used on the modern web. This is the default tier for
``detect()`` and ``detect_all()``.

Unicode
^^^^^^^

- ``UTF-8``
- ``UTF-8-SIG``
- ``UTF-16`` (BE and LE variants)
- ``UTF-32`` (BE and LE variants)

Multi-byte (CJK)
^^^^^^^^^^^^^^^^^

- ``Big5`` (Traditional Chinese)
- ``CP932`` (Japanese)
- ``CP949`` (Korean)
- ``EUC-JP`` (Japanese)
- ``EUC-KR`` (Korean)
- ``GB18030`` (Simplified Chinese)
- ``HZ-GB-2312`` (Simplified Chinese)
- ``ISO-2022-JP`` (Japanese)
- ``ISO-2022-KR`` (Korean)
- ``Shift-JIS`` (Japanese)

Single-byte (Windows)
^^^^^^^^^^^^^^^^^^^^^

- ``ASCII``
- ``CP874`` (Thai)
- ``KOI8-R`` (Russian, Ukrainian)
- ``KOI8-U`` (Ukrainian)
- ``TIS-620`` (Thai)
- ``Windows-1250`` (Croatian, Czech, Hungarian, Polish, Romanian, Slovak, Slovene)
- ``Windows-1251`` (Belarusian, Bulgarian, Macedonian, Russian, Serbian, Ukrainian)
- ``Windows-1252`` (Danish, Dutch, English, Finnish, French, German, Indonesian, Italian, Malay, Norwegian, Portuguese, Spanish, Swedish)
- ``Windows-1253`` (Greek)
- ``Windows-1254`` (Turkish)
- ``Windows-1255`` (Hebrew)
- ``Windows-1256`` (Arabic, Farsi)
- ``Windows-1257`` (Estonian, Latvian, Lithuanian)
- ``Windows-1258`` (Vietnamese)

LEGACY_ISO
----------

ISO 8859 family and other well-known legacy standards. Include this tier
when working with older web content or Unix-era text.

- ``ISO-8859-1`` (Danish, Dutch, English, Finnish, French, German, Icelandic, Indonesian, Italian, Malay, Norwegian, Portuguese, Spanish, Swedish)
- ``ISO-8859-2`` (Croatian, Czech, Hungarian, Polish, Romanian, Slovak, Slovene)
- ``ISO-8859-3`` (Esperanto, Maltese, Turkish)
- ``ISO-8859-4`` (Estonian, Latvian, Lithuanian)
- ``ISO-8859-5`` (Belarusian, Bulgarian, Macedonian, Russian, Serbian, Ukrainian)
- ``ISO-8859-6`` (Arabic, Farsi)
- ``ISO-8859-7`` (Greek)
- ``ISO-8859-8`` (Hebrew — visual and logical)
- ``ISO-8859-9`` (Turkish)
- ``ISO-8859-10`` (Icelandic)
- ``ISO-8859-11`` (Thai)
- ``ISO-8859-13`` (Estonian, Latvian, Lithuanian)
- ``ISO-8859-14`` (Breton, Irish, Scottish Gaelic, Welsh)
- ``ISO-8859-15`` (Danish, Dutch, Finnish, French, Italian, Norwegian, Portuguese, Spanish, Swedish)
- ``ISO-8859-16`` (Croatian, Hungarian, Polish, Romanian, Slovak, Slovene)
- ``Johab`` (Korean)

LEGACY_MAC
----------

Apple Macintosh-specific encodings.

- ``MacCyrillic`` (Belarusian, Bulgarian, Macedonian, Russian, Serbian, Ukrainian)
- ``MacGreek`` (Greek)
- ``MacIceland`` (Icelandic)
- ``MacLatin2`` (Croatian, Czech, Hungarian, Polish, Romanian, Slovak, Slovene)
- ``MacRoman`` (Danish, Dutch, English, Finnish, French, German, Icelandic, Indonesian, Italian, Malay, Norwegian, Portuguese, Spanish, Swedish)
- ``MacTurkish`` (Turkish)

LEGACY_REGIONAL
---------------

Uncommon regional and national encodings.

- ``CP720`` (Arabic)
- ``CP1006`` (Urdu)
- ``CP1125`` (Ukrainian)
- ``KOI8-T`` (Tajik)
- ``KZ1048`` (Kazakh)
- ``PTCP154`` (Kazakh)

DOS
---

DOS/OEM code pages.

- ``CP437`` (English)
- ``CP737`` (Greek)
- ``CP775`` (Estonian, Latvian, Lithuanian)
- ``CP850`` (Danish, Dutch, English, Finnish, French, German, Italian, Norwegian, Portuguese, Spanish, Swedish)
- ``CP852`` (Croatian, Czech, Hungarian, Polish, Romanian, Slovak, Slovene)
- ``CP855`` (Bulgarian, Macedonian, Russian, Serbian, Ukrainian)
- ``CP856`` (Hebrew)
- ``CP857`` (Turkish)
- ``CP858`` (Danish, Dutch, English, Finnish, French, German, Italian, Norwegian, Portuguese, Spanish, Swedish)
- ``CP860`` (Portuguese)
- ``CP861`` (Icelandic)
- ``CP862`` (Hebrew)
- ``CP863`` (French)
- ``CP864`` (Arabic)
- ``CP865`` (Danish, Norwegian)
- ``CP866`` (Belarusian, Russian, Ukrainian)
- ``CP869`` (Greek)

MAINFRAME
---------

IBM EBCDIC mainframe encodings.

- ``CP037`` (Breton, Danish, Dutch, English, Finnish, French, German, Icelandic, Indonesian, Irish, Italian, Malay, Norwegian, Portuguese, Scottish Gaelic, Spanish, Swedish, Welsh)
- ``CP424`` (Hebrew)
- ``CP500`` (Breton, Danish, Dutch, English, Finnish, French, German, Icelandic, Indonesian, Irish, Italian, Malay, Norwegian, Portuguese, Scottish Gaelic, Spanish, Swedish, Welsh)
- ``CP875`` (Greek)
- ``CP1026`` (Turkish)
```

**Step 2: Build docs to verify**

Run: `cd docs && uv run make html 2>&1 | tail -5`
Expected: Build completes with no errors related to supported-encodings.rst

**Step 3: Commit**

```bash
git add docs/supported-encodings.rst
git commit -m "docs: restructure supported-encodings by EncodingEra tier"
```

---

### Task 2: Update `docs/usage.rst`

**Files:**
- Modify: `docs/usage.rst`

**Step 1: Rewrite usage.rst**

Replace the file with updated content covering all current API features.

```rst
Usage
=====

Basic usage
-----------

The easiest way to use the Universal Encoding Detector library is with
the ``detect`` function.


Example: Using the ``detect`` function
--------------------------------------

The ``detect`` function takes a byte string and returns a dictionary
containing the auto-detected character encoding, a confidence level
from ``0`` to ``1``, and the detected language.

.. code:: python

    >>> import urllib.request
    >>> rawdata = urllib.request.urlopen('https://www.google.co.jp/').read()
    >>> import chardet
    >>> chardet.detect(rawdata)
    {'encoding': 'UTF-8', 'confidence': 0.99, 'language': ''}

The result dictionary always contains three keys:

- ``encoding``: the detected encoding name (or ``None`` if detection failed)
- ``confidence``: a float from ``0`` to ``1``
- ``language``: the detected language (or ``''`` if not applicable)


Filtering by encoding era
--------------------------

By default, ``detect()`` only considers modern web encodings (UTF-8,
Windows-125x, CJK multi-byte, etc.). If you're working with legacy data,
you can expand the search using the ``encoding_era`` parameter:

.. code:: python

    from chardet import detect
    from chardet.enums import EncodingEra

    # Default: only modern web encodings
    result = detect(data)

    # Include all encoding eras
    result = detect(data, encoding_era=EncodingEra.ALL)

    # Only consider DOS-era encodings
    result = detect(data, encoding_era=EncodingEra.DOS)

    # Combine specific eras
    result = detect(data, encoding_era=EncodingEra.MODERN_WEB | EncodingEra.LEGACY_ISO)

See :doc:`supported-encodings` for which encodings belong to each era.


Getting all candidates with ``detect_all``
------------------------------------------

If you want to see all candidate encodings rather than just the best
guess, use ``detect_all``:

.. code:: python

    >>> import chardet
    >>> chardet.detect_all(b'\xe4\xf6\xfc')
    [{'encoding': 'Windows-1252', 'confidence': 0.73, 'language': 'German'},
     {'encoding': 'ISO-8859-1', 'confidence': 0.60, 'language': 'German'}]

Results are sorted by confidence (highest first). ``detect_all`` accepts
the same ``encoding_era``, ``should_rename_legacy``, ``max_bytes``, and
``chunk_size`` parameters as ``detect``.


Advanced usage
--------------

If you're dealing with a large amount of text, you can call the
Universal Encoding Detector library incrementally, and it will stop as
soon as it is confident enough to report its results.

Create a ``UniversalDetector`` object, then call its ``feed`` method
repeatedly with each block of text. If the detector reaches a minimum
threshold of confidence, it will set ``detector.done`` to ``True``.

Once you've exhausted the source text, call ``detector.close()``, which
will do some final calculations in case the detector didn't hit its
minimum confidence threshold earlier. Then ``detector.result`` will be a
dictionary containing the auto-detected character encoding and
confidence level (the same as the ``chardet.detect`` function
`returns <#example-using-the-detect-function>`__).


Example: Detecting encoding incrementally
-----------------------------------------

.. code:: python

    import urllib.request
    from chardet.universaldetector import UniversalDetector

    usock = urllib.request.urlopen('https://www.google.co.jp/')
    detector = UniversalDetector()
    for line in usock.readlines():
        detector.feed(line)
        if detector.done: break
    detector.close()
    usock.close()
    print(detector.result)

.. code:: python

    {'encoding': 'UTF-8', 'confidence': 0.99, 'language': ''}

``UniversalDetector`` also accepts ``encoding_era`` and ``max_bytes``
parameters:

.. code:: python

    from chardet.enums import EncodingEra
    from chardet.universaldetector import UniversalDetector

    detector = UniversalDetector(encoding_era=EncodingEra.ALL)

If you want to detect the encoding of multiple texts (such as separate
files), you can re-use a single ``UniversalDetector`` object. Just call
``detector.reset()`` at the start of each file, call ``detector.feed``
as many times as you like, and then call ``detector.close()`` and check
the ``detector.result`` dictionary for the file's results.

Example: Detecting encodings of multiple files
----------------------------------------------

.. code:: python

    import glob
    from chardet.universaldetector import UniversalDetector

    detector = UniversalDetector()
    for filename in glob.glob('*.xml'):
        print(filename.ljust(60), end='')
        detector.reset()
        for line in open(filename, 'rb'):
            detector.feed(line)
            if detector.done: break
        detector.close()
        print(detector.result)


Command-line tool
-----------------

chardet includes a ``chardetect`` command-line tool:

.. code:: bash

    $ chardetect somefile.txt someotherfile.txt
    somefile.txt: Windows-1252 with confidence 0.73
    someotherfile.txt: ascii with confidence 1.0

To consider all encoding eras (not just modern web encodings):

.. code:: bash

    $ chardetect -e ALL somefile.txt

Other options:

.. code:: bash

    $ chardetect --help
    usage: chardetect [-h] [--minimal] [-l] [-e ENCODING_ERA] [--version]
                      [input ...]

    Takes one or more file paths and reports their detected encodings

    positional arguments:
      input                 File whose encoding we would like to determine.
                            (default: stdin)

    options:
      -h, --help            show this help message and exit
      --minimal             Print only the encoding to standard output
      -l, --legacy          Rename legacy encodings to more modern ones.
      -e ENCODING_ERA, --encoding-era ENCODING_ERA
                            Which era of encodings to consider (default:
                            MODERN_WEB). Choices: MODERN_WEB, LEGACY_ISO,
                            LEGACY_MAC, LEGACY_REGIONAL, DOS, MAINFRAME, ALL
      --version             show program's version number and exit
```

**Step 2: Build docs to verify**

Run: `cd docs && uv run make html 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add docs/usage.rst
git commit -m "docs: update usage.rst with encoding_era, detect_all, and CLI"
```

---

### Task 3: Rewrite `docs/how-it-works.rst`

**Files:**
- Modify: `docs/how-it-works.rst`

**Step 1: Rewrite how-it-works.rst**

Replace with a full rewrite reflecting the 6.0 detection pipeline.

```rst
How it works
============

This is a guide to how chardet's detection algorithm works internally.

You may also be interested in the research paper which originally inspired
the Mozilla implementation that chardet is based on: `A composite approach
to language/encoding
detection <https://www-archive.mozilla.org/projects/intl/UniversalCharsetDetection.html>`__.

Overview
--------

The main entry point is ``universaldetector.py``, which contains the
``UniversalDetector`` class. (The ``detect`` function in
``chardet/__init__.py`` is a convenience wrapper that creates a
``UniversalDetector``, feeds it data, and returns the result.)

``UniversalDetector`` processes input through a pipeline of probers,
each specialized for a category of encodings. Detection proceeds
through these stages in order:

#. **BOM detection** — immediate identification of UTF-8-SIG, UTF-16,
   or UTF-32 via byte order marks.
#. **UTF-16/32 without BOM** — ``UTF1632Prober`` detects UTF-16/32 by
   analyzing null-byte patterns and byte distributions.
#. **Escaped encodings** — ``EscCharSetProber`` detects 7-bit encodings
   that use escape sequences (``ISO-2022-JP``, ``ISO-2022-KR``,
   ``HZ-GB-2312``).
#. **Multi-byte encodings** — ``MBCSGroupProber`` runs probers for
   ``UTF-8``, ``GB18030``, ``Big5``, ``EUC-JP``, ``EUC-KR``,
   ``Shift-JIS``, ``CP949``, and ``Johab``.
#. **Single-byte encodings** — ``SBCSGroupProber`` runs hundreds of
   encoding+language-specific probers using bigram frequency models.
#. **Encoding era filtering** — results are filtered by the requested
   ``EncodingEra`` tier, and close confidence scores are broken by
   preferring more modern encodings.

BOM detection
-------------

If the text starts with a byte order mark (BOM), ``UniversalDetector``
immediately identifies the encoding as ``UTF-8-SIG``, ``UTF-16 BE/LE``,
or ``UTF-32 BE/LE`` and returns the result without further processing.

UTF-16/32 without BOM
----------------------

``UTF1632Prober`` (defined in ``utf1632prober.py``) detects UTF-16 and
UTF-32 encoded text that lacks a BOM. It analyzes the distribution of
null bytes: UTF-32 produces characteristic patterns of 3 null bytes per
character for ASCII-range text, while UTF-16 produces alternating null
and non-null bytes.

Escaped encodings
-----------------

If the text contains escape sequences, ``UniversalDetector`` creates an
``EscCharSetProber`` (defined in ``escprober.py``) which runs state
machines for ``HZ-GB-2312``, ``ISO-2022-JP``, and ``ISO-2022-KR``
(defined in ``escsm.py``). Each state machine processes the text one
byte at a time. If any state machine uniquely identifies the encoding,
the result is returned immediately. State machines that encounter
illegal sequences are dropped.

Multi-byte encodings
--------------------

When high-bit characters are detected, ``UniversalDetector`` creates a
``MBCSGroupProber`` (defined in ``mbcsgroupprober.py``) which manages
probers for each multi-byte encoding:

- ``UTF8Prober`` — UTF-8
- ``GB18030Prober`` — GB18030 / GB2312 (Simplified Chinese)
- ``Big5Prober`` — Big5 (Traditional Chinese)
- ``EUCJPProber`` — EUC-JP (Japanese)
- ``SJISProber`` — Shift-JIS (Japanese)
- ``EUCKRProber`` — EUC-KR (Korean)
- ``CP949Prober`` — CP949 (Korean)
- ``JOHABProber`` — Johab (Korean)

Each multi-byte prober inherits from ``MultiByteCharSetProber`` (defined
in ``mbcharsetprober.py``) and uses two analysis techniques:

**Coding state machines** (defined in ``mbcssm.py``) process the text
one byte at a time, looking for byte sequences that are valid or invalid
in the target encoding. An illegal sequence immediately eliminates that
encoding from consideration. A uniquely identifying sequence produces an
immediate positive result.

**Character distribution analysis** (defined in ``chardistribution.py``)
uses language-specific frequency tables to measure how well the decoded
characters match expected usage patterns. Once enough text has been
processed, a confidence rating is calculated.

The case of Japanese is more complex. Single-character distribution
analysis alone cannot always distinguish ``EUC-JP`` from ``Shift-JIS``,
so ``SJISProber`` (defined in ``sjisprober.py``) also uses 2-character
context analysis. ``SJISContextAnalysis`` and ``EUCJPContextAnalysis``
(both defined in ``jpcntx.py``) check the frequency of Hiragana
syllabary characters to help distinguish between the two encodings.

Single-byte encodings
---------------------

``SBCSGroupProber`` (defined in ``sbcsgroupprober.py``) manages hundreds
of ``SingleByteCharSetProber`` instances, one for each combination of
single-byte encoding and language. For example, ``Windows-1252`` is
paired with English, French, German, Spanish, and many other Western
European languages, while ``KOI8-R`` is paired with Russian.

Every single-byte encoding is detected the same way: each
``SingleByteCharSetProber`` (defined in ``sbcharsetprober.py``) takes a
bigram language model as input. These models (stored in
``lang*model.py`` files) define how frequently each pair of consecutive
characters appears in typical text for that language and encoding. The
prober tallies bigram frequencies in the input and calculates a
confidence score.

The bigram models are trained using the ``create_language_model.py``
script from the CulturaX multilingual corpus, covering 45+ languages.
This unified approach replaces the older system where only a few
languages had trained models and Western encodings relied on
special-case heuristics.

Hebrew is handled as a special case by ``HebrewProber`` (defined in
``hebrewprober.py``), which distinguishes between Visual Hebrew (stored
right-to-left, displayed verbatim) and Logical Hebrew (stored in
reading order, rendered right-to-left by the client) by analyzing the
positions of final-form characters.

Encoding era filtering and tie-breaking
---------------------------------------

After all probers report their confidence scores, ``UniversalDetector``
filters results by the requested ``EncodingEra``. Only encodings
belonging to the selected era(s) are considered.

When multiple encodings have very close confidence scores, the detector
prefers encodings from more modern tiers (``MODERN_WEB`` over
``LEGACY_ISO`` over ``LEGACY_MAC``, and so on). This prevents legacy
encodings from winning ties against their modern equivalents.

See :doc:`supported-encodings` for which encodings belong to each era.
```

**Step 2: Build docs to verify**

Run: `cd docs && uv run make html 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add docs/how-it-works.rst
git commit -m "docs: rewrite how-it-works.rst for 6.0 detection pipeline"
```

---

### Task 4: Regenerate `docs/api/chardet.rst`

**Files:**
- Modify: `docs/api/chardet.rst`

**Step 1: Rewrite api/chardet.rst**

Replace with current module list. Include all current modules, remove deleted ones (`compat`, `latin1prober`, `gb2312prober`, `gb2312freq`). Add new modules (`gb18030prober`, `johabprober`, `johabfreq`, `utf1632prober`, `enums`, `resultdict`, `codingstatemachinedict`). Add all 45 `lang*model.py` files. Add `metadata` subpackage.

The automodule directives will be generated for every `.py` file under `chardet/` (excluding `__init__.py`, `__main__.py`, `version.py`, and `__pycache__`).

Note: The complete list of lang*model files is: langarabicmodel, langbelarusianmodel, langbretonmodel, langbulgarianmodel, langcroatianmodel, langczechmodel, langdanishmodel, langdutchmodel, langenglishmodel, langesperantomodel, langestonianmodel, langfarsimodel, langfinnishmodel, langfrenchmodel, langgermanmodel, langgreekmodel, langhebrewmodel, langhungarianmodel, langicelandicmodel, langindonesianmodel, langirishmodel, langitalianmodel, langkazakhmodel, langlatvianmodel, langlithuanianmodel, langmacedonianmodel, langmalaymodel, langmaltesemodel, langnorwegianmodel, langpolishmodel, langportuguesemodel, langromanianmodel, langrussianmodel, langscottishgaelicmodel, langserbianmodel, langslovakmodel, langslovenemodel, langspanishmodel, langswedishmodel, langtajikmodel, langthaimodel, langturkishmodel, langukrainianmodel, langvietnamesemodel, langwelshmodel.

Write the complete file with automodule directives for all modules above. Group the language models under a single heading to avoid clutter.

**Step 2: Build docs to verify no broken references**

Run: `cd docs && uv run make html 2>&1 | grep -i "error\|warning" | head -20`
Expected: No errors (some warnings about missing references are OK)

**Step 3: Commit**

```bash
git add docs/api/chardet.rst
git commit -m "docs: regenerate API reference for current module list"
```

---

### Task 5: Update `docs/faq.rst`

**Files:**
- Modify: `docs/faq.rst`

**Step 1: Update the "Who wrote this" section**

Replace the existing "Who wrote this detection algorithm?" section content with:

```rst
Who wrote this detection algorithm?
-----------------------------------

This library is a port of `the auto-detection code in
Mozilla <https://www-archive.mozilla.org/projects/intl/chardet.html>`__.
The original structure has been largely maintained, though chardet 6.0
significantly expanded the detection capabilities by adding unified
bigram language models (trained on the
`CulturaX <https://huggingface.co/datasets/uonlp/CulturaX>`__ multilingual
corpus) for all single-byte encodings across 45+ languages.

You may also be interested in the research paper which led to the
Mozilla implementation, `A composite approach to language/encoding
detection <https://www-archive.mozilla.org/projects/intl/UniversalCharsetDetection.html>`__.
```

Leave all other sections unchanged.

**Step 2: Build docs to verify**

Run: `cd docs && uv run make html 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add docs/faq.rst
git commit -m "docs: update faq.rst for 6.0 rewrite"
```

---

### Task 6: Update `README.rst`

**Files:**
- Modify: `README.rst`

**Step 1: Update badges**

Replace the Travis CI and Coveralls badges with a GitHub Actions badge:

```rst
.. image:: https://github.com/chardet/chardet/actions/workflows/test.yml/badge.svg?branch=main
   :alt: Build status
   :target: https://github.com/chardet/chardet/actions/workflows/test.yml
```

Remove the Coveralls badge entirely. Keep the PyPI version and license badges but update their URLs:

```rst
.. image:: https://img.shields.io/pypi/v/chardet.svg
   :target: https://pypi.org/project/chardet/
   :alt: Latest version on PyPI

.. image:: https://img.shields.io/pypi/l/chardet.svg
   :alt: License
```

**Step 2: Update encoding list**

Replace the flat encoding list with a shorter summary that references the full docs, rather than duplicating the entire list. Something like:

```rst
Detects over 70 character encodings including:

- All major Unicode encodings (UTF-8, UTF-16, UTF-32)
- Windows code pages (Windows-1250 through Windows-1258)
- ISO-8859 family (ISO-8859-1 through ISO-8859-16)
- CJK encodings (Big5, GB18030, EUC-JP, EUC-KR, Shift-JIS, and more)
- Cyrillic encodings (KOI8-R, KOI8-U, IBM866, and more)
- Mac encodings (MacRoman, MacCyrillic, and more)
- DOS/OEM code pages (CP437, CP850, CP866, and more)
- EBCDIC variants (CP037, CP500)

See the `full list of supported encodings <https://chardet.readthedocs.io/en/latest/supported-encodings.html>`_.
```

**Step 3: Verify Python version requirement is correct**

The README already says "Requires Python 3.10+." — confirm this is still accurate (it is).

**Step 4: Commit**

```bash
git add README.rst
git commit -m "docs: update README badges and encoding list"
```

---

### Task 7: Update `docs/conf.py`

**Files:**
- Modify: `docs/conf.py`

**Step 1: Fix deprecated settings**

Change `master_doc` to `root_doc`:

```python
# Before
master_doc = "index"

# After
root_doc = "index"
```

Simplify the RTD theme setup (modern sphinx-rtd-theme doesn't need `get_html_theme_path`):

```python
# Before
on_rtd = os.environ.get("READTHEDOCS", None) == "True"
if not on_rtd:
    import sphinx_rtd_theme

    html_theme = "sphinx_rtd_theme"
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# After
html_theme = "sphinx_rtd_theme"
```

**Step 2: Build docs to verify**

Run: `cd docs && uv run make html 2>&1 | tail -5`
Expected: Build succeeds

**Step 3: Commit**

```bash
git add docs/conf.py
git commit -m "docs: fix deprecated settings in conf.py"
```

---

### Task 8: Final verification

**Step 1: Full docs build**

Run: `cd docs && uv run make clean && uv run make html 2>&1 | tail -20`
Expected: Build completes successfully. Check for any warnings about broken cross-references.

**Step 2: Spot-check rendered HTML**

Run: `open docs/_build/html/index.html` (macOS) to visually verify the rendered docs look correct.

**Step 3: Run project tests to ensure nothing broke**

Run: `uv run pytest test.py -x -q`
Expected: All tests pass (docs changes shouldn't affect tests, but verify anyway).

**Step 4: Run linters**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: All checks pass.
