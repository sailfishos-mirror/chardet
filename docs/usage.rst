Usage
=====

Basic usage
-----------

The easiest way to use chardet is with the ``detect`` function.


Example: Using the ``detect`` function
--------------------------------------

The ``detect`` function takes a byte string and returns a dictionary
containing the auto-detected character encoding, a confidence level
from ``0`` to ``1``, and the detected language.

.. code:: python

    >>> import chardet
    >>> chardet.detect('Strauß und Müller über Änderungen'.encode('windows-1252'))
    {'encoding': 'WINDOWS-1252', 'confidence': 0.6316251912431836, 'language': 'German'}

The result dictionary always contains three keys:

- ``encoding``: the detected encoding name (or ``None`` if detection failed)
- ``confidence``: a float from ``0`` to ``1``
- ``language``: the detected language (or ``''`` if not applicable)


Controlling how much data to process
-------------------------------------

By default, ``detect()`` reads up to 200 KB of input in 64 KB chunks.
You can tune this with the ``max_bytes`` and ``chunk_size`` parameters:

.. code:: python

    import chardet

    # Process at most 50 KB, feeding 8 KB at a time internally
    result = chardet.detect(data, max_bytes=50_000, chunk_size=8192)

These parameters also apply to ``detect_all``.


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
    >>> chardet.detect_all('Strauß und Müller über Änderungen'.encode('windows-1252'))[:3]
    [{'encoding': 'WINDOWS-1252', 'confidence': 0.6316251912431836, 'language': 'German'},
     {'encoding': 'WINDOWS-1250', 'confidence': 0.5220501710295528, 'language': 'Czech'},
     {'encoding': 'WINDOWS-1257', 'confidence': 0.5197657012389119, 'language': 'Estonian'}]

Results are sorted by confidence (highest first). ``detect_all`` accepts
the same ``encoding_era``, ``should_rename_legacy``, ``max_bytes``, and
``chunk_size`` parameters as ``detect``.


Advanced usage: incremental detection
--------------------------------------

In most cases, the ``max_bytes`` and ``chunk_size`` parameters on
``detect()`` and ``detect_all()`` are sufficient for controlling how much
data is processed. However, if you need to feed data from a custom source
(such as a network stream or a decompressor), you can use
``UniversalDetector`` directly.

Create a ``UniversalDetector`` object, then call its ``feed`` method
repeatedly with each block of data. If the detector reaches a minimum
threshold of confidence, it will set ``detector.done`` to ``True``.

Once you've exhausted the source data, call ``detector.close()`` to
finalize detection. The result is then available in ``detector.result``.

.. code:: python

    from chardet.universaldetector import UniversalDetector

    detector = UniversalDetector()
    with open('mystery-file.txt', 'rb') as f:
        for line in f:
            detector.feed(line)
            if detector.done:
                break
    detector.close()
    print(detector.result)

``UniversalDetector`` also accepts ``encoding_era`` and ``max_bytes``
parameters:

.. code:: python

    from chardet.enums import EncodingEra
    from chardet.universaldetector import UniversalDetector

    detector = UniversalDetector(encoding_era=EncodingEra.ALL)
    detector.feed(data)
    detector.close()
    print(detector.result)

If you want to detect the encoding of multiple texts (such as separate
files), you can re-use a single ``UniversalDetector`` object. Call
``detector.reset()`` at the start of each file, ``feed`` as many times as
you like, then ``close()`` and check ``detector.result``.

Example: Detecting encodings of multiple files
----------------------------------------------

.. code:: python

    import glob
    from chardet.universaldetector import UniversalDetector

    detector = UniversalDetector()
    for filename in glob.glob('*.xml'):
        detector.reset()
        with open(filename, 'rb') as f:
            for line in f:
                detector.feed(line)
                if detector.done:
                    break
        detector.close()
        print(f'{filename}: {detector.result}')


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
