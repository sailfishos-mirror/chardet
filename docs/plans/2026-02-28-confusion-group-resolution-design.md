# Confusion Group Resolution — Design

**Date**: 2026-02-28
**Goal**: Improve detection accuracy by systematically resolving confusion between similar single-byte encodings using auto-computed distinguishing byte maps.

## Problem

The statistical bigram model cannot reliably differentiate encodings that share >80% of their byte-to-Unicode mappings. The signal from the ~5-50 distinguishing byte positions is drowned out by the ~200+ identical positions. This causes 60-80 of the ~109 remaining test failures.

### Largest Failure Clusters

| Confusion Family | Pairwise Byte Diffs | Failures | Notes |
|------------------|---------------------|----------|-------|
| EBCDIC: cp037 ↔ cp500 | 7 bytes | ~20 | Punctuation swaps only |
| EBCDIC: cp037 ↔ cp1026 | 29 bytes | ~15 | Turkish chars in cp1026 |
| DOS: cp850 ↔ cp858 | 1 byte (0xD5) | ~46 | ı vs € at one position |
| DOS: cp437 ↔ cp865 | 3 bytes | ~5 | ¢/¥/» vs ø/Ø/¤ |
| ISO-8859-1 ↔ iso-8859-15 | 8 bytes | ~20 | €, Œ/œ, Š/š, Ž/ž, Ÿ |
| ISO-8859-1 ↔ iso-8859-14 | 31 bytes | ~6 | Celtic dot-above chars |

### Current Ad-Hoc Handling

The pipeline already has manual distinguishing-byte logic for three specific cases:
- `_demote_niche_latin()`: demotes iso-8859-10, iso-8859-14, windows-1254 when no distinguishing bytes are present
- `_promote_koi8t()`: promotes KOI8-T over KOI8-R when Tajik-specific bytes appear

These work but don't scale. The design generalizes this into a systematic framework.

## Approach: Confusion Group Resolution

### Core Concepts

**Confusion Group**: A set of single-byte encodings where >80% of byte values (0x00-0xFF) produce the same Unicode character. Members are statistically indistinguishable by bigram scoring alone.

**Distinguishing Byte Map**: For each pair within a group, the set of byte values where they decode to different Unicode characters. Auto-computed from Python's codec machinery.

**Resolution Stage**: A new post-scoring pipeline stage that re-examines the top candidates when they belong to the same confusion group, using the distinguishing bytes to break ties.

### Build-Time Computation (in `scripts/train.py`)

During model training, compute and serialize:

1. **Pairwise byte similarity** for all single-byte encodings in the registry
2. **Confusion groups** via transitive closure (>80% similarity threshold)
3. **Distinguishing byte maps** for each pair within a group
4. **Unicode category table** for each distinguishing byte position in each encoding

Data is stored in binary struct format alongside `models.bin`, estimated <5KB total.

#### Binary Format

```
Header:
  uint16: number_of_groups

Per group:
  uint8:  group_size
  Per encoding:
    uint8:  name_length
    bytes:  encoding_name (UTF-8)
  uint16: number_of_pairs
  Per pair:
    uint8:  enc1_index (within group)
    uint8:  enc2_index
    uint8:  num_distinguishing_bytes
    Per distinguishing byte:
      uint8:  byte_value
      uint8:  enc1_unicode_category (enum)
      uint8:  enc2_unicode_category (enum)
```

### Runtime Resolution (in `orchestrator.py`)

After `score_candidates()` returns ranked results, `_resolve_confusion_groups()` checks if the top 2+ candidates are in the same confusion group. If so, it applies a resolution strategy.

Three strategies to experiment with:

**Strategy 1 — Distinguishing-Bigram Re-Scoring**: Extract bigrams containing distinguishing bytes from the input. Re-score only those bigrams against each candidate's model. The encoding with the higher distinguishing-bigram score wins.

**Strategy 2 — Unicode Category Voting**: For each distinguishing byte present in the input, vote for the encoding that maps it to a "better" Unicode category. Preference: Letter (L*) > Number (N*) > Punctuation (P*) > Symbol (S*) > Other.

**Strategy 3 — Hybrid**: Run both strategies. If they agree, use the result. If they disagree, use distinguishing-bigram re-scoring.

### Pipeline Integration

```python
# In run_pipeline(), after statistical scoring:
results = score_candidates(data, tuple(valid_candidates))
results = _resolve_confusion_groups(data, results)  # NEW

# Existing ad-hoc functions kept as fallbacks during experimentation:
results = _demote_niche_latin(data, results)
results = _promote_koi8t(data, results)
```

Once the confusion group system is validated, the ad-hoc functions can be removed.

## Experimentation Plan

1. **Baseline**: Measure current accuracy with `diagnose_accuracy.py`
2. **Implement all three strategies** behind internal `confusion_strategy` parameter
3. **Diagnostic reporting**: Extend `diagnose_accuracy.py` to report per-strategy:
   - Confusion group resolutions attempted / changed / correct / incorrect
   - Net accuracy delta per strategy per group
4. **Performance**: Verify resolution stage adds <0.1ms average per detection
5. **Select best strategy** (or mix per group) and remove the flag

## Files Changed

| File | Change |
|------|--------|
| `src/chardet/pipeline/confusion.py` | **New** — data structures, loading, resolution logic |
| `src/chardet/models/__init__.py` | Load confusion group data from binary file |
| `src/chardet/pipeline/orchestrator.py` | Integrate `_resolve_confusion_groups()` into pipeline |
| `scripts/train.py` | Compute and serialize confusion groups during training |
| `scripts/diagnose_accuracy.py` | Per-strategy comparison reporting |
| `tests/test_confusion.py` | **New** — unit tests for computation and resolution |

## Success Criteria

- Fix **15+ test files** (from ~109 failures to ~94 or fewer)
- No regressions on currently-passing encodings
- Resolution stage adds <0.1ms average latency
- Confusion group data adds <10KB to model file
- Subsumes existing `_demote_niche_latin()` and `_promote_koi8t()` logic
