Performance
===========

Benchmarked against 2,510 test files from the
`chardet test suite <https://github.com/chardet/test-data>`_. All
detectors evaluated with the same equivalence rules. Numbers below are
CPython 3.12 unless noted.

Accuracy
--------

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 15

   * - Detector
     - Correct
     - Accuracy
     - Speed
   * - **chardet 7.1.0 (mypyc)**
     - **2464/2510**
     - **98.2%**
     - **533 files/s**
   * - chardet 7.1.0 (pure)
     - 2464/2510
     - 98.2%
     - 372 files/s
   * - chardet 6.0.0
     - 2216/2510
     - 88.3%
     - 12 files/s
   * - charset-normalizer
     - 2114/2510
     - 84.2%
     - 129 files/s
   * - cchardet
     - 1406/2510
     - 56.0%
     - 1,662 files/s

chardet leads all detectors on accuracy: **+9.9pp** vs chardet 6.0.0,
**+14.0pp** vs charset-normalizer, and **+42.2pp** vs cchardet.

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
   * - cchardet
     - 1,662
     - 0.60ms
     - 0.05ms
     - 0.70ms
     - 1.18ms
   * - **chardet 7.1.0 (mypyc)**
     - **533**
     - **1.88ms**
     - **0.57ms**
     - **4.44ms**
     - **5.86ms**
   * - chardet 7.1.0 (pure)
     - 372
     - 2.69ms
     - 0.99ms
     - 5.89ms
     - 7.71ms
   * - charset-normalizer (mypyc)
     - 129
     - 7.75ms
     - 2.68ms
     - 22.47ms
     - 39.36ms
   * - charset-normalizer (pure)
     - 67
     - 15.00ms
     - 5.11ms
     - 43.44ms
     - 77.37ms
   * - chardet 6.0.0
     - 12
     - 82.70ms
     - 2.31ms
     - 180.02ms
     - 372.50ms

With mypyc compilation, chardet 7.1.0 is **44x faster** than chardet 6.0.0 and
**4.1x faster** than charset-normalizer (mypyc). Even the pure-Python build is
**31x faster** than chardet 6.0.0 and **5.6x faster** than charset-normalizer
(pure). Median time per file is 0.57ms (mypyc) / 0.99ms (pure).

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
   * - **chardet 7.1.0**
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
   * - **chardet 7.1.0**
     - **2383/2502**
     - **95.2%**
   * - charset-normalizer
     - 1476/2502
     - 59.0%
   * - chardet 6.0.0
     - 1002/2502
     - 40.0%
   * - cchardet
     - 0/2502
     - 0.0%

chardet detects language with **95.2% accuracy** — +36.2pp vs
charset-normalizer and +55.2pp vs chardet 6.0.0. cchardet does not report
language.

Thread Safety
-------------

:func:`chardet.detect` and :func:`chardet.detect_all` are fully thread-safe.
Each call carries its own state with no shared mutable data between threads.
Thread safety adds no measurable overhead (< 0.1%).

On free-threaded Python (GIL disabled), detection scales with threads.
Benchmarked with 2,510 files, ``encoding_era=ALL``:

.. list-table::
   :header-rows: 1
   :widths: 10 16 12 12 12 12

   * - Threads
     - Build
     - CPython 3.13t
     - Speedup
     - CPython 3.14t
     - Speedup
   * - 1
     - pure
     - 10,150ms
     - baseline
     - 7,280ms
     - baseline
   * - 2
     - pure
     - 8,530ms
     - 1.2x
     - 6,330ms
     - 1.2x
   * - 4
     - pure
     - 4,360ms
     - 2.3x
     - 3,000ms
     - 2.4x
   * - 8
     - pure
     - 5,050ms
     - 2.0x
     - 1,830ms
     - 4.0x
   * - 1
     - mypyc
     - 4,630ms
     - baseline
     - 5,390ms
     - baseline
   * - 2
     - mypyc
     - 2,350ms
     - 2.0x
     - 2,690ms
     - 2.0x
   * - 4
     - mypyc
     - 1,300ms
     - 3.6x
     - 1,450ms
     - 3.7x
   * - 8
     - mypyc
     - 1,120ms
     - **4.1x**
     - 1,160ms
     - **4.6x**

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

Benchmarked chardet 7.1.0 across all supported Python versions
(macOS aarch64, 2,510 files, ``encoding_era=ALL``). CPython versions
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
