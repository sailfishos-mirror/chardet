Performance
===========

Benchmarked against 2,521 test files from the
`chardet test suite <https://github.com/chardet/test-data>`_. All
detectors evaluated with the same equivalence rules. Numbers below are
CPython 3.14 unless noted.

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
     - 8,740ms
     - 8,720ms
     - 8,700ms
     - 8,700ms
   * - 3.13t (pure)
     - 10,150ms
     - 8,530ms (1.2x)
     - 4,360ms (2.3x)
     - 5,050ms (2.0x)
   * - 3.13 (mypyc)
     - 4,650ms
     - 4,700ms
     - 4,760ms
     - 4,760ms
   * - **3.13t (mypyc)**
     - 4,630ms
     - 2,350ms (2.0x)
     - 1,300ms (3.6x)
     - **1,120ms (4.1x)**
   * - 3.14 (pure)
     - 6,460ms
     - 6,490ms
     - 6,510ms
     - 6,500ms
   * - 3.14t (pure)
     - 7,280ms
     - 6,330ms (1.2x)
     - 3,000ms (2.4x)
     - 1,830ms (4.0x)
   * - 3.14 (mypyc)
     - 4,700ms
     - 4,690ms
     - 4,670ms
     - 4,670ms
   * - **3.14t (mypyc)**
     - 5,390ms
     - 2,690ms (2.0x)
     - 1,450ms (3.7x)
     - **1,160ms (4.6x)**

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
     - 390
     - baseline
   * - mypyc compiled
     - 581
     - **1.49x**

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
     - 4,336ms
     - 579
     - 1.73ms
     - 0.54ms
     - 4.15ms
     - 5.16ms
   * - CPython 3.10
     - pure
     - 7,987ms
     - 314
     - 3.18ms
     - 1.16ms
     - 7.03ms
     - 9.02ms
   * - **CPython 3.11**
     - **mypyc**
     - **3,746ms**
     - **670**
     - **1.49ms**
     - **0.46ms**
     - **3.56ms**
     - **4.51ms**
   * - CPython 3.11
     - pure
     - 6,490ms
     - 387
     - 2.59ms
     - 0.94ms
     - 5.73ms
     - 7.44ms
   * - CPython 3.12
     - mypyc
     - 4,320ms
     - 581
     - 1.72ms
     - 0.54ms
     - 4.02ms
     - 5.16ms
   * - CPython 3.12
     - pure
     - 6,433ms
     - 390
     - 2.56ms
     - 0.95ms
     - 5.55ms
     - 7.20ms
   * - CPython 3.13
     - mypyc
     - 4,703ms
     - 534
     - 1.87ms
     - 0.58ms
     - 4.37ms
     - 5.67ms
   * - CPython 3.13
     - pure
     - 8,560ms
     - 293
     - 3.41ms
     - 1.28ms
     - 7.44ms
     - 9.44ms
   * - CPython 3.14
     - mypyc
     - 4,616ms
     - 544
     - 1.84ms
     - 0.58ms
     - 4.36ms
     - 5.61ms
   * - CPython 3.14
     - pure
     - 6,514ms
     - 385
     - 2.60ms
     - 0.97ms
     - 5.67ms
     - 7.43ms
   * - PyPy 3.10
     - pure
     - 6,194ms
     - 405
     - 2.47ms
     - 0.26ms
     - 5.15ms
     - 7.37ms
   * - PyPy 3.11
     - pure
     - 6,128ms
     - 410
     - 2.44ms
     - 0.26ms
     - 5.08ms
     - 7.83ms

**CPython 3.11 + mypyc is the fastest combination** at 670 files/s.
mypyc provides a 1.4--1.8x speedup across CPython versions. PyPy's JIT
is competitive with mypyc: pure Python on PyPy (410 files/s) beats every
pure CPython version and reaches 61--100% of mypyc-compiled CPython
throughput.
