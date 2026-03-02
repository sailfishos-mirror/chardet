# tests/test_registry.py
from __future__ import annotations

import pytest

from chardet.enums import EncodingEra
from chardet.registry import REGISTRY, EncodingInfo, get_candidates


def test_encoding_info_is_frozen():
    info = REGISTRY[0]
    assert isinstance(info, EncodingInfo)
    with pytest.raises(AttributeError):
        info.name = "something"  # type: ignore[misc]


def test_registry_is_tuple():
    assert isinstance(REGISTRY, tuple)


def test_registry_has_entries():
    assert len(REGISTRY) > 50


def test_registry_utf8_is_modern_web():
    utf8 = next(e for e in REGISTRY if e.name == "utf-8")
    assert EncodingEra.MODERN_WEB in utf8.era


def test_registry_iso_8859_1_is_legacy_iso():
    iso = next(e for e in REGISTRY if e.name == "iso-8859-1")
    assert EncodingEra.LEGACY_ISO in iso.era


def test_registry_cp037_is_mainframe():
    cp037 = next(e for e in REGISTRY if e.name == "cp037")
    assert EncodingEra.MAINFRAME in cp037.era


def test_registry_macroman_is_legacy_mac():
    mac = next(e for e in REGISTRY if e.name == "mac-roman")
    assert EncodingEra.LEGACY_MAC in mac.era


def test_registry_cp437_is_dos():
    cp437 = next(e for e in REGISTRY if e.name == "cp437")
    assert EncodingEra.DOS in cp437.era


def test_registry_kz1048_is_legacy_regional():
    kz = next(e for e in REGISTRY if e.name == "kz-1048")
    assert EncodingEra.LEGACY_REGIONAL in kz.era


def test_get_candidates_filters_by_era():
    modern = get_candidates(EncodingEra.MODERN_WEB)
    for enc in modern:
        assert EncodingEra.MODERN_WEB in enc.era


def test_get_candidates_all_returns_everything():
    all_candidates = get_candidates(EncodingEra.ALL)
    assert len(all_candidates) == len(REGISTRY)


def test_get_candidates_combined_eras():
    combined = get_candidates(EncodingEra.MODERN_WEB | EncodingEra.LEGACY_ISO)
    names = {e.name for e in combined}
    assert "utf-8" in names
    assert "iso-8859-1" in names


def test_multibyte_encodings_flagged():
    shift_jis = next(e for e in REGISTRY if e.name == "shift_jis_2004")
    assert shift_jis.is_multibyte is True

    iso_8859_1 = next(e for e in REGISTRY if e.name == "iso-8859-1")
    assert iso_8859_1.is_multibyte is False


def test_registry_cp273_is_mainframe():
    cp273 = next(e for e in REGISTRY if e.name == "cp273")
    assert EncodingEra.MAINFRAME in cp273.era
    assert cp273.is_multibyte is False
    assert cp273.python_codec == "cp273"


def test_registry_hp_roman8_is_legacy_regional():
    hp = next(e for e in REGISTRY if e.name == "hp-roman8")
    assert EncodingEra.LEGACY_REGIONAL in hp.era
    assert hp.is_multibyte is False
    assert hp.python_codec == "hp-roman8"


def test_python_codec_is_valid():
    import codecs

    for enc in REGISTRY:
        codec_info = codecs.lookup(enc.python_codec)
        assert codec_info is not None, f"Invalid codec: {enc.python_codec}"


def test_languages_field_exists():
    """Every EncodingInfo has a languages tuple."""
    for enc in REGISTRY:
        assert isinstance(enc.languages, tuple), f"{enc.name} missing languages"
        for lang in enc.languages:
            assert isinstance(lang, str), f"{enc.name} has non-str language: {lang}"
            assert len(lang) == 2, f"{enc.name} has non-ISO-639-1 language: {lang}"


def test_single_language_encodings():
    """Spot-check single-language encodings."""
    by_name = {e.name: e for e in REGISTRY}
    assert by_name["shift_jis_2004"].languages == ("ja",)
    assert by_name["euc-kr"].languages == ("ko",)
    assert by_name["gb18030"].languages == ("zh",)
    assert by_name["cp273"].languages == ("de",)
    assert by_name["koi8-r"].languages == ("ru",)


def test_multi_language_encodings():
    """Spot-check multi-language encodings."""
    by_name = {e.name: e for e in REGISTRY}
    assert "en" in by_name["windows-1252"].languages
    assert "fr" in by_name["windows-1252"].languages
    assert "ru" in by_name["windows-1251"].languages
    assert "bg" in by_name["windows-1251"].languages


def test_language_agnostic_encodings():
    """Unicode and ASCII encodings have empty languages tuple."""
    by_name = {e.name: e for e in REGISTRY}
    assert by_name["ascii"].languages == ()
    assert by_name["utf-8"].languages == ()
    assert by_name["utf-7"].languages == ()
    assert by_name["utf-16"].languages == ()


def test_utf7_in_registry():
    """utf-7 is in the registry as MODERN_WEB."""
    by_name = {e.name: e for e in REGISTRY}
    assert "utf-7" in by_name
    assert EncodingEra.MODERN_WEB in by_name["utf-7"].era


# === Task 1: big5 -> big5hkscs ===


def test_big5_family_uses_broadest_superset():
    """big5hkscs is the primary name; big5 is an alias."""
    entry = next(e for e in REGISTRY if e.python_codec == "big5hkscs")
    assert entry.name == "big5hkscs"
    assert "big5" in entry.aliases
    assert "big5-tw" in entry.aliases
    assert "csbig5" in entry.aliases
    assert "cp950" in entry.aliases
    assert entry.is_multibyte is True
    assert entry.languages == ("zh",)


# === Task 2: gb18030 gets gb2312/gbk aliases ===


def test_gb18030_has_subset_aliases():
    """gb18030 includes gb2312 and gbk as aliases."""
    entry = next(e for e in REGISTRY if e.name == "gb18030")
    assert "gb2312" in entry.aliases
    assert "gbk" in entry.aliases
    assert "gb-18030" in entry.aliases


# === Task 3: euc-jp -> euc-jis-2004 ===


def test_euc_jp_family_uses_broadest_superset():
    """euc-jis-2004 is the primary name; euc-jp is an alias."""
    entry = next(e for e in REGISTRY if e.python_codec == "euc_jis_2004")
    assert entry.name == "euc-jis-2004"
    assert "euc-jp" in entry.aliases
    assert "eucjp" in entry.aliases
    assert "ujis" in entry.aliases
    assert "u-jis" in entry.aliases
    assert "euc-jisx0213" in entry.aliases
    assert entry.is_multibyte is True
    assert entry.languages == ("ja",)


# === Task 4: shift_jis -> shift_jis_2004 ===


def test_shift_jis_family_uses_broadest_superset():
    """shift_jis_2004 is the primary name; shift_jis is an alias."""
    entry = next(e for e in REGISTRY if e.python_codec == "shift_jis_2004")
    assert entry.name == "shift_jis_2004"
    assert "shift_jis" in entry.aliases
    assert "sjis" in entry.aliases
    assert "shiftjis" in entry.aliases
    assert "s_jis" in entry.aliases
    assert "shift-jisx0213" in entry.aliases
    assert entry.is_multibyte is True
    assert entry.languages == ("ja",)


# === Task 5: iso-2022-jp split into 3 branches ===


def test_iso2022_jp_split_into_branches():
    """iso-2022-jp is split into jp-2, jp-2004, and jp-ext."""
    by_name = {e.name: e for e in REGISTRY}

    # iso-2022-jp should NOT be a primary name
    assert "iso-2022-jp" not in by_name

    # iso2022-jp-2 is the multinational branch and gets the old alias
    jp2 = by_name["iso2022-jp-2"]
    assert "iso-2022-jp" in jp2.aliases
    assert "csiso2022jp" in jp2.aliases
    assert "iso2022-jp-1" in jp2.aliases
    assert jp2.python_codec == "iso2022_jp_2"
    assert jp2.is_multibyte is True
    assert jp2.languages == ("ja",)

    # iso2022-jp-2004 is the modern Japanese branch
    jp2004 = by_name["iso2022-jp-2004"]
    assert "iso2022-jp-3" in jp2004.aliases
    assert jp2004.python_codec == "iso2022_jp_2004"
    assert jp2004.is_multibyte is True
    assert jp2004.languages == ("ja",)

    # iso2022-jp-ext is the katakana branch
    jpext = by_name["iso2022-jp-ext"]
    assert jpext.aliases == ()
    assert jpext.python_codec == "iso2022_jp_ext"
    assert jpext.is_multibyte is True
    assert jpext.languages == ("ja",)


# === Task 6a: cp500 -> cp1140 ===


def test_cp500_flipped_to_cp1140():
    """cp1140 is the primary name; cp500 is an alias."""
    by_name = {e.name: e for e in REGISTRY}
    assert "cp1140" in by_name
    entry = by_name["cp1140"]
    assert "cp500" in entry.aliases
    assert entry.python_codec == "cp1140"
    assert EncodingEra.MAINFRAME in entry.era


# === Task 6b: tis-620 gets iso-8859-11 alias ===


def test_tis620_has_iso8859_11_alias():
    """tis-620 includes iso-8859-11 as an alias."""
    entry = next(e for e in REGISTRY if e.name == "tis-620")
    assert "iso-8859-11" in entry.aliases
    assert "tis620" in entry.aliases
