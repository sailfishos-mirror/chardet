# Test Coverage Gap Analysis and Improvement Design

**Date:** 2026-03-03
**Status:** Approved
**Baseline:** 93.5% (87 lines uncovered across 1344 statements)
**Target:** 97-98%

## Approach

1. Remove dead code branches (don't inflate coverage artificially)
2. Add tests for all reachable uncovered paths
3. Create `scripts/tests/` for script utility tests
4. Add `# pragma: no cover` only for intentional invariant assertions

## Dead Code to Remove

| Location | Code | Reason |
|----------|------|--------|
| `escape.py:72` | `last_val < 0` guard in `_is_valid_utf7_b64` | Caller only passes bytes from `_UTF7_BASE64`; `_B64_DECODE` covers all of them |
| `confusion.py:332` | Final `return results` in `resolve_confusion_groups` | `winner` can only be `enc_a`, `enc_b`, or `None` — all handled by earlier branches |
| `models/__init__.py:117` | `else` branch (plain key) in `get_enc_index` | Training always writes `lang/enc` keys; backward-compat shim for a format that no longer exists |

## Intentional Invariant Assertions (pragma: no cover)

| Location | Code | Reason |
|----------|------|--------|
| `orchestrator.py:593-594` | `if not results: raise RuntimeError` | `_fill_language` never drops items; kept as safety-net assertion |

## Tests to Add

### 1. `test_utf8.py` — 3 new tests
- Overlong 3-byte sequence (`\xE0\x80\x80`) → line 69
- Overlong 4-byte sequence (`\xF0\x80\x80\x80`) → line 76
- Above-Unicode-max (`\xF4\x90\x80\x80`) → line 79

### 2. `test_equivalences.py` — 2 new tests
- `is_correct(None, None)` returns True, `is_correct(None, "utf-8")` returns False → line 158
- `is_equivalent_detection(data, None, None/encoding)` → line 235

### 3. `test_cli.py` — 3 new tests
- `python -m chardet` subprocess entry point → `__main__.py` lines 3-6
- Detection failure on file (monkeypatch `chardet.detect` to raise) → cli.py lines 64-67
- Detection failure on stdin (monkeypatch) → cli.py lines 72-78

### 4. `test_escape.py` — 2 new tests
- HZ with `~}` appearing before `~{` → line 30
- UTF-7 with fewer than 3 base64 chars (`+AB-`) → line 64

### 5. `test_confusion.py` — 4 new tests
- Empty `confusion.bin` emits RuntimeWarning → lines 125-132
- Corrupt `confusion.bin` raises ValueError → lines 135-137
- `resolve_confusion_groups` with <2 results returns unchanged → line 312
- `resolve_by_bigram_rescore` with empty freq returns None → line 238

### 6. `test_models.py` — 6 new tests
- Empty `models.bin` emits RuntimeWarning → lines 55-62
- Corrupt models: num_encodings > 10000 → lines 70-71
- Corrupt models: name_len > 256 → lines 77-78
- Corrupt models: num_entries > 65536 → lines 84-85
- Corrupt models: truncated mid-model → lines 93-95
- `score_with_profile` fallback norm + all-zeros model → lines 243-250

### 7. `test_orchestrator.py` — 4 new tests
- `_to_utf8` with unknown encoding returns None → lines 411-412
- `_to_utf8` with UTF-8 passthrough → line 405-406
- `_demote_niche_latin` for iso-8859-14 → partially covers orchestrator demotion logic
- `_demote_niche_latin` for windows-1254 → same

### 8. `test_structural.py` — 5 new tests
- `_analyze_euc_jp` SS2 with invalid trail byte → line 97
- `_analyze_euc_jp` SS3 path (3-byte JIS X 0212) → lines 100-111
- `compute_multibyte_byte_coverage` with all-ASCII input → line 376
- `compute_lead_byte_diversity` with empty data → line 396
- Coverage/diversity for escape-protocol encoding hitting no-analyzer fallback → lines 362, 366, 399

### 9. `test_utf1632.py` — 5 new tests
- UTF-32 BE decode error (invalid code point) → lines 97-98
- UTF-32 LE decode error → lines 114-115
- UTF-16 single-candidate decode error → lines 171-172
- Both-candidates low text quality → line 232
- `_looks_like_text("")` → line 257

### 10. `test_pipeline_types.py` — 1 new test
- `PipelineContext.mb_coverage` field exists and works → covers the field

### 11. `scripts/tests/test_utils.py` — new file
- `get_data_dir()` returns correct path
- `collect_test_files()` returns expected structure
- `normalize_language()` handles expected inputs

## Summary

- **Dead code removed:** 3 branches (~5 statements)
- **New tests:** ~38 tests across 11 files
- **Pragmas added:** 1 (invariant assertion)
- **New test directory:** `scripts/tests/`
- **Expected final coverage:** 97-98%
