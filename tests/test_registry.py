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
    shift_jis = next(e for e in REGISTRY if e.name == "shift_jis")
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
    assert by_name["shift_jis"].languages == ("ja",)
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
