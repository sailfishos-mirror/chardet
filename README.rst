Chardet: The Universal Character Encoding Detector
--------------------------------------------------

.. image:: https://github.com/chardet/chardet/actions/workflows/test.yml/badge.svg?branch=main
   :alt: Build status
   :target: https://github.com/chardet/chardet/actions/workflows/test.yml

.. image:: https://img.shields.io/pypi/v/chardet.svg
   :target: https://pypi.org/project/chardet/
   :alt: Latest version on PyPI

.. image:: https://img.shields.io/pypi/l/chardet.svg
   :alt: License


Detects over 70 character encodings including:

- All major Unicode encodings (UTF-8, UTF-16, UTF-32)
- Windows code pages (Windows-1250 through Windows-1258)
- ISO-8859 family (ISO-8859-1 through ISO-8859-16)
- CJK encodings (Big5, GB18030, EUC-JP, EUC-KR, Shift-JIS, and more)
- Cyrillic encodings (KOI8-R, KOI8-U, IBM866, and more)
- Mac encodings (MacRoman, MacCyrillic, and more)
- DOS/OEM code pages (CP437, CP850, CP866, and more)
- EBCDIC variants (CP037, CP500)

See the `full list of supported encodings <https://chardet.readthedocs.io/en/latest/supported-encodings.html>`_.


Requires Python 3.10+.

Installation
------------

Install from `PyPI <https://pypi.org/project/chardet/>`_::

    pip install chardet

Documentation
-------------

For users, docs are now available at https://chardet.readthedocs.io/.

Command-line Tool
-----------------

chardet comes with a command-line script which reports on the encodings of one
or more files::

    % chardetect somefile someotherfile
    somefile: windows-1252 with confidence 0.5
    someotherfile: ascii with confidence 1.0

About
-----

This is a continuation of Mark Pilgrim's excellent original chardet port from C, and `Ian Cordasco <https://github.com/sigmavirus24>`_'s
`charade <https://github.com/sigmavirus24/charade>`_ Python 3-compatible fork.

:maintainer: Dan Blanchard
