Performance
===========

Benchmarked against 2,521 test files from the
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
   * - **chardet 7.3.0 (mypyc)**
     - **2473/2521**
     - **98.1%**
     - **582 files/s**
   * - chardet 6.0.0
     - 2223/2521
     - 88.2%
     - 12 files/s
   * - charset-normalizer 3.4.6 (mypyc)
     - 2152/2521
     - 85.4%
     - 373 files/s
   * - cchardet 2.1.19
     - 1410/2521
     - 55.9%
     - 1,992 files/s

chardet leads all detectors on accuracy: **+9.9pp** vs chardet 6.0.0,
**+12.7pp** vs charset-normalizer, and **+42.2pp** vs cchardet.

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
     - 1,992
     - 0.50ms
     - 0.04ms
     - 0.65ms
     - 1.00ms
   * - **chardet 7.3.0 (mypyc)**
     - **582**
     - **1.72ms**
     - **0.57ms**
     - **4.29ms**
     - **5.38ms**
   * - charset-normalizer 3.4.6 (mypyc)
     - 373
     - 2.68ms
     - 1.47ms
     - 6.90ms
     - 10.67ms
   * - chardet 6.0.0
     - 12
     - 85.68ms
     - 1.71ms
     - 190.06ms
     - 395.24ms

With mypyc compilation, chardet 7.3.0 is **50x faster** than chardet 6.0.0 and
**1.6x faster** than charset-normalizer 3.4.6 (mypyc). Median time per file is
0.57ms.

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
   * - **chardet 7.3.0**
     - **0.015s**
     - **1.9 MiB**
     - **25.9 MiB**
     - **115.6 MiB**
   * - chardet 6.0.0
     - 0.053s
     - 13.0 MiB
     - 29.5 MiB
     - 122.3 MiB
   * - charset-normalizer
     - 0.010s
     - 1.4 MiB
     - 101.3 MiB
     - 273.3 MiB
   * - cchardet
     - 0.001s
     - 23.2 KiB
     - 26.8 KiB
     - 81.9 MiB

chardet uses **3.9x less peak memory** than charset-normalizer and
**2.4x less RSS**.

Language Detection
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 20

   * - Detector
     - Correct
     - Accuracy
   * - **chardet 7.3.0**
     - **2393/2513**
     - **95.2%**
   * - charset-normalizer 3.4.6
     - 1489/2513
     - 59.3%
   * - chardet 6.0.0
     - 1004/2513
     - 40.0%
   * - cchardet 2.1.19
     - 0/2513
     - 0.0%

chardet detects language with **95.2% accuracy** — +35.9pp vs
charset-normalizer and +55.2pp vs chardet 6.0.0. cchardet does not report
language.

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
   * - **chardet 7.3.0 (mypyc)**
     - **461/469**
     - **98.3%**
     - **92.8%**
   * - charset-normalizer 3.4.6 (mypyc)
     - 453/469
     - 96.6%
     - 85.9%

chardet is **+1.7pp more accurate** than charset-normalizer on
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
Standard GIL Python shows no scaling — the GIL serializes threads.
Benchmarked with 2,521 files, ``encoding_era=ALL``:

.. list-table::
   :header-rows: 1
   :widths: 14 14 14 14 14

   * - Python
     - 1 thread
     - 2 threads
     - 4 threads
     - 8 threads
   * - 3.13 (pure)
     - 8,100ms
     - 8,290ms
     - 8,280ms
     - 8,300ms
   * - 3.13t (pure)
     - 9,690ms
     - 5,510ms (1.8x)
     - 3,820ms (2.5x)
     - 4,710ms (2.1x)
   * - 3.13 (mypyc)
     - 4,380ms
     - 4,170ms
     - 4,170ms
     - 4,170ms
   * - **3.13t (mypyc)**
     - 4,400ms
     - 2,230ms (2.0x)
     - 1,180ms (3.7x)
     - **940ms (4.7x)**
   * - 3.14 (pure)
     - 6,260ms
     - 6,210ms
     - 6,230ms
     - 6,270ms
   * - 3.14t (pure)
     - 6,760ms
     - 5,240ms (1.3x)
     - 2,840ms (2.4x)
     - 1,690ms (4.0x)
   * - 3.14 (mypyc)
     - 4,370ms
     - 4,200ms
     - 4,190ms
     - 4,260ms
   * - **3.14t (mypyc)**
     - 5,080ms
     - 2,570ms (2.0x)
     - 1,350ms (3.8x)
     - **980ms (5.2x)**

Individual :class:`~chardet.UniversalDetector` instances are not thread-safe.
Create one instance per thread when using the streaming API.

Optional mypyc Compilation
--------------------------

Prebuilt `mypyc <https://mypyc.readthedocs.io>`_-compiled wheels are
published to PyPI for CPython on Linux, macOS, and Windows. A regular
``pip install chardet`` will pick them up automatically — no extra flags
needed.

.. list-table::
   :header-rows: 1
   :widths: 30 20 20

   * - Build
     - Files/s
     - Speedup
   * - Pure Python
     - 415
     - baseline
   * - mypyc compiled
     - 588
     - **1.42x**

Pure-Python wheels are always available for PyPy and platforms without
prebuilt binaries.

Performance Across Python Versions
-----------------------------------

Benchmarked chardet 7.3.0 across all supported Python versions
(macOS aarch64, 2,521 files, ``encoding_era=ALL``). CPython versions
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
     - 4,057ms
     - 621
     - 1.61ms
     - 0.53ms
     - 4.02ms
     - 5.16ms
   * - CPython 3.10
     - pure
     - 7,662ms
     - 329
     - 3.04ms
     - 1.17ms
     - 7.07ms
     - 8.94ms
   * - **CPython 3.11**
     - **mypyc**
     - **3,454ms**
     - **730**
     - **1.37ms**
     - **0.45ms**
     - **3.37ms**
     - **4.30ms**
   * - CPython 3.11
     - pure
     - 5,821ms
     - 433
     - 2.31ms
     - 0.88ms
     - 5.41ms
     - 7.04ms
   * - CPython 3.12
     - mypyc
     - 3,994ms
     - 631
     - 1.58ms
     - 0.53ms
     - 3.95ms
     - 5.07ms
   * - CPython 3.12
     - pure
     - 6,017ms
     - 419
     - 2.39ms
     - 0.93ms
     - 5.53ms
     - 7.20ms
   * - CPython 3.13
     - mypyc
     - 4,260ms
     - 592
     - 1.69ms
     - 0.56ms
     - 4.24ms
     - 5.24ms
   * - CPython 3.13
     - pure
     - 7,984ms
     - 316
     - 3.17ms
     - 1.24ms
     - 7.26ms
     - 9.55ms
   * - CPython 3.14
     - mypyc
     - 4,283ms
     - 588
     - 1.70ms
     - 0.57ms
     - 4.26ms
     - 5.39ms
   * - CPython 3.14
     - pure
     - 6,080ms
     - 415
     - 2.41ms
     - 0.93ms
     - 5.58ms
     - 7.38ms
   * - PyPy 3.10
     - pure
     - 6,106ms
     - 413
     - 2.42ms
     - 0.26ms
     - 5.03ms
     - 7.23ms
   * - PyPy 3.11
     - pure
     - 6,047ms
     - 417
     - 2.40ms
     - 0.27ms
     - 5.03ms
     - 7.38ms

**CPython 3.11 + mypyc is the fastest combination** at 730 files/s.
mypyc provides a 1.4--1.9x speedup across CPython versions. PyPy's JIT
is competitive with mypyc: pure Python on PyPy (417 files/s) beats every
pure CPython version and reaches 57--71% of mypyc-compiled CPython
throughput.
