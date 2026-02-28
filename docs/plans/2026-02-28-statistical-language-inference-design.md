# Statistical Language Inference for Multi-Language Encodings

## Problem

`_fill_language` currently only fills language for single-language encodings
via a hardcoded map (41 entries). Multi-language encodings (windows-1251,
iso-8859-5, cp037, etc.) detected via early pipeline stages (markup charset,
BOM, escape) return `language=None` because those stages identify encoding
structurally rather than statistically. This accounts for ~165 files.

## Approach

Extend `_fill_language` with a second tier: when `infer_language()` returns
None but the encoding has model variants in the bigram index, use
`score_best_language()` to determine language statistically.

Build the `BigramProfile` lazily (at most once) and reuse it across all
results in the list.

### Three-tier resolution in `_fill_language`

1. **Single-language encoding** — `infer_language()` (instant, hardcoded map)
2. **Multi-language encoding with model variants** — lazy `BigramProfile` +
   `score_best_language(data, encoding, profile=profile)`
3. **No model variants** (UTF-8/16/32, ASCII) — leave `language=None`

## Files Changed

- `src/chardet/pipeline/orchestrator.py` — pass `data` to `_fill_language`,
  add lazy BigramProfile construction and `score_best_language` fallback

## Performance

- One `BigramProfile(data)` construction (~200KB scan) only for files hitting
  early-exit paths with multi-language encodings
- No impact on files already handled by single-language inference or
  statistical scoring
- Expected to be negligible since the same work happens in the statistical
  scorer for files that reach that stage

## Scope

UTF-8/16/32 language detection is out of scope — those encodings have no
bigram model variants. A different approach (e.g. Unicode-level language
models) would be needed and is a separate project.
