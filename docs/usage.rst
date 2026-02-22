Usage
=====

Basic usage
-----------

The easiest way to use the Universal Encoding Detector library is with
the ``detect`` function.


Example: Using the ``detect`` function
--------------------------------------

The ``detect`` function takes a byte string and returns a dictionary
containing the auto-detected character encoding, a confidence level
from ``0`` to ``1``, and the detected language.

.. code:: python

    >>> import urllib.request
    >>> rawdata = urllib.request.urlopen('https://www.google.co.jp/').read()
    >>> import chardet
    >>> chardet.detect(rawdata)
    {'encoding': 'UTF-8', 'confidence': 0.99, 'language': ''}

The result dictionary always contains three keys:

- ``encoding``: the detected encoding name (or ``None`` if detection failed)
- ``confidence``: a float from ``0`` to ``1``
- ``language``: the detected language (or ``''`` if not applicable)


Filtering by encoding era
--------------------------

By default, ``detect()`` only considers modern web encodings (UTF-8,
Windows-125x, CJK multi-byte, etc.). If you're working with legacy data,
you can expand the search using the ``encoding_era`` parameter:

.. code:: python

    from chardet import detect
    from chardet.enums import EncodingEra

    # Default: only modern web encodings
    result = detect(data)

    # Include all encoding eras
    result = detect(data, encoding_era=EncodingEra.ALL)

    # Only consider DOS-era encodings
    result = detect(data, encoding_era=EncodingEra.DOS)

    # Combine specific eras
    result = detect(data, encoding_era=EncodingEra.MODERN_WEB | EncodingEra.LEGACY_ISO)

See :doc:`supported-encodings` for which encodings belong to each era.


Getting all candidates with ``detect_all``
------------------------------------------

If you want to see all candidate encodings rather than just the best
guess, use ``detect_all``:

.. code:: python

    >>> import chardet
    >>> chardet.detect_all(b'\xe4\xf6\xfc')
    [{'encoding': 'Windows-1252', 'confidence': 0.73, 'language': 'German'},
     {'encoding': 'ISO-8859-1', 'confidence': 0.60, 'language': 'German'}]

Results are sorted by confidence (highest first). ``detect_all`` accepts
the same ``encoding_era``, ``should_rename_legacy``, ``max_bytes``, and
``chunk_size`` parameters as ``detect``.


Advanced usage
--------------

If you're dealing with a large amount of text, you can call the
Universal Encoding Detector library incrementally, and it will stop as
soon as it is confident enough to report its results.

Create a ``UniversalDetector`` object, then call its ``feed`` method
repeatedly with each block of text. If the detector reaches a minimum
threshold of confidence, it will set ``detector.done`` to ``True``.

Once you've exhausted the source text, call ``detector.close()``, which
will do some final calculations in case the detector didn't hit its
minimum confidence threshold earlier. Then ``detector.result`` will be a
dictionary containing the auto-detected character encoding and
confidence level (the same as the ``chardet.detect`` function
`returns <#example-using-the-detect-function>`__).


Example: Detecting encoding incrementally
-----------------------------------------

.. code:: python

    import urllib.request
    from chardet.universaldetector import UniversalDetector

    usock = urllib.request.urlopen('https://www.google.co.jp/')
    detector = UniversalDetector()
    for line in usock.readlines():
        detector.feed(line)
        if detector.done: break
    detector.close()
    usock.close()
    print(detector.result)

.. code:: python

    {'encoding': 'UTF-8', 'confidence': 0.99, 'language': ''}

``UniversalDetector`` also accepts ``encoding_era`` and ``max_bytes``
parameters:

.. code:: python

    from chardet.enums import EncodingEra
    from chardet.universaldetector import UniversalDetector

    detector = UniversalDetector(encoding_era=EncodingEra.ALL)

If you want to detect the encoding of multiple texts (such as separate
files), you can re-use a single ``UniversalDetector`` object. Just call
``detector.reset()`` at the start of each file, call ``detector.feed``
as many times as you like, and then call ``detector.close()`` and check
the ``detector.result`` dictionary for the file's results.

Example: Detecting encodings of multiple files
----------------------------------------------

.. code:: python

    import glob
    from chardet.universaldetector import UniversalDetector

    detector = UniversalDetector()
    for filename in glob.glob('*.xml'):
        print(filename.ljust(60), end='')
        detector.reset()
        for line in open(filename, 'rb'):
            detector.feed(line)
            if detector.done: break
        detector.close()
        print(detector.result)


Command-line tool
-----------------

chardet includes a ``chardetect`` command-line tool:

.. code:: bash

    $ chardetect somefile.txt someotherfile.txt
    somefile.txt: Windows-1252 with confidence 0.73
    someotherfile.txt: ascii with confidence 1.0

To consider all encoding eras (not just modern web encodings):

.. code:: bash

    $ chardetect -e ALL somefile.txt

Other options:

.. code:: text

    $ chardetect --help
    usage: chardetect [-h] [--minimal] [-l] [-e ENCODING_ERA] [--version]
                      [input ...]

    Takes one or more file paths and reports their detected encodings

    positional arguments:
      input                 File whose encoding we would like to determine.
                            (default: stdin)

    options:
      -h, --help            show this help message and exit
      --minimal             Print only the encoding to standard output
      -l, --legacy          Rename legacy encodings to more modern ones.
      -e ENCODING_ERA, --encoding-era ENCODING_ERA
                            Which era of encodings to consider (default:
                            MODERN_WEB). Choices: MODERN_WEB, LEGACY_ISO,
                            LEGACY_MAC, LEGACY_REGIONAL, DOS, MAINFRAME, ALL
      --version             show program's version number and exit
