######################## BEGIN LICENSE BLOCK ########################
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301  USA
######################### END LICENSE BLOCK #########################

from .enums import EncodingEra

# Mapping of encoding names to their eras
ENCODING_ERA_MAP = {
    # Unicode encodings - part of modern web but most preferred
    "UTF-8": EncodingEra.MODERN_WEB,
    "UTF-16": EncodingEra.MODERN_WEB,
    "UTF-16BE": EncodingEra.MODERN_WEB,
    "UTF-16LE": EncodingEra.MODERN_WEB,
    "UTF-32": EncodingEra.MODERN_WEB,
    "UTF-32BE": EncodingEra.MODERN_WEB,
    "UTF-32LE": EncodingEra.MODERN_WEB,
    # Modern web encodings - Windows and widely used encodings
    "WINDOWS-1250": EncodingEra.MODERN_WEB,
    "WINDOWS-1251": EncodingEra.MODERN_WEB,
    "WINDOWS-1252": EncodingEra.MODERN_WEB,
    "WINDOWS-1253": EncodingEra.MODERN_WEB,
    "WINDOWS-1254": EncodingEra.MODERN_WEB,
    "WINDOWS-1255": EncodingEra.MODERN_WEB,
    "WINDOWS-1256": EncodingEra.MODERN_WEB,
    "WINDOWS-1257": EncodingEra.MODERN_WEB,
    "WINDOWS-1258": EncodingEra.MODERN_WEB,
    "CP874": EncodingEra.MODERN_WEB,  # Thai (Windows-874)
    "TIS-620": EncodingEra.MODERN_WEB,  # Thai
    "KOI8-R": EncodingEra.MODERN_WEB,  # Russian, still used
    "KOI8-U": EncodingEra.MODERN_WEB,  # Ukrainian, still used
    # Multibyte encodings for Asian languages (modern web)
    "GB18030": EncodingEra.MODERN_WEB,  # Chinese (modern superset)
    "BIG5": EncodingEra.MODERN_WEB,  # Traditional Chinese
    "SHIFT_JIS": EncodingEra.MODERN_WEB,  # Japanese
    "EUC-JP": EncodingEra.MODERN_WEB,  # Japanese
    "EUC-KR": EncodingEra.MODERN_WEB,  # Korean
    "CP949": EncodingEra.MODERN_WEB,  # Korean (Windows)
    "ISO-2022-JP": EncodingEra.MODERN_WEB,  # Japanese (email)
    "ISO-2022-KR": EncodingEra.MODERN_WEB,  # Korean (email)
    # Legacy ISO encodings
    "ISO-8859-1": EncodingEra.LEGACY_ISO,
    "ISO-8859-2": EncodingEra.LEGACY_ISO,
    "ISO-8859-3": EncodingEra.LEGACY_ISO,
    "ISO-8859-4": EncodingEra.LEGACY_ISO,
    "ISO-8859-5": EncodingEra.LEGACY_ISO,
    "ISO-8859-6": EncodingEra.LEGACY_ISO,
    "ISO-8859-7": EncodingEra.LEGACY_ISO,
    "ISO-8859-8": EncodingEra.LEGACY_ISO,
    "ISO-8859-9": EncodingEra.LEGACY_ISO,
    "ISO-8859-10": EncodingEra.LEGACY_ISO,
    "ISO-8859-11": EncodingEra.LEGACY_ISO,
    "ISO-8859-13": EncodingEra.LEGACY_ISO,
    "ISO-8859-14": EncodingEra.LEGACY_ISO,
    "ISO-8859-15": EncodingEra.LEGACY_ISO,
    "ISO-8859-16": EncodingEra.LEGACY_ISO,
    # Legacy Mac encodings
    "MACCYRILLIC": EncodingEra.LEGACY_MAC,
    "MACGREEK": EncodingEra.LEGACY_MAC,
    "MACICELAND": EncodingEra.LEGACY_MAC,
    "MACLATIN2": EncodingEra.LEGACY_MAC,
    "MACROMAN": EncodingEra.LEGACY_MAC,
    "MACTURKISH": EncodingEra.LEGACY_MAC,
    "KOI8-T": EncodingEra.LEGACY_MAC,  # Tajik
    "KZ1048": EncodingEra.LEGACY_MAC,  # Kazakh
    "PTCP154": EncodingEra.LEGACY_MAC,  # Cyrillic Asian
    "CP1125": EncodingEra.LEGACY_MAC,  # Ukrainian
    "CP720": EncodingEra.LEGACY_MAC,  # Arabic
    # Legacy multibyte encodings
    "GB2312": EncodingEra.LEGACY_ISO,  # Chinese (subset of GB18030)
    "JOHAB": EncodingEra.LEGACY_ISO,  # Korean
    "CP932": EncodingEra.LEGACY_ISO,  # Japanese (Windows)
    # DOS-era codepages
    "CP437": EncodingEra.DOS,  # US
    "CP737": EncodingEra.DOS,  # Greek
    "CP775": EncodingEra.DOS,  # Baltic
    "CP850": EncodingEra.DOS,  # Western European
    "CP852": EncodingEra.DOS,  # Central European
    "CP855": EncodingEra.DOS,  # Cyrillic
    "CP856": EncodingEra.DOS,  # Hebrew
    "CP857": EncodingEra.DOS,  # Turkish
    "CP858": EncodingEra.DOS,  # Western European with Euro
    "CP860": EncodingEra.DOS,  # Portuguese
    "CP861": EncodingEra.DOS,  # Icelandic
    "CP862": EncodingEra.DOS,  # Hebrew
    "CP863": EncodingEra.DOS,  # French Canadian
    "CP864": EncodingEra.DOS,  # Arabic
    "CP865": EncodingEra.DOS,  # Nordic
    "CP866": EncodingEra.DOS,  # Cyrillic
    "CP869": EncodingEra.DOS,  # Greek
    # EBCDIC/IBM mainframe codepages
    "CP037": EncodingEra.MAINFRAME,  # EBCDIC US/Canada
    "CP424": EncodingEra.MAINFRAME,  # EBCDIC Hebrew
    "CP500": EncodingEra.MAINFRAME,  # EBCDIC Latin-1
    "CP875": EncodingEra.MAINFRAME,  # EBCDIC Greek
    "CP1026": EncodingEra.MAINFRAME,  # EBCDIC Turkish
}


def get_encoding_era(encoding_name: str) -> EncodingEra:
    """
    Get the era for a given encoding name.

    :param encoding_name: The encoding name to look up
    :return: The EncodingEra for this encoding, defaults to MODERN_WEB if unknown
    """
    normalized_name = encoding_name.upper().replace("_", "-")
    return ENCODING_ERA_MAP.get(normalized_name, EncodingEra.MODERN_WEB)


def is_unicode_encoding(encoding_name: str) -> bool:
    """
    Check if an encoding is a Unicode encoding (UTF-8, UTF-16, UTF-32).

    :param encoding_name: The encoding name to check
    :return: True if the encoding is Unicode, False otherwise
    """
    normalized_name = encoding_name.upper().replace("_", "-")
    return normalized_name.startswith("UTF-")
