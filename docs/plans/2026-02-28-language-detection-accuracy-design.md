# Language Detection Accuracy Tracking

## Goal

Add language detection accuracy as a parallel, non-blocking metric alongside
encoding detection accuracy. Language accuracy is diagnostic — it helps
identify weak spots and guide model training — but never gates CI or counts
against encoding accuracy.

## Approach: Detected-language passthrough

Extend the existing subprocess JSON protocol with one field
(`detected_language`), then track language accuracy as a parallel metric in
`compare_detectors.py` and emit warnings in `test_accuracy.py`.

## Changes by file

### 1. `scripts/benchmark_time.py`

Change `detect()` closures from `() -> str | None` to
`() -> tuple[str | None, str | None]` returning `(encoding, language)`:

- **chardet** (both era and no-era branches): return
  `(result["encoding"], result["language"])`
- **cchardet**: return `(result["encoding"], None)` — cchardet doesn't
  return language reliably
- **charset-normalizer**: return `(best.encoding, None)` — no language field

Add `"detected_language"` to JSON output alongside `"detected"`. Human-readable
output unchanged.

`benchmark_memory.py` is **not changed** — it doesn't output per-file results.

### 2. `scripts/compare_detectors.py`

**Subprocess parsing:** `_run_timing_subprocess` return tuple grows from
`(expected_enc, expected_lang, path, detected_enc)` to include
`detected_language` as a 5th element.

**Stats tracking:** Extend per-detector stats dict:
- `lang_correct`, `lang_total` (overall counters)
- `per_enc[encoding]["lang_correct"]`, `per_enc[encoding]["lang_total"]`
- `lang_failures` list

**`_record_result`:** Add `expected_language` and `detected_language`
parameters. Language comparison is **case-insensitive exact match**.
`detected_language=None` counts as incorrect. Language tracking is fully
independent of encoding tracking.

**Report additions:**
1. **Overall accuracy** — add a language accuracy line below encoding accuracy
   per detector
2. **Per-encoding language table** — new `PER-ENCODING LANGUAGE ACCURACY`
   table (separate from encoding table, same structure)
3. **Language failures** — new `LANGUAGE FAILURES` section per detector
   (capped at 80, like encoding failures)

Non-chardet detectors will show 0% language accuracy (they return `None`).

### 3. `tests/test_accuracy.py`

After the encoding assertion, call `warnings.warn()` when detected language
doesn't match expected language (case-insensitive). The warning message
includes: expected language, detected language, encoding, and file path.

- Encoding test failures still fail the test (unchanged)
- Language mismatches appear in pytest warnings summary
- CI stays green regardless of language accuracy
- `pytest -W error::UserWarning` can optionally promote to failures

## What this does NOT change

- Encoding accuracy is the primary metric — unchanged
- `benchmark_memory.py` — no per-file output, no language needed
- Encoding equivalences (`equivalences.py`) — language has no equivalence system
- `diagnose_accuracy.py` — out of scope for this change
