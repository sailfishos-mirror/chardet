Usage
=====

Installation
------------

.. code-block:: bash

   pip install chardet

Basic Detection
---------------

Use :func:`chardet.detect` to detect the encoding of a byte string:

.. code-block:: python

   import chardet

   result = chardet.detect(b"\xc3\xa9\xc3\xa0\xc3\xbc")
   print(result)
   # {'encoding': 'utf-8', 'confidence': 0.99, 'language': 'French'}

The result is a dictionary with three keys:

- ``"encoding"`` — the detected encoding name (e.g., ``"utf-8"``,
  ``"windows-1252"``), or ``None`` if detection failed
- ``"confidence"`` — a float between 0 and 1
- ``"language"`` — the detected language (e.g., ``"French"``), or ``None``

Multiple Candidates
~~~~~~~~~~~~~~~~~~~

Use :func:`chardet.detect_all` to get all candidate encodings ranked by
confidence:

.. code-block:: python

   results = chardet.detect_all(data)
   for r in results:
       print(f"{r['encoding']}: {r['confidence']:.2f}")

By default, results below the minimum confidence threshold (0.20) are
filtered out. Pass ``ignore_threshold=True`` to see all candidates.

Streaming Detection
-------------------

For large files or streaming data, use :class:`chardet.UniversalDetector`:

.. code-block:: python

   from chardet import UniversalDetector

   detector = UniversalDetector()
   with open("somefile.txt", "rb") as f:
       for line in f:
           detector.feed(line)
           if detector.done:
               break
   detector.close()
   print(detector.result)

Call :meth:`~chardet.UniversalDetector.reset` to reuse the detector for
another file.

Encoding Eras
-------------

By default, chardet only considers modern web encodings. Use the
``encoding_era`` parameter to broaden the search:

.. code-block:: python

   from chardet import detect, EncodingEra

   # Default: only modern web encodings
   result = detect(data)

   # Include legacy ISO, Mac, DOS, and mainframe encodings
   result = detect(data, encoding_era=EncodingEra.ALL)

   # Only legacy ISO encodings
   result = detect(data, encoding_era=EncodingEra.LEGACY_ISO)

Available eras (can be combined with ``|``):

- :attr:`~chardet.EncodingEra.MODERN_WEB` — UTF-8, Windows codepages,
  CJK encodings (default)
- :attr:`~chardet.EncodingEra.LEGACY_ISO` — ISO-8859 family
- :attr:`~chardet.EncodingEra.LEGACY_MAC` — Mac encodings
- :attr:`~chardet.EncodingEra.LEGACY_REGIONAL` — Regional codepages
  (KOI8-T, KZ-1048, etc.)
- :attr:`~chardet.EncodingEra.DOS` — DOS codepages (CP437, CP850, etc.)
- :attr:`~chardet.EncodingEra.MAINFRAME` — EBCDIC encodings
- :attr:`~chardet.EncodingEra.ALL` — All of the above

Limiting Bytes
--------------

By default, chardet examines up to 200,000 bytes. Use ``max_bytes`` to
adjust:

.. code-block:: python

   # Examine only the first 10 KB
   result = chardet.detect(data, max_bytes=10_000)

Smaller values are faster but may reduce accuracy for encodings that
require more data to distinguish.

Command-Line Tool
-----------------

chardet includes a ``chardetect`` command:

.. code-block:: bash

   # Detect encoding of files
   chardetect somefile.txt anotherfile.csv

   # Output only the encoding name
   chardetect --minimal somefile.txt

   # Include all encoding eras
   chardetect --legacy somefile.txt

   # Specific encoding era
   chardetect -e dos somefile.txt

   # Read from stdin
   cat somefile.txt | chardetect
