# Design: Switch Internal Canonical Names to Python Codec Names

**Date:** 2026-03-10

## Problem

Chardet uses display-cased "canonical names" internally (e.g., `"UTF-8"`,
`"Windows-1252"`, `"ISO-8859-1"`) that differ from Python's `codecs.lookup().name`
output (`"utf-8"`, `"cp1252"`, `"iso8859-1"`). This creates a confusing naming
layer: the registry stores display names, a separate `python_codec` field stores
the codec name, `_LEGACY_NAMES` maps display names to chardet 5.x names,
`PREFERRED_SUPERSET` maps to display names, and `should_rename_legacy` controls
which mapping is applied. The result is hard to reason about and has caused bugs.

## Solution

Use `codecs.lookup(name).name` as the single internal canonical name for every
encoding. Add a `compat_names` parameter (default `True`) to map codec names to
chardet 5.x/6.x display names at the public API boundary. Rename
`should_rename_legacy` to `prefer_superset` (keep old name as deprecated alias).

## Data Flow

```
pipeline (codec names)
  → prefer_superset? apply PREFERRED_SUPERSET
  → compat_names? apply _COMPAT_NAMES
  → return to caller
```

## API Parameters

`detect()`, `detect_all()`, and `UniversalDetector` gain:

| Parameter | Default | Effect |
|---|---|---|
| `compat_names` | `True` | Map codec names to chardet 5.x/6.x display names |
| `prefer_superset` | `False` | Remap subsets to supersets (ISO-8859-1 → cp1252) |
| `should_rename_legacy` | `False` | Deprecated alias for `prefer_superset` |

Example outputs for ISO-8859-1 data:

| prefer_superset | compat_names | Result |
|---|---|---|
| False | True (default) | `"ISO-8859-1"` |
| False | False | `"iso8859-1"` |
| True | True | `"Windows-1252"` |
| True | False | `"cp1252"` |

`should_rename_legacy` emits `DeprecationWarning` when used. If both
`should_rename_legacy` and `prefer_superset` are passed and conflict,
`prefer_superset` wins.

## Internal Changes

### registry.py

- `EncodingName` type literal uses codec names (`"utf-8"`, `"cp1252"`, etc.)
- `EncodingInfo.name` is the codec name
- `EncodingInfo.python_codec` field removed (redundant with `name`)
- `REGISTRY` keyed by codec names
- `lookup_encoding()` returns codec names
- Old display-cased names kept as aliases for backward-compat lookups

### Pipeline Modules

All `DetectionResult.encoding` values use codec names:

- `escape.py`: `"iso2022_jp_2004"` instead of `"ISO-2022-JP-2004"`
- `bom.py`: `"utf-8-sig"` instead of `"UTF-8-SIG"`
- All other pipeline modules follow suit

### equivalences.py

- `SUPERSETS`, `BIDIRECTIONAL_GROUPS`, `PREFERRED_SUPERSET` use codec names
- `_LEGACY_NAMES` replaced by `_COMPAT_NAMES`: maps codec name → 5.x display name
- `apply_compat_names()` does `_COMPAT_NAMES.get(name, name)` lookup
- `apply_legacy_rename()` replaced by `apply_preferred_superset()`
- `normalize_encoding_name()` unchanged

### _COMPAT_NAMES

Only contains entries where codec name differs from chardet 5.x output:

```python
_COMPAT_NAMES = {
    "big5hkscs": "Big5",
    "cp855": "IBM855",
    "cp866": "IBM866",
    "euc_jis_2004": "EUC-JP",
    "iso2022_jp_2": "ISO-2022-JP",
    "mac-cyrillic": "MacCyrillic",
    "mac-roman": "MacRoman",
    "shift_jis_2004": "SHIFT_JIS",
    "cp1250": "Windows-1250",
    # ... all Windows-125x, ISO-8859-x, etc.
}
```

Encodings new to v7 (DOS codepages, EBCDIC, etc.) have no entry — codec name
passes through unchanged. Encodings where 5.x already returned the codec name
(e.g., `"ascii"`, `"utf-8"`, `"koi8-r"`) need no entry.

### Models

- Model keys change from `"French/Windows-1252"` to `"fr/cp1252"` (ISO 639-1
  language codes + codec names)
- Requires retraining to regenerate `models.bin`

### PREFERRED_SUPERSET

Uses codec names as keys and values:

```python
PREFERRED_SUPERSET = {
    "ascii": "cp1252",
    "euc_kr": "cp949",
    "iso8859-1": "cp1252",
    "iso8859-2": "cp1250",
    # ...
}
```

## Test Data

Test data directories in the external `chardet/test-data` repo are not renamed.
`collect_test_files()` normalizes parsed directory encoding names through
`codecs.lookup().name` before comparison.

## Test Updates

- `test_escape.py` and other pipeline-level tests: update assertions to codec
  names (they call internal APIs directly)
- `test_api.py`, `test_accuracy.py`: go through public API, assertions depend
  on `compat_names` setting
- Fix failing `test_enc_index_alias_resolution`

## Deprecation

- `should_rename_legacy`: kept working, emits `DeprecationWarning`, documented
  as replaced by `prefer_superset`
- Default output of `detect()` unchanged from 7.0.x (`compat_names=True`)
- `EncodingInfo.python_codec` removed (was internal)

## What Gets Removed

- `EncodingInfo.python_codec` field
- `_LEGACY_NAMES` dict (replaced by `_COMPAT_NAMES`)
- `apply_legacy_rename()` function (replaced by `apply_preferred_superset()`)
