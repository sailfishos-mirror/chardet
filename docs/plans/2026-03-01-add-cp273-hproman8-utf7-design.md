# Design: Add cp273, hp-roman8, and UTF-7 Support

## Goal

Add three missing encodings to close the gap with charset-normalizer: cp273 (EBCDIC German), hp-roman8 (HP legacy Western European), and UTF-7 (RFC 2152 mail-safe Unicode).

## UTF-7

UTF-7 encodes non-ASCII characters as `+<Base64>-` escape sequences. It is structurally detectable like ISO-2022-JP and HZ-GB-2312.

**Approach:** Add detection to `pipeline/escape.py`. Look for `+<Base64 chars>-` sequences (not just `+-`, which is a literal `+`). Validate that the Base64 content decodes to valid Unicode. Return a deterministic result (confidence 1.0). No registry entry or bigram model needed.

**Changes:**
- `src/chardet/pipeline/escape.py` — add UTF-7 detector after HZ-GB-2312

## cp273

cp273 is EBCDIC German/Austrian. Follows the same pattern as the five existing EBCDIC code pages.

**Approach:** Add to registry under `MAINFRAME` era. Train a German bigram model to discriminate against other EBCDIC code pages (cp037, cp500, etc.).

**Changes:**
- `src/chardet/registry.py` — add `EncodingInfo` under MAINFRAME
- `scripts/train.py` — add `"cp273": ["de"]` to `ENCODING_LANG_MAP`
- `src/chardet/models/__init__.py` — add to `_SINGLE_LANG_MAP` (German)
- `src/chardet/models/models.bin` — retrain

## hp-roman8

hp-roman8 is a single-byte Western European encoding from HP-UX. Upper half (0x80–0xFF) differs from iso-8859-1/windows-1252.

**Approach:** Add to registry under `LEGACY_REGIONAL` era. Train bigram models for Western European languages to compete with other Latin encodings.

**Changes:**
- `src/chardet/registry.py` — add `EncodingInfo` under LEGACY_REGIONAL
- `scripts/train.py` — add `"hp-roman8": _WESTERN_EUROPEAN_LANGS` to `ENCODING_LANG_MAP`
- `src/chardet/models/models.bin` — retrain

## Summary

| Encoding | Pipeline stage | Registry | Bigram model | Era |
|---|---|---|---|---|
| UTF-7 | Escape detector | No | No | N/A |
| cp273 | Statistical | Yes, `MAINFRAME` | Yes, `["de"]` | `MAINFRAME` |
| hp-roman8 | Statistical | Yes, `LEGACY_REGIONAL` | Yes, `_WESTERN_EUROPEAN_LANGS` | `LEGACY_REGIONAL` |
