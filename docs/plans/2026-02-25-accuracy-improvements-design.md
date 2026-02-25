# Accuracy Improvements Design

**Date:** 2026-02-25
**Goal:** Match or exceed charset-normalizer's accuracy on the chardet test suite; never return None for non-binary text input.

## Baseline

With strict directional equivalence classes:

| Library              | Accuracy          |
| -------------------- | ----------------- |
| chardet-rewrite      | 74.6% (1613/2161) |
| charset-normalizer   | 76.0% (1642/2161) |

Gap: 1.4 percentage points (~30 files).

chardet-rewrite beats charset-normalizer on 27 encodings (Scandinavian, Celtic, Baltic, East Asian escape-sequences). charset-normalizer beats chardet-rewrite on 24 encodings (common Windows codepages, Cyrillic, EBCDIC, Central European).

## Root Causes

### 1. CJK catch-all encodings (~35-40 failures)

gb18030, cp932 (Shift_JIS superset), and big5 accept nearly any byte sequence as structurally valid. They win as false positives for:

- EBCDIC (cp037 → gb18030: 12+ failures)
- Korean (johab → gb18030: 5 failures)
- Baltic/regional (cp775, windows-1257, iso-8859-4 → gb18030)
- Japanese (euc-jp → big5: 5 failures)
- DOS code pages (cp437 → cp932: 7 failures)

### 2. Mac encodings competing with ISO/Windows (~20-30 failures)

Mac encodings compete equally with modern encodings despite being far less common:

- mac-latin2 steals from iso-8859-2/windows-1250: 26 failures
- mac-turkish steals from mac-roman and iso-8859-9

### 3. Weak or missing models (~15-20 failures)

- johab (Korean): 0% accuracy, no model at all
- koi8-r: 69% accuracy, all 8 failures are koi8-u (only 8 byte positions differ)
- cp866: 59% accuracy, 12 failures to cp1125
- iso-8859-1/windows-1252: ~7-8% accuracy, scattered across many wrong answers

### 4. None results for ambiguous text (7 failures + short input gaps)

The detector returns None for short or ambiguous text where a best-guess answer would be more useful.

## Changes

### 1. Fix test framework — directional equivalence classes

Replace the current bidirectional equivalence groups with directional superset relationships. Detecting a superset encoding is acceptable (e.g., detecting UTF-8 when the file is ASCII); detecting a subset is not (e.g., detecting ASCII when the file is UTF-8).

**Superset relationships** (detecting the right-hand side when the left-hand side is expected = correct):

| Expected     | Acceptable Supersets         |
| ------------ | ---------------------------- |
| ascii        | utf-8                        |
| tis-620      | iso-8859-11, cp874           |
| iso-8859-11  | cp874                        |
| gb2312       | gb18030                      |
| shift_jis    | cp932                        |
| euc-kr       | cp949                        |

**Bidirectional equivalents** (same character repertoire, byte-order only):

- utf-16, utf-16-le, utf-16-be
- utf-32, utf-32-le, utf-32-be

Add per-encoding accuracy reporting to the diagnostic scripts for development use. The pytest gate remains on overall accuracy.

### 2. CJK gating — require multi-byte structural evidence

After Stage 2a (byte validity filtering), before Stage 3 (statistical scoring), add a CJK evidence check for gb18030, cp932, big5, euc-jp, and euc-kr:

- Use the existing structural probing logic from Stage 2b to check for actual multi-byte sequences.
- Require at least ~5% of bytes to participate in valid multi-byte sequences.
- If a file is purely single-byte data that happens to pass CJK validity rules, eliminate the CJK candidate.

This leverages existing code — the structural probing functions already compute multi-byte ratios. The change makes this a gate rather than just a scoring signal.

**Expected impact:** ~35-40 failures fixed.
**Risk:** Could break CJK detection for files with very little multi-byte content. The 5% threshold is low enough that real CJK text (which typically has 30-60% multi-byte content) passes easily.

### 3. Era-based tiebreaking

When statistical scores are close (within a configurable margin, e.g., top candidates within 10% of each other), prefer encodings from the requested `encoding_era`:

- After Stage 3 scoring, examine the top candidates.
- If the top candidate is not in the requested era but another candidate is, and their scores are within the tiebreak margin, prefer the in-era candidate.
- Era preference order for MODERN_WEB: MODERN_WEB > LEGACY_ISO > LEGACY_REGIONAL > DOS > LEGACY_MAC > MAINFRAME.

This only activates when scores are genuinely close. A Mac encoding with a clearly better score still wins.

**Expected impact:** ~20-30 failures fixed, especially mac-latin2 → iso-8859-2 corrections.

### 4. Training and model improvements

**4a. Train johab model:** Add johab to the training script's language→encoding mapping. Train on Korean text from CulturaX. Johab uses a unique byte structure that should produce a distinctive bigram model.

**4b. Improve Cyrillic discrimination:** koi8-r and koi8-u differ in 8 byte positions (Ukrainian-specific letters Ґ, Є, І, Ї). Train koi8-r specifically on Russian-only text (no Ukrainian) and koi8-u on Ukrainian text. The distinguishing bytes will then appear in koi8-u's model but not koi8-r's.

**4c. Improve Western European models:** Increase training data diversity for iso-8859-1/windows-1252. Ensure training text heavily exercises the 0xA0-0xFF range (French accents, German umlauts, Scandinavian characters). This is inherently the hardest discrimination problem — many Latin single-byte encodings are very similar — but some improvement is expected.

**4d. Improve EBCDIC discrimination:** The CJK gate (change 2) fixes gb18030 false positives. For cp037↔cp500 confusion (they differ in bracket/brace byte positions): train on text that specifically exercises the differing characters.

### 5. Fallback behavior for non-binary text

**Binary files** (Stage 0 detects >1% control bytes):
```python
{'encoding': None, 'confidence': 0.95, 'language': None}
```
High confidence signals "we're confident this is binary."

**Empty input** (`b""`):
```python
{'encoding': 'windows-1252', 'confidence': 0.10, 'language': None}
```
Empty bytes decode as empty string under any encoding. windows-1252 is the web's de facto default.

**Non-binary text with no confident encoding result:**
```python
{'encoding': 'windows-1252', 'confidence': 0.10, 'language': None}
```
The low confidence (0.10) signals "this is a guess based on common web practice."

Implementation: at the end of the orchestrator pipeline, if the result is None and the data passed the binary check, substitute the windows-1252 fallback.

### 6. Per-encoding accuracy tracking

Update the diagnostic scripts (`scripts/diagnose_accuracy.py`, `scripts/compare_strict.py`) to use the directional equivalence classes. Keep these as development tools for tracking per-encoding regressions and improvements during iteration.

## Non-Goals

- **Speed optimization:** not addressed in this design. Changes should not make speed significantly worse, but speed improvements are a separate effort.
- **Non-MODERN_WEB eras:** MODERN_WEB is the focus. DOS, EBCDIC, and Mac improvements are incidental to the changes above.
- **New pipeline stages (trigram, Unicode character analysis):** not needed to close the gap with charset-normalizer. May revisit if the above changes prove insufficient.

## Success Criteria

- Overall accuracy exceeds charset-normalizer (>76.0%) under strict directional equivalence classes.
- No None results for non-binary, non-empty text input.
- No accuracy regressions on currently-correct encodings (verified via per-encoding tracking).
- All existing tests pass.
