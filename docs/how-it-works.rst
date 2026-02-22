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
