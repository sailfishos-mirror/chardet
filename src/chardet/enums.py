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


# Priority order for tiebreaking: lower number = higher priority.
ERA_PRIORITY: dict[EncodingEra, int] = {
    EncodingEra.MODERN_WEB: 0,
    EncodingEra.LEGACY_ISO: 1,
    EncodingEra.LEGACY_REGIONAL: 2,
    EncodingEra.DOS: 3,
    EncodingEra.LEGACY_MAC: 4,
    EncodingEra.MAINFRAME: 5,
}
