chardet documentation
=====================

**chardet** is a universal character encoding detector for Python. It analyzes
byte strings and returns the detected encoding, confidence score, and language.

.. code-block:: python

   import chardet

   result = chardet.detect(b"\xc3\xa9\xc3\xa0\xc3\xbc")
   print(result)
   # {'encoding': 'utf-8', 'confidence': 0.99, 'language': 'French'}

chardet is a drop-in replacement for previous versions with the same package
name and public API. Python 3.10+, zero runtime dependencies.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   usage
   supported-encodings
   how-it-works
   performance
   faq
   api/index
