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
