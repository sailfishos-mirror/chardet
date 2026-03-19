# Char-Dataset Accuracy Benchmark Design

**Date:** 2026-03-19
**Status:** Draft
**Goal:** Reproduce, verify, and fairly compare chardet vs charset-normalizer accuracy on the charset-normalizer test dataset (char-dataset), then identify genuine detection failures to guide pipeline improvements.

## Background

charset-normalizer's README claims chardet achieves 89% accuracy vs their 97% on
their test dataset ([Ousret/char-dataset](https://github.com/Ousret/char-dataset)).
Investigation revealed several methodological asymmetries:

1. **charset-normalizer tests itself with multi-candidate scoring** — their
   `coverage.py` uses `from_path()` and checks if the expected encoding appears
   anywhere in `result.could_be_from_charset`, not just the best guess.
2. **No encoding equivalences applied to chardet** — detecting `windows-1252` for
   an `iso8859_1`-labeled file counts as a failure, even though CP1252 is a strict
   superset of ISO-8859-1.
3. **No CI job generates the 89% number** — despite claiming "see GHA workflows",
   no workflow step measures chardet accuracy against ground truth. The number
   appears to be manually computed or from an unchecked-in script.
4. **Encoding name normalization differences** — char-dataset uses Python codec
   names as directory names (`iso8859_1`, `utf_8`), while chardet returns
   display-cased IANA names (`ISO-8859-1`, `UTF-8`). Without proper normalization,
   string comparison produces false failures.

## Approach

A new standalone script `scripts/benchmark_char_dataset.py` that runs both
libraries against the char-dataset with four scoring tiers, producing transparent
and reproducible results.

## Data Acquisition

- Clone `Ousret/char-dataset` into `.char-dataset/` at project root.
- Add `.char-dataset/` and `.char-dataset-results/` to `.gitignore`.
- Same pattern as test-data cloning: check if directory exists, pull if stale.
- Directory structure: `char-dataset/<encoding>/*.*` where `<encoding>` is a Python
  codec name (`iso8859_1`, `utf_8`, `windows_1252`, etc.).
- Expected encoding extracted from parent directory name: skip `None` directory
  (binary), then normalize via `codecs.lookup(dirname).name` to get Python's
  canonical codec form. `LookupError` on unknown names is a hard error (dataset
  structure has changed).
- A new `collect_char_dataset_files()` function is needed — the existing
  `collect_test_files()` assumes `{encoding}-{lang}` directory naming and cannot
  be reused.
- 48 encoding directories, 400+ files total.

## Scoring Methodology

Four tiers, reported separately to show how methodology choice affects results:

### Tier 1 — Strict Single-Best

`detect()` result must exactly match expected encoding after normalizing both
through `codecs.lookup().name`. This approximates what charset-normalizer's README
claims chardet gets 89% on.

### Tier 2 — Single-Best with Equivalences

`detect()` result is checked against chardet's existing `is_correct()` (supersets,
bidirectional groups) and `is_equivalent_detection()` (decoded output comparison).
This is how chardet's own test suite scores accuracy. Applied to both libraries
for fairness.

### Tier 3 — All-Candidates Strict

`detect_all()` / `from_bytes()` — check if expected encoding appears anywhere in
the candidate list (after normalization). This approximates how charset-normalizer
tests itself in `coverage.py`.

### Tier 4 — All-Candidates with Equivalences

Any candidate passes `is_correct()` or `is_equivalent_detection()` against the
expected encoding. Most generous tier, applied equally to both libraries.

Each library is scored at all four tiers. The report shows a 2x4 matrix so the
reader can see exactly how methodology choice affects the numbers.

### Encoding Name Normalization

All encoding names (expected from directory, detected from library) pass through
`codecs.lookup(name).name` before comparison. This collapses
`ISO-8859-1` / `iso8859_1` / `iso8859-1` / `latin-1` into a single canonical
form, eliminating false failures from naming differences.

### Equivalence Checking

Tiers 2 and 4 import `is_correct()` and `is_equivalent_detection()` from
`chardet.equivalences`. These same equivalences are applied to charset-normalizer
results for fairness (charset-normalizer has no equivalent concept, so we are
being generous to both libraries).

## Script Structure

**File:** `scripts/benchmark_char_dataset.py`

### Main Flow

1. Clone/update `Ousret/char-dataset` into `.char-dataset/` (gitignored)
2. Collect all files, extract expected encoding from parent directory via
   `codecs.lookup(dirname).name`
3. Run chardet against all files (direct import)
4. Run charset-normalizer against all files in an isolated venv (created with
   `uv`, same pattern as `compare_detectors.py`)
5. Score both at all 4 tiers
6. Print report

### Chardet Detection

Direct import. Call `chardet.detect_all()` once per file. Use `results[0]` for
single-best tiers (1-2) and the full list for all-candidates tiers (3-4). This
avoids redundant work from calling both `detect()` and `detect_all()`.

### charset-normalizer Detection

Subprocess via isolated venv created with `uv` (same isolation approach as
`compare_detectors.py`). A helper script runs
`charset_normalizer.from_bytes(data)` and serializes results as JSON:

```json
{
  "best": {"encoding": "utf-8", "confidence": 0.99},
  "candidates": [
    {"encoding": "utf-8", "confidence": 0.99},
    {"encoding": "ascii", "confidence": 0.80}
  ]
}
```

The main process reads each file's bytes locally for equivalence checking in
tiers 2 and 4 — `is_equivalent_detection()` needs the raw bytes to decode with
both encodings and compare. This is not delegated to the subprocess.

If venv creation fails (network issues, version conflicts), the script prints a
warning and continues in chardet-only mode (same as `--chardet-only`).

### None/Binary Handling

Files in the `None` directory: expected encoding is None. A detection of None is
correct. A non-None detection is a failure.

## Output Format

### Summary Table (default)

```
                          chardet 7.2.0    charset-normalizer 3.x.x
Tier 1 (strict best)         XX.X%              XX.X%
Tier 2 (best + equiv)        XX.X%              XX.X%
Tier 3 (all candidates)      XX.X%              XX.X%
Tier 4 (all + equiv)         XX.X%              XX.X%
Total files: NNN
```

### Per-Encoding Breakdown

For each encoding directory, pass/fail counts at Tier 2 (most realistic
single-best metric) for both libraries. Sorted by failure count descending.

### Failure Detail List (`--failures` flag)

For each file where chardet fails at Tier 2: file path, expected encoding,
detected encoding, confidence. Grouped by failure category:

- **Superset detection** — would pass with equivalences but directory name
  doesn't match (these are arguably correct)
- **Wrong family** — genuinely wrong encoding detected
- **None result** — no detection returned

## Caching

charset-normalizer results cached to `.char-dataset-results/` (gitignored).
Cache is a single JSON file per charset-normalizer version, keyed by per-file
SHA-256 content hash. Format follows `compare_detectors.py`'s pattern:
`{version}_{hash[:12]}.json`. chardet results are not cached (direct import,
fast enough). This avoids re-running slow subprocess calls when iterating on
report format.

## CLI Flags

| Flag | Description |
|------|-------------|
| `--no-cache` | Force re-run of charset-normalizer |
| `--json` | Machine-readable JSON output |
| `--chardet-only` | Skip charset-normalizer (no venv setup needed) |
| `--tier N` | Show results for a specific tier only (default: all) |
| `--failures` | Print detailed failure list |
| `--encoding NAME` | Filter to a single encoding directory |

## Out of Scope

- **Timing and memory measurement** — covered by existing benchmark scripts
- **Pipeline improvements** — deferred to phase 2 after analyzing the failure
  list from this script
- **Modifying chardet's test suite** — this is a benchmarking tool, not a test

## Phase 2 (Future)

After running the benchmark, analyze the failure detail list to determine:

1. How many "failures" are actually superset detections (arguably correct)
2. What the "true" gap is after applying equivalences fairly
3. Which genuine detection failures are worth fixing via pipeline changes
4. Whether any failures suggest missing encodings or model gaps

Scope of phase 2 pipeline work will be decided based on findings.
