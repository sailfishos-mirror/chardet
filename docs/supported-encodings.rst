Supported Encodings
===================

chardet supports **81 encodings** across six encoding eras.
The default :attr:`~chardet.EncodingEra.MODERN_WEB` era covers the
encodings most commonly found on the web today. Use
:attr:`~chardet.EncodingEra.ALL` to enable detection of all encodings.

Modern Web
----------

.. list-table::
   :header-rows: 1
   :widths: 25 50 15

   * - Encoding
     - Aliases
     - Multi-byte
   * - ascii
     - us-ascii
     - No
   * - big5
     - big5-tw, csbig5
     - Yes
   * - cp874
     - windows-874
     - No
   * - cp932
     - ms932, mskanji, ms-kanji
     - Yes
   * - cp949
     - ms949, uhc
     - Yes
   * - euc-jp
     - eucjp, ujis, u-jis
     - Yes
   * - euc-kr
     - euckr
     - Yes
   * - gb18030
     - gb-18030
     - Yes
   * - hz-gb-2312
     - hz
     - Yes
   * - iso-2022-jp
     - csiso2022jp
     - Yes
   * - iso-2022-kr
     - csiso2022kr
     - Yes
   * - koi8-r
     - koi8r
     - No
   * - koi8-u
     - koi8u
     - No
   * - shift_jis
     - sjis, shiftjis, s_jis
     - Yes
   * - tis-620
     - tis620
     - No
   * - utf-16
     - utf16
     - No
   * - utf-16-be
     - utf-16be
     - No
   * - utf-16-le
     - utf-16le
     - No
   * - utf-32
     - utf32
     - No
   * - utf-32-be
     - utf-32be
     - No
   * - utf-32-le
     - utf-32le
     - No
   * - utf-8
     - utf8
     - No
   * - utf-8-sig
     - utf-8-bom
     - No
   * - windows-1250
     - cp1250
     - No
   * - windows-1251
     - cp1251
     - No
   * - windows-1252
     - cp1252
     - No
   * - windows-1253
     - cp1253
     - No
   * - windows-1254
     - cp1254
     - No
   * - windows-1255
     - cp1255
     - No
   * - windows-1256
     - cp1256
     - No
   * - windows-1257
     - cp1257
     - No
   * - windows-1258
     - cp1258
     - No

Legacy ISO
----------

.. list-table::
   :header-rows: 1
   :widths: 25 50 15

   * - Encoding
     - Aliases
     - Multi-byte
   * - iso-8859-1
     - latin-1, latin1, iso8859-1
     - No
   * - iso-8859-10
     - latin-6, latin6, iso8859-10
     - No
   * - iso-8859-13
     - latin-7, latin7, iso8859-13
     - No
   * - iso-8859-14
     - latin-8, latin8, iso8859-14
     - No
   * - iso-8859-15
     - latin-9, latin9, iso8859-15
     - No
   * - iso-8859-16
     - latin-10, latin10, iso8859-16
     - No
   * - iso-8859-2
     - latin-2, latin2, iso8859-2
     - No
   * - iso-8859-3
     - latin-3, latin3, iso8859-3
     - No
   * - iso-8859-4
     - latin-4, latin4, iso8859-4
     - No
   * - iso-8859-5
     - iso8859-5, cyrillic
     - No
   * - iso-8859-6
     - iso8859-6, arabic
     - No
   * - iso-8859-7
     - iso8859-7, greek
     - No
   * - iso-8859-8
     - iso8859-8, hebrew
     - No
   * - iso-8859-9
     - latin-5, latin5, iso8859-9
     - No
   * - johab
     - —
     - Yes

Legacy Mac
----------

.. list-table::
   :header-rows: 1
   :widths: 25 50 15

   * - Encoding
     - Aliases
     - Multi-byte
   * - mac-cyrillic
     - maccyrillic
     - No
   * - mac-greek
     - macgreek
     - No
   * - mac-iceland
     - maciceland
     - No
   * - mac-latin2
     - maclatin2, maccentraleurope
     - No
   * - mac-roman
     - macroman, macintosh
     - No
   * - mac-turkish
     - macturkish
     - No

Legacy Regional
---------------

.. list-table::
   :header-rows: 1
   :widths: 25 50 15

   * - Encoding
     - Aliases
     - Multi-byte
   * - cp1006
     - —
     - No
   * - cp1125
     - —
     - No
   * - cp720
     - —
     - No
   * - koi8-t
     - —
     - No
   * - kz-1048
     - kz1048, strk1048-2002, rk1048
     - No
   * - ptcp154
     - pt154, cp154
     - No

DOS
---

.. list-table::
   :header-rows: 1
   :widths: 25 50 15

   * - Encoding
     - Aliases
     - Multi-byte
   * - cp437
     - —
     - No
   * - cp737
     - —
     - No
   * - cp775
     - —
     - No
   * - cp850
     - —
     - No
   * - cp852
     - —
     - No
   * - cp855
     - —
     - No
   * - cp856
     - —
     - No
   * - cp857
     - —
     - No
   * - cp858
     - —
     - No
   * - cp860
     - —
     - No
   * - cp861
     - —
     - No
   * - cp862
     - —
     - No
   * - cp863
     - —
     - No
   * - cp864
     - —
     - No
   * - cp865
     - —
     - No
   * - cp866
     - —
     - No
   * - cp869
     - —
     - No

Mainframe (EBCDIC)
------------------

.. list-table::
   :header-rows: 1
   :widths: 25 50 15

   * - Encoding
     - Aliases
     - Multi-byte
   * - cp037
     - —
     - No
   * - cp1026
     - —
     - No
   * - cp424
     - —
     - No
   * - cp500
     - —
     - No
   * - cp875
     - —
     - No
