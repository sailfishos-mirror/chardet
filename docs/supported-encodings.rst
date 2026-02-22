Supported encodings
===================

chardet supports over 70 character encodings, organized into tiers by
the ``EncodingEra`` enum. By default, ``detect()`` only considers
``MODERN_WEB`` encodings. Pass ``encoding_era=EncodingEra.ALL`` to
consider all tiers, or combine specific tiers with ``|``.

.. contents:: Encoding tiers
   :local:
   :depth: 1

MODERN_WEB
----------

Encodings widely used on the modern web. This is the default tier for
``detect()`` and ``detect_all()``.

Unicode
^^^^^^^

- ``UTF-8``
- ``UTF-8-SIG``
- ``UTF-16`` (BE and LE variants)
- ``UTF-32`` (BE and LE variants)

Multi-byte (CJK)
^^^^^^^^^^^^^^^^^

- ``Big5`` (Traditional Chinese)
- ``CP932`` (Japanese)
- ``CP949`` (Korean)
- ``EUC-JP`` (Japanese)
- ``EUC-KR`` (Korean)
- ``GB18030`` (Simplified Chinese)
- ``HZ-GB-2312`` (Simplified Chinese)
- ``ISO-2022-JP`` (Japanese)
- ``ISO-2022-KR`` (Korean)
- ``Shift-JIS`` (Japanese)

Single-byte (Windows)
^^^^^^^^^^^^^^^^^^^^^

- ``ASCII``
- ``CP874`` (Thai)
- ``KOI8-R`` (Russian, Ukrainian)
- ``KOI8-U`` (Ukrainian)
- ``TIS-620`` (Thai)
- ``Windows-1250`` (Croatian, Czech, Hungarian, Polish, Romanian, Slovak, Slovene)
- ``Windows-1251`` (Belarusian, Bulgarian, Macedonian, Russian, Serbian, Ukrainian)
- ``Windows-1252`` (Danish, Dutch, English, Finnish, French, German, Indonesian, Italian, Malay, Norwegian, Portuguese, Spanish, Swedish)
- ``Windows-1253`` (Greek)
- ``Windows-1254`` (Turkish)
- ``Windows-1255`` (Hebrew)
- ``Windows-1256`` (Arabic, Farsi)
- ``Windows-1257`` (Estonian, Latvian, Lithuanian)
- ``Windows-1258`` (Vietnamese)

LEGACY_ISO
----------

ISO 8859 family and other well-known legacy standards. Include this tier
when working with older web content or Unix-era text.

- ``ISO-8859-1`` (Danish, Dutch, English, Finnish, French, German, Icelandic, Indonesian, Italian, Malay, Norwegian, Portuguese, Spanish, Swedish)
- ``ISO-8859-2`` (Croatian, Czech, Hungarian, Polish, Romanian, Slovak, Slovene)
- ``ISO-8859-3`` (Esperanto, Maltese, Turkish)
- ``ISO-8859-4`` (Estonian, Latvian, Lithuanian)
- ``ISO-8859-5`` (Belarusian, Bulgarian, Macedonian, Russian, Serbian, Ukrainian)
- ``ISO-8859-6`` (Arabic, Farsi)
- ``ISO-8859-7`` (Greek)
- ``ISO-8859-8`` (Hebrew — visual and logical)
- ``ISO-8859-9`` (Turkish)
- ``ISO-8859-10`` (Icelandic)
- ``ISO-8859-11`` (Thai)
- ``ISO-8859-13`` (Estonian, Latvian, Lithuanian)
- ``ISO-8859-14`` (Breton, Irish, Scottish Gaelic, Welsh)
- ``ISO-8859-15`` (Danish, Dutch, Finnish, French, Italian, Norwegian, Portuguese, Spanish, Swedish)
- ``ISO-8859-16`` (Croatian, Hungarian, Polish, Romanian, Slovak, Slovene)
- ``Johab`` (Korean)

LEGACY_MAC
----------

Apple Macintosh-specific encodings.

- ``MacCyrillic`` (Belarusian, Bulgarian, Macedonian, Russian, Serbian, Ukrainian)
- ``MacGreek`` (Greek)
- ``MacIceland`` (Icelandic)
- ``MacLatin2`` (Croatian, Czech, Hungarian, Polish, Romanian, Slovak, Slovene)
- ``MacRoman`` (Danish, Dutch, English, Finnish, French, German, Icelandic, Indonesian, Italian, Malay, Norwegian, Portuguese, Spanish, Swedish)
- ``MacTurkish`` (Turkish)

LEGACY_REGIONAL
---------------

Uncommon regional and national encodings.

- ``CP720`` (Arabic)
- ``CP1006`` (Urdu)
- ``CP1125`` (Ukrainian)
- ``KOI8-T`` (Tajik)
- ``KZ1048`` (Kazakh)
- ``PTCP154`` (Kazakh)

DOS
---

DOS/OEM code pages.

- ``CP437`` (English)
- ``CP737`` (Greek)
- ``CP775`` (Estonian, Latvian, Lithuanian)
- ``CP850`` (Danish, Dutch, English, Finnish, French, German, Italian, Norwegian, Portuguese, Spanish, Swedish)
- ``CP852`` (Croatian, Czech, Hungarian, Polish, Romanian, Slovak, Slovene)
- ``CP855`` (Bulgarian, Macedonian, Russian, Serbian, Ukrainian)
- ``CP856`` (Hebrew)
- ``CP857`` (Turkish)
- ``CP858`` (Danish, Dutch, English, Finnish, French, German, Italian, Norwegian, Portuguese, Spanish, Swedish)
- ``CP860`` (Portuguese)
- ``CP861`` (Icelandic)
- ``CP862`` (Hebrew)
- ``CP863`` (French)
- ``CP864`` (Arabic)
- ``CP865`` (Danish, Norwegian)
- ``CP866`` (Belarusian, Russian, Ukrainian)
- ``CP869`` (Greek)

MAINFRAME
---------

IBM EBCDIC mainframe encodings.

- ``CP037`` (Breton, Danish, Dutch, English, Finnish, French, German, Icelandic, Indonesian, Irish, Italian, Malay, Norwegian, Portuguese, Scottish Gaelic, Spanish, Swedish, Welsh)
- ``CP424`` (Hebrew)
- ``CP500`` (Breton, Danish, Dutch, English, Finnish, French, German, Icelandic, Indonesian, Irish, Italian, Malay, Norwegian, Portuguese, Scottish Gaelic, Spanish, Swedish, Welsh)
- ``CP875`` (Greek)
- ``CP1026`` (Turkish)
