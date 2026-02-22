# Documentation Update for chardet 6.0.0

## Context

The ReadTheDocs documentation is stale relative to the 6.0.0 release. Removed modules are still referenced, new APIs are undocumented, and encoding lists are incomplete.

## Files to Update

### 1. `docs/supported-encodings.rst`
- Restructure from flat alphabetical list to grouped-by-`EncodingEra` sections
- Headers: MODERN_WEB, LEGACY_ISO, LEGACY_MAC, LEGACY_REGIONAL, DOS, MAINFRAME
- Each encoding lists supported languages
- Add missing encodings (CP869, CP1006, CP1125, ISO-8859-10, ISO-8859-14, ISO-8859-16, etc.)
- Fix KOI8-T language (Turkish → Tajik)

### 2. `docs/usage.rst`
- Update `detect()` example result to include `'language'` key
- Add section on `encoding_era` parameter with examples
- Add section on `detect_all()` function
- Add `encoding_era` parameter to `UniversalDetector` incremental example
- Add CLI section for `chardetect` with `--encoding-era` flag
- Replace yahoo.co.jp URL with a working alternative

### 3. `docs/how-it-works.rst` — Full rewrite
- Document the 6.0 detection pipeline:
  1. BOM detection (UTF-8-SIG, UTF-16/32 with BOM)
  2. UTF1632Prober — UTF-16/32 without BOM
  3. EscCharSetProber — escape-sequence encodings
  4. MBCSGroupProber — multi-byte encodings (UTF-8, GB18030, Big5, EUC-*, Shift-JIS, CP949, Johab)
  5. SBCSGroupProber — unified bigram language models for all single-byte encodings
  6. EncodingEra filtering and tie-breaking
- Remove: Latin1Prober section, windows-1252 fallback, GB2312 references

### 4. `docs/api/chardet.rst`
- Remove deleted modules: `compat`, `latin1prober`, `gb2312prober`, old lang models
- Add new modules: `gb18030prober`, `johabprober`, `utf1632prober`, `enums`, `resultdict`, `codingstatemachinedict`
- Add `metadata` subpackage: `charsets`, `languages`
- Add all current `lang*model.py` files

### 5. `docs/faq.rst`
- Update "who wrote this" to mention 6.0 rewrite with CulturaX-based models
- Minimal other changes

### 6. `README.rst`
- Replace Travis CI / Coveralls badges with GitHub Actions
- Update encoding list to match supported-encodings.rst
- Verify Python version requirement

### 7. `docs/conf.py`
- Fix deprecated `master_doc` → `root_doc`
- Clean up theme path pattern

## Decisions
- Encodings grouped by EncodingEra tier (not flat alphabetical)
- Keep URL-based examples in usage.rst
- Full rewrite of how-it-works.rst (not targeted patches)
- All 7 files in scope
