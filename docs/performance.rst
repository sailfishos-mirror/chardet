Performance
===========

Benchmarked against 2,517 test files from the
`chardet test suite <https://github.com/chardet/test-data>`_. All
detectors evaluated with the same equivalence rules. Numbers below are
CPython 3.14 unless noted.

Detecting a superset of the expected encoding is counted as correct,
since the superset decodes the data without loss (e.g., detecting
Windows-1252 when the expected answer is ISO-8859-1, or GB18030 when
the expected answer is GB2312). Byte-order variants of the same
encoding (e.g., UTF-16-LE vs UTF-16) are also treated as equivalent.
These rules are applied equally to all detectors.

Accuracy
--------

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 15

   * - Detector
     - Correct
     - Accuracy
     - Speed
   * - **chardet 7.4.0 (mypyc)**
     - **2499/2517**
     - **99.3%**
     - **551 files/s**
   * - chardet 6.0.0
     - 2219/2517
     - 88.2%
     - 12 files/s
   * - charset-normalizer 3.4.6 (mypyc)
     - 2149/2517
     - 85.4%
     - 376 files/s
   * - cchardet 2.1.19
     - 1407/2517
     - 55.9%
     - 2,005 files/s

chardet leads all detectors on accuracy: **+11.1pp** vs chardet 6.0.0,
**+13.9pp** vs charset-normalizer 3.4.6, and **+43.4pp** vs cchardet 2.1.19.

Speed
-----

.. list-table::
   :header-rows: 1
   :widths: 30 12 12 12 12 12

   * - Detector
     - Files/s
     - Mean
     - Median
     - p90
     - p95
   * - cchardet 2.1.19
     - 2,005
     - 0.50ms
     - 0.04ms
     - 0.64ms
     - 0.99ms
   * - **chardet 7.4.0 (mypyc)**
     - **551**
     - **1.81ms**
     - **0.54ms**
     - **4.61ms**
     - **5.84ms**
   * - charset-normalizer 3.4.6 (mypyc)
     - 376
     - 2.65ms
     - 1.46ms
     - 6.86ms
     - 10.45ms
   * - chardet 6.0.0
     - 12
     - 85.16ms
     - 1.70ms
     - 190.84ms
     - 394.63ms

With mypyc compilation, chardet 7.4.0 is **47x faster** than chardet 6.0.0 and
**1.5x faster** than charset-normalizer 3.4.6 (mypyc). Median time per file is
0.54ms.

Memory
------

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 15 15

   * - Detector
     - Import Time
     - Import Memory
     - Peak Memory
     - RSS
   * - **chardet 7.4.0**
     - **0.013s**
     - **0 B**
     - **52.9 MiB**
     - **137.0 MiB**
   * - chardet 6.0.0
     - 0.053s
     - 13.0 MiB
     - 29.5 MiB
     - 122.3 MiB
   * - charset-normalizer 3.4.6
     - 0.013s
     - 3.4 MiB
     - 78.8 MiB
     - 238.9 MiB
   * - cchardet 2.1.19
     - 0.001s
     - 28.1 KiB
     - 155.0 KiB
     - 87.7 MiB

chardet uses **1.5x less peak memory** than charset-normalizer 3.4.6 and
**1.7x less RSS**.

Language Detection
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 20

   * - Detector
     - Correct
     - Accuracy
   * - **chardet 7.4.0**
     - **2400/2509**
     - **95.7%**
   * - charset-normalizer 3.4.6
     - 1486/2509
     - 59.2%
   * - chardet 6.0.0
     - 1003/2509
     - 40.0%
   * - cchardet 2.1.19
     - 0/2509
     - 0.0%

chardet detects language with **95.7% accuracy** --- +36.5pp vs
charset-normalizer 3.4.6 and +55.7pp vs chardet 6.0.0. cchardet 2.1.19 does
not report language.

Accuracy on charset-normalizer's Test Set
------------------------------------------

charset-normalizer maintains its own test dataset at
`char-dataset <https://github.com/Ousret/char-dataset>`_. 469 of those
files also exist in the chardet test suite (matched by content hash),
so we can compare both detectors on charset-normalizer's own ground
truth. We filed
`an issue <https://github.com/Ousret/char-dataset/issues/1>`_ about
the 5 files we excluded (4 ambiguous Cyrillic files and 1 corrupted
Vietnamese file) and 2 we relabeled (UTF-8-SIG, not UTF-8).

.. list-table::
   :header-rows: 1
   :widths: 35 15 15 15

   * - Detector
     - Correct
     - Encoding Accuracy
     - Language Accuracy
   * - **chardet 7.4.0 (mypyc)**
     - **463/469**
     - **98.7%**
     - **92.8%**
   * - charset-normalizer 3.4.6 (mypyc)
     - 453/469
     - 96.6%
     - 85.9%

chardet is **+2.1pp more accurate** than charset-normalizer 3.4.6 on
charset-normalizer's own test data, and **+6.9pp** on language
detection.

You can reproduce these numbers with
``python scripts/compare_detectors.py --cn-dataset --cn --mypyc``.

Thread Safety
-------------

:func:`chardet.detect` and :func:`chardet.detect_all` are fully thread-safe.
Each call carries its own state with no shared mutable data between threads.
Thread safety adds no measurable overhead (< 0.1%).

On free-threaded Python (GIL disabled), detection scales with threads.
Standard GIL Python shows no scaling --- the GIL serializes threads.
Benchmarked with 2,517 files, ``encoding_era=ALL``:

.. list-table::
   :header-rows: 1
   :widths: 14 14 14 14 14

   * - Python
     - 1 thread
     - 2 threads
     - 4 threads
     - 8 threads
   * - 3.13 (pure)
     - 10,140ms
     - 10,040ms
     - 10,060ms
     - 10,130ms
   * - 3.13t (pure)
     - 9,890ms
     - 7,930ms (1.2x)
     - 4,890ms (2.0x)
     - 4,720ms (2.1x)
   * - 3.13 (mypyc)
     - 4,980ms
     - 4,930ms
     - 4,920ms
     - 4,930ms
   * - **3.13t (mypyc)**
     - 4,570ms
     - 2,450ms (1.9x)
     - 1,330ms (3.4x)
     - **1,040ms (4.4x)**
   * - 3.14 (pure)
     - 7,670ms
     - 7,720ms
     - 7,800ms
     - 7,880ms
   * - 3.14t (pure)
     - 8,330ms
     - 6,160ms (1.4x)
     - 2,640ms (3.2x)
     - 2,070ms (4.0x)
   * - 3.14 (mypyc)
     - 4,620ms
     - 4,590ms
     - 4,600ms
     - 4,590ms
   * - **3.14t (mypyc)**
     - 5,020ms
     - 2,650ms (1.9x)
     - 1,420ms (3.5x)
     - **1,180ms (4.3x)**

Individual :class:`~chardet.UniversalDetector` instances are not thread-safe.
Create one instance per thread when using the streaming API.

Optional mypyc Compilation
--------------------------

Prebuilt `mypyc <https://mypyc.readthedocs.io>`_-compiled wheels are
published to PyPI for CPython on Linux, macOS, and Windows. A regular
``pip install chardet`` will pick them up automatically --- no extra flags
needed.

.. list-table::
   :header-rows: 1
   :widths: 30 20 20

   * - Build
     - Files/s
     - Speedup
   * - Pure Python
     - 330
     - baseline
   * - mypyc compiled
     - 551
     - **1.67x**

Pure-Python wheels are always available for PyPy and platforms without
prebuilt binaries.

Historical Performance
----------------------

Accuracy and speed of every Python 3-compatible chardet release and its
predecessor `charade <https://pypi.org/project/charade/>`_, measured on
the same 2,517-file test suite with the same equivalence rules. Pure
Python on CPython 3.14 for versions before 7.0; mypyc-compiled for
7.0+, matching what ``pip install chardet`` delivers. Language column
shows "---" for versions that did not support language detection.

.. list-table::
   :header-rows: 1
   :widths: 22 10 12 10 10 10

   * - Version
     - Date
     - Correct
     - Accuracy
     - Files/s
     - Language
   * - charade 1.0.0
     - 2012-12
     - 716/2517
     - 28.4%
     - 43
     - ---
   * - charade 1.0.1
     - 2012-12
     - 714/2517
     - 28.4%
     - 43
     - ---
   * - charade 1.0.3
     - 2013-01
     - 1018/2517
     - 40.4%
     - 48
     - ---
   * - chardet 2.2.1
     - 2013-12
     - 1019/2517
     - 40.5%
     - 47
     - ---
   * - chardet 2.3.0
     - 2014-10
     - 1165/2517
     - 46.3%
     - 48
     - ---
   * - chardet 3.0.4
     - 2017-06
     - 1253/2517
     - 49.8%
     - 56
     - 16.2%
   * - chardet 4.0.0
     - 2020-12
     - 1253/2517
     - 49.8%
     - 59
     - 16.9%
   * - chardet 5.0.0
     - 2022-06
     - 1618/2517
     - 64.3%
     - 57
     - 16.9%
   * - chardet 5.2.0
     - 2023-08
     - 1645/2517
     - 65.4%
     - 55
     - 16.7%
   * - chardet 6.0.0
     - 2026-02
     - 2219/2517
     - 88.2%
     - 11
     - 40.0%
   * - **chardet 7.4.0 (mypyc)**
     - **2026-03**
     - **2499/2517**
     - **99.3%**
     - **551**
     - **95.7%**

chardet 3.0.1--3.0.4 had identical accuracy and speed; only 3.0.4 is
shown. chardet 5.1.0--5.2.0 were likewise identical. charade 1.0.2 could
not be installed on Python 3.14. chardet 3.0.0 crashed on Python 3.14
and is omitted.

Performance Across Python Versions
-----------------------------------

Benchmarked chardet 7.4.0 across all supported Python versions
(macOS aarch64, 2,517 files, ``encoding_era=ALL``). CPython versions
install mypyc-compiled wheels automatically; PyPy receives the
pure-Python wheel.

.. list-table::
   :header-rows: 1
   :widths: 16 8 10 10 10 10 10 10

   * - Python
     - Wheel
     - Total
     - Files/s
     - Mean
     - Median
     - p90
     - p95
   * - CPython 3.10
     - mypyc
     - 4,015ms
     - 627
     - 1.60ms
     - 0.55ms
     - 3.84ms
     - 4.79ms
   * - CPython 3.10
     - pure
     - 9,180ms
     - 274
     - 3.65ms
     - 1.36ms
     - 8.46ms
     - 10.89ms
   * - **CPython 3.11**
     - **mypyc**
     - **3,939ms**
     - **639**
     - **1.56ms**
     - **0.53ms**
     - **3.83ms**
     - **4.77ms**
   * - CPython 3.11
     - pure
     - 7,145ms
     - 352
     - 2.84ms
     - 1.05ms
     - 6.61ms
     - 8.42ms
   * - CPython 3.12
     - mypyc
     - 4,429ms
     - 568
     - 1.76ms
     - 0.51ms
     - 4.46ms
     - 5.58ms
   * - CPython 3.12
     - pure
     - 7,655ms
     - 329
     - 3.04ms
     - 1.06ms
     - 7.17ms
     - 9.24ms
   * - CPython 3.13
     - mypyc
     - 4,914ms
     - 512
     - 1.95ms
     - 0.58ms
     - 4.89ms
     - 6.03ms
   * - CPython 3.13
     - pure
     - 9,911ms
     - 254
     - 3.94ms
     - 1.42ms
     - 9.20ms
     - 11.72ms
   * - CPython 3.14
     - mypyc
     - 4,564ms
     - 551
     - 1.81ms
     - 0.54ms
     - 4.61ms
     - 5.84ms
   * - CPython 3.14
     - pure
     - 7,632ms
     - 330
     - 3.03ms
     - 1.04ms
     - 7.18ms
     - 9.24ms
   * - PyPy 3.10
     - pure
     - 5,782ms
     - 435
     - 2.30ms
     - 0.21ms
     - 4.73ms
     - 7.03ms
   * - PyPy 3.11
     - pure
     - 5,750ms
     - 438
     - 2.28ms
     - 0.22ms
     - 4.69ms
     - 6.94ms

**CPython 3.11 + mypyc is the fastest combination** at 639 files/s.
mypyc provides a 1.7--2.3x speedup across CPython versions. PyPy's JIT
is competitive with mypyc: pure Python on PyPy (435--438 files/s) beats every
pure CPython version and reaches 68--86% of mypyc-compiled CPython
throughput.
