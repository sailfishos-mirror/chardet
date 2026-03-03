Performance
===========

Benchmarked against 2,179 test files from the
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
     - Speed
   * - **chardet 7.0 (mypyc)**
     - **2110/2179**
     - **96.8%**
     - **494 files/s**
   * - chardet 7.0 (pure)
     - 2110/2179
     - 96.8%
     - 336 files/s
   * - chardet 6.0.0
     - 2060/2179
     - 94.5%
     - 12 files/s
   * - charset-normalizer
     - 1942/2179
     - 89.1%
     - 66 files/s
   * - cchardet
     - 1245/2179
     - 57.1%
     - 1,801 files/s

chardet leads all detectors on accuracy: **+2.3pp** vs chardet 6.0.0,
**+7.7pp** vs charset-normalizer, and **+39.7pp** vs cchardet.

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
     - 1,811
     - 0.55ms
     - 0.07ms
     - 0.65ms
     - 0.92ms
   * - **chardet 7.0 (mypyc)**
     - **494**
     - **2.02ms**
     - **0.61ms**
     - **3.86ms**
     - **4.49ms**
   * - chardet 7.0 (pure)
     - 336
     - 2.98ms
     - 1.11ms
     - 5.37ms
     - 6.21ms
   * - charset-normalizer
     - 66
     - 15.17ms
     - 4.67ms
     - 49.31ms
     - 70.71ms
   * - chardet 6.0.0
     - 12
     - 83.19ms
     - 16.32ms
     - 122.32ms
     - 319.77ms

With mypyc compilation, chardet 7.0 is **41x faster** than chardet 6.0.0 and
**7.5x faster** than charset-normalizer. Even the pure-Python build is **28x
faster** than chardet 6.0.0 and **5.1x faster** than charset-normalizer.
Median time per file is 0.61ms (mypyc) / 1.11ms (pure).

Memory
------

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 15

   * - Detector
     - Import Memory
     - Peak Memory
     - RSS
   * - **chardet 7.0**
     - **96 B**
     - **22.5 MiB**
     - **96.1 MiB**
   * - chardet 6.0.0
     - 96 B
     - 16.4 MiB
     - 101.8 MiB
   * - charset-normalizer
     - 1.3 MiB
     - 101.8 MiB
     - 265.7 MiB
   * - cchardet
     - 23.6 KiB
     - 27.2 KiB
     - 62.8 MiB

chardet uses negligible import memory (96 B), **4.5x less peak memory** than
charset-normalizer, and **2.8x less RSS**.

Language Detection
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 20

   * - Detector
     - Correct
     - Accuracy
   * - **chardet 7.0**
     - **1964/2171**
     - **90.5%**
   * - chardet 6.0.0
     - 1016/2171
     - 46.8%
   * - charset-normalizer
     - 0/2171
     - 0.0%
   * - cchardet
     - 0/2171
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
     - 332
     - baseline
   * - mypyc compiled
     - 494
     - **1.49x**

Pure-Python wheels are always available for PyPy and platforms without
prebuilt binaries.
