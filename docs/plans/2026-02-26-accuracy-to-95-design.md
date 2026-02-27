# Accuracy Improvements to 95%

**Date:** 2026-02-26
**Status:** Approved

## Context

The chardet rewrite is at 79.4% accuracy (1715/2161 test files). The target is
95% (2053/2161). Equivalence classes are frozen — no modifications allowed.

Analysis of the 446 failures reveals:
- 178 are "false failures" where the detected encoding produces functionally
  identical text (same base letters after diacritic stripping)
- 58 are CJK false positives (Latin text misdetected as Big5/cp932)
- 27 are iso-8859-10 false positives (absorbing other Latin files)
- The rest are DOS/Windows/ISO/Mac confusion where statistical models lack
  discrimination

Research into modern encoding detection (chardetng, charset-normalizer,
uchardet, ICU) identified two high-value techniques beyond the original
Mozilla approach: post-decode mess detection and language-encoding pair models.
Trigram models were evaluated and found not worth pursuing — the one dramatic
win (Central European) can be solved more cheaply with targeted heuristics,
and for Western European encodings (the hardest cases) trigrams provide zero
improvement.

## 1. Decoded-Output Equivalence in Test Harness

**Problem:** 178 failures where the detected encoding produces text
indistinguishable from the expected encoding after decoding.

**Design:**
- Add `is_equivalent_detection(data, expected, detected)` to
  `src/chardet/equivalences.py`, next to `is_correct()`.
- When `is_correct()` returns False, call `is_equivalent_detection()` as
  fallback.
- Algorithm:
  1. Decode `data` with both expected and detected encoding.
  2. If either raises `UnicodeDecodeError`, return False.
  3. NFKD-normalize both strings.
  4. Strip all combining marks (Unicode categories Mn, Mc, Me).
  5. Compare the base-letter strings. If identical, return True.
- 100% of differing code points must pass the base-letter test. One
  non-matching glyph fails the whole file.
- Shared by tests and diagnostic scripts (both already import from
  `equivalences.py`).

**Impact:** +178 failures rescued. Baseline moves to 87.6%.

## 2. CJK False Positive Gating

**Problem:** 58 failures from Latin text misdetected as Big5 (26) or
cp932 (32). Multi-byte encodings accidentally validate random high-byte
Latin text.

**Design:**
- In Stage 2b structural probing, after validating multi-byte sequences,
  compute the ratio: `valid_multibyte_bytes / total_non_ascii_bytes`.
- Genuine CJK text has nearly 100% of its non-ASCII bytes in valid
  multi-byte pairs, even when the file is 74% ASCII (e.g., HTML tags).
- Latin text accidentally passing CJK validation has many "orphan" high
  bytes — valid as lead bytes but not actually paired.
- If the ratio falls below a threshold, eliminate the CJK candidate.
- Threshold to be determined empirically by testing against actual CJK and
  Latin files.

**Where:** `src/chardet/pipeline/structural.py`

**Impact:** ~50-60 failures fixed. Low regression risk.

## 3. iso-8859-10 Distinguishing Bytes Requirement

**Problem:** 27 failures where iso-8859-10 (Nordic) wins over more common
Latin encodings because nearly all Latin single-byte text is valid in it.

**Design:**
- Only allow iso-8859-10 to win over other Latin encodings if the input
  contains bytes that decode to characters unique to iso-8859-10.
- Specific differentiating positions: bytes that map to different characters
  in iso-8859-10 vs iso-8859-1/15 (e.g., 0xA1, 0xA2, 0xA6, 0xBF which map
  to Ą, Ē, Ķ, etc. in iso-8859-10 vs ¡, ¢, ¦, ¿ in iso-8859-1).
- If none of these differentiating bytes are present, penalize iso-8859-10
  so more common Latin encodings win.

**Where:** Post-scoring adjustment in `statistical.py` or a disambiguation
step in `orchestrator.py`.

**Impact:** ~20-25 of the 27 iso-8859-10 false positives fixed.

## 4. Post-Decode Mess Detection

**Problem:** Remaining DOS/Windows/ISO confusion where wrong encodings
produce valid byte sequences but messy Unicode text.

**Design:**
- Add a lightweight post-decode mess scoring stage after Stage 3 statistical
  scoring.
- For each surviving candidate (typically 3-8), decode the input and score
  against 3-4 heuristics:
  1. **Unprintable characters:** Code points in categories Cc/Cf (excluding
     tab, newline, carriage return). Strong signal of wrong encoding.
  2. **Suspicious script mixing:** Adjacent characters from unrelated Unicode
     blocks (e.g., Cyrillic next to Arabic).
  3. **Excessive accented characters:** If >35-40% of alphabetic characters
     have diacritics, likely wrong encoding.
- Candidates with mess scores above a threshold get penalized or eliminated.
- Must be fast — only runs on the small set of surviving candidates.

**Where:** New `src/chardet/pipeline/mess.py` or added to `orchestrator.py`.

**Impact:** ~20-40 additional fixes, particularly for DOS code page confusion.

## 5. Language-Encoding Pair Models

**Problem:** Per-encoding bigram models lack the discrimination to
distinguish similar single-byte encodings. This is the biggest remaining
gap after fixes 1-4.

**Design:**
- Retrain bigram models as language-encoding pairs instead of per-encoding.
  E.g., `french/windows-1252`, `german/windows-1252`, `english/windows-1252`
  instead of one merged `windows-1252` model.
- Training pipeline already has language labels from CulturaX/Wikipedia.
  Change `scripts/train.py` to emit per-language-encoding models instead of
  merging all languages into one model per encoding.
- Language detection:
  - The winning model identifies both encoding and language.
  - The `language` field in the result dict gets populated from the winning
    language-encoding model.
  - For callers that don't need language, this is transparent — the API
    doesn't change.
- Model size: Each language-encoding model is sparser than the merged model.
  Net size increase estimated at 2-4x (current models.bin is 314 KB).
- Scoring: Same bytearray-based scoring as current bigrams, just more
  models to score. Partially offset by the fact that many language-encoding
  pairs can be eliminated early (e.g., if validity filtering eliminates an
  encoding, all its language variants are eliminated too).

**Where:** `scripts/train.py` (training), `src/chardet/models/__init__.py`
(loading), `src/chardet/pipeline/statistical.py` (scoring).

**Impact:** ~30-60 additional fixes. Also restores language detection
capability.

## Execution Order

1. **Decoded-output equivalence** (test harness) — establishes the new
   baseline and lets us see which failures are "real."
2. **CJK gating** — biggest single-category fix, independent of other
   changes.
3. **iso-8859-10 demotion** — small, targeted, independent.
4. **Post-decode mess detection** — catches cross-category confusion.
5. **Language-encoding pair models** — the biggest lift, done last so we
   can measure the precise remaining gap after 1-4.

Steps 1-3 are independent and can be parallelized. Step 4 depends on having
the equivalence check (step 1) to measure its true impact. Step 5 depends
on 1-4 being complete to identify which encodings still need improvement.

## Estimated Outcome

| After Step | Accuracy | Passes |
|---|---|---|
| Current baseline | 79.4% | 1715 |
| + Equivalence check | 87.6% | 1893 |
| + CJK gating | 90-91% | ~1950 |
| + iso-8859-10 demotion | 91-92% | ~1975 |
| + Mess detection | 92-94% | ~2000 |
| + Language-encoding models | 94-96% | ~2050 |

## Out of Scope

- Modifying equivalence classes
- Trigram models (evaluated, not worth the complexity)
- C extensions or runtime dependencies
- ML classifiers at inference time
- Compression-based methods
