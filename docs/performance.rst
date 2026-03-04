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
   * - **chardet 7.0 (mypyc)**
     - **2463/2510**
     - **98.1%**
     - **546 files/s**
   * - chardet 7.0 (pure)
     - 2463/2510
     - 98.1%
     - 383 files/s
   * - chardet 6.0.0
     - 2213/2510
     - 88.2%
     - 13 files/s
   * - charset-normalizer
     - 1970/2510
     - 78.5%
     - 80 files/s
   * - cchardet
     - 1405/2510
     - 56.0%
     - 2,041 files/s

chardet leads all detectors on accuracy: **+9.9pp** vs chardet 6.0.0,
**+19.6pp** vs charset-normalizer, and **+42.1pp** vs cchardet.

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
     - 2,041
     - 0.49ms
     - 0.04ms
     - 0.60ms
     - 0.96ms
   * - **chardet 7.0 (mypyc)**
     - **546**
     - **1.83ms**
     - **0.55ms**
     - **3.91ms**
     - **5.06ms**
   * - chardet 7.0 (pure)
     - 383
     - 2.61ms
     - 0.94ms
     - 5.12ms
     - 6.74ms
   * - charset-normalizer (mypyc)
     - 80
     - 12.47ms
     - 3.94ms
     - 35.33ms
     - 63.83ms
   * - charset-normalizer (pure)
     - 55
     - 18.26ms
     - 6.21ms
     - 52.09ms
     - 94.14ms
   * - chardet 6.0.0
     - 13
     - 79.49ms
     - 2.24ms
     - 176.22ms
     - 362.23ms

With mypyc compilation, chardet 7.0 is **43x faster** than chardet 6.0.0 and
**6.8x faster** than charset-normalizer (mypyc). Even the pure-Python build is
**30x faster** than chardet 6.0.0 and **7.0x faster** than charset-normalizer
(pure). Median time per file is 0.55ms (mypyc) / 0.94ms (pure).

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
   * - **chardet 7.0**
     - **0.019s**
     - **2.7 MiB**
     - **26.2 MiB**
     - **115.9 MiB**
   * - chardet 6.0.0
     - 0.036s
     - 13.0 MiB
     - 29.5 MiB
     - 123.3 MiB
   * - charset-normalizer
     - 0.009s
     - 1.3 MiB
     - 101.2 MiB
     - 323.2 MiB
   * - cchardet
     - 0.001s
     - 23.6 KiB
     - 27.2 KiB
     - 81.7 MiB

chardet uses **3.9x less peak memory** than charset-normalizer and
**2.8x less RSS**.

Language Detection
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 20

   * - Detector
     - Correct
     - Accuracy
   * - **chardet 7.0**
     - **2380/2502**
     - **95.1%**
   * - chardet 6.0.0
     - 0/2502
     - 0.0%
   * - charset-normalizer
     - 0/2502
     - 0.0%
   * - cchardet
     - 0/2502
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
     - 383
     - baseline
   * - mypyc compiled
     - 546
     - **1.42x**

Pure-Python wheels are always available for PyPy and platforms without
prebuilt binaries.

Performance Across Python Versions
-----------------------------------

Benchmarked chardet 7.0 across all supported Python versions
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
     - 4,475ms
     - 561
     - 1.78ms
     - 0.53ms
     - 3.95ms
     - 5.09ms
   * - CPython 3.10
     - pure
     - 8,796ms
     - 285
     - 3.50ms
     - 1.22ms
     - 7.33ms
     - 9.31ms
   * - **CPython 3.11**
     - **mypyc**
     - **4,079ms**
     - **615**
     - **1.63ms**
     - **0.48ms**
     - **3.54ms**
     - **4.60ms**
   * - CPython 3.11
     - pure
     - 6,797ms
     - 369
     - 2.71ms
     - 0.92ms
     - 5.65ms
     - 7.41ms
   * - CPython 3.12
     - mypyc
     - 4,597ms
     - 546
     - 1.83ms
     - 0.55ms
     - 3.91ms
     - 5.06ms
   * - CPython 3.12
     - pure
     - 6,545ms
     - 383
     - 2.61ms
     - 0.94ms
     - 5.12ms
     - 6.74ms
   * - CPython 3.13
     - mypyc
     - 5,046ms
     - 497
     - 2.01ms
     - 0.58ms
     - 4.32ms
     - 5.65ms
   * - CPython 3.13
     - pure
     - 9,293ms
     - 270
     - 3.70ms
     - 1.30ms
     - 7.41ms
     - 9.66ms
   * - CPython 3.14
     - mypyc
     - 5,064ms
     - 496
     - 2.02ms
     - 0.60ms
     - 4.39ms
     - 5.64ms
   * - CPython 3.14
     - pure
     - 6,977ms
     - 360
     - 2.78ms
     - 0.98ms
     - 5.64ms
     - 7.32ms
   * - PyPy 3.10
     - pure
     - 6,111ms
     - 411
     - 2.43ms
     - 0.24ms
     - 4.99ms
     - 7.43ms
   * - PyPy 3.11
     - pure
     - 6,114ms
     - 410
     - 2.44ms
     - 0.25ms
     - 4.97ms
     - 7.33ms

**CPython 3.11 + mypyc is the fastest combination** at 615 files/s.
mypyc provides a 1.4--2.0x speedup across CPython versions. PyPy's JIT
is competitive with mypyc: pure Python on PyPy (411 files/s) beats every
pure CPython version and reaches 67--100% of mypyc-compiled CPython
throughput.
