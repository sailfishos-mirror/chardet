Frequently Asked Questions
==========================

Why does detect() return None for encoding?
--------------------------------------------

chardet returns ``None`` when the data appears to be binary rather than
text. This happens when the data contains null bytes or a high proportion
of control characters that don't match any known text encoding.

.. code-block:: python

   result = chardet.detect(b"\x00\x01\x02\x03")
   # {'encoding': None, 'confidence': None, 'language': None}

How do I increase accuracy?
----------------------------

- **Provide more data.** The more bytes chardet can examine, the more
  accurate the result. The default limit is 200,000 bytes.
- **Broaden the encoding era.** By default, chardet only considers modern
  web encodings. If your data may use legacy encodings, pass
  ``encoding_era=EncodingEra.ALL``.
- **Use detect_all().** If the top result is wrong, the correct encoding
  may be the second candidate. :func:`chardet.detect_all` returns all
  candidates ranked by confidence.

What changed from chardet 5.x?
-------------------------------

chardet 6.x was a major rewrite:

- Dramatically improved accuracy (96.4% vs 68.0%)
- 29x faster than chardet 6.0.0, 5.5x faster than chardet 5.2.0
- Encoding era system (:class:`~chardet.EncodingEra`) for filtering
  candidates
- Language detection for every file (90.9% accuracy)
- Thread-safe :func:`~chardet.detect` and :func:`~chardet.detect_all`
- Free-threaded Python support (3.13t+)
- Negligible import memory (96 bytes)
- Zero runtime dependencies

The public API is backward-compatible. ``detect()``, ``detect_all()``,
and ``UniversalDetector`` work the same way.

How is chardet different from charset-normalizer?
--------------------------------------------------

`charset-normalizer <https://github.com/Ousret/charset_normalizer>`_ is
an alternative encoding detector. Key differences:

- **Accuracy:** chardet achieves 96.4% vs charset-normalizer's 89.0% on
  the same test suite.
- **Speed:** chardet is 5.6x faster (6s vs 34s for 2,161 files).
- **Memory:** chardet uses 5x less peak memory (20 MiB vs 102 MiB).
- **Language detection:** chardet reports the detected language;
  charset-normalizer does not.
- **Encoding breadth:** chardet supports EBCDIC, Mac, and DOS encodings
  that charset-normalizer does not.

How is chardet different from cchardet?
----------------------------------------

`cchardet <https://github.com/faust-streaming/faust-cchardet>`_ wraps
Mozilla's uchardet C/C++ library. Key differences:

- **Accuracy:** chardet achieves 96.4% vs cchardet's 56.8%.
- **Speed:** cchardet is faster (0.73s vs 6s) due to C implementation.
- **Encoding breadth:** chardet supports 49 more encodings than cchardet,
  including EBCDIC, Mac, Baltic, and BOM-less UTF-16/32.
- **Dependencies:** chardet is pure Python with zero dependencies.
  cchardet requires a C compiler to build from source.

Is chardet thread-safe?
-------------------------

:func:`chardet.detect` and :func:`chardet.detect_all` are fully
thread-safe and can be called concurrently from any number of threads.

:class:`~chardet.UniversalDetector` instances are **not** thread-safe.
Create one instance per thread when using the streaming API.

Does chardet work on PyPy?
---------------------------

Yes. chardet is pure Python and works on PyPy without modification.
The optional mypyc compilation is CPython-only; PyPy uses the pure-Python
code path automatically.
