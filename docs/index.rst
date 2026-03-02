chardet documentation
=====================

**chardet** is a universal character encoding detector for Python. It analyzes
byte strings and returns the detected encoding, confidence score, and language.

.. code-block:: python

   import chardet

   result = chardet.detect(b"\xc3\xa9\xc3\xa0\xc3\xbc")
   print(result)
   # {'encoding': 'utf-8', 'confidence': 0.99, 'language': 'French'}

chardet 7.0 is a ground-up, MIT-licensed rewrite — same package name, same
public API, drop-in replacement for chardet 5.x/6.x. Python 3.10+, zero
runtime dependencies, works on PyPy.

- **96.8% accuracy** on 2,179 test files
- **28x faster** than chardet 6.0.0
- **Language detection** for every result (90.5% accuracy)
- **99 encodings** across six encoding eras
- **Thread-safe** ``detect()`` and ``detect_all()``

.. toctree::
   :maxdepth: 2
   :caption: Contents

   usage
   supported-encodings
   how-it-works
   performance
   faq
   api/index
   contributing
   changelog
