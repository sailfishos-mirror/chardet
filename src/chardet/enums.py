"""Enumerations for chardet."""

import enum


class EncodingEra(enum.IntFlag):
    """Bit flags representing encoding eras for filtering detection candidates."""

    MODERN_WEB = 1
    LEGACY_ISO = 2
    LEGACY_MAC = 4
    LEGACY_REGIONAL = 8
    DOS = 16
    MAINFRAME = 32
    ALL = MODERN_WEB | LEGACY_ISO | LEGACY_MAC | LEGACY_REGIONAL | DOS | MAINFRAME
