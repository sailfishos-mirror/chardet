# UTF-8 Language Models with Universal Fallback

## Problem

1,087 files return `language=None` — primarily UTF-8 (160), UTF-16/32
variants (861), and a handful of legacy encodings whose names don't match
the model index (cp855, cp866, maccyrillic). The existing bigram models
only cover legacy encodings, so there's nothing to score against for
Unicode encodings.

## Approach: UTF-8 Byte Bigram Models

UTF-8's variable-length encoding naturally maps different Unicode ranges to
different byte prefixes: Japanese clusters around `0xe3xx`, Russian around
`0xd0xx`, French around `0xc3xx`, Chinese around `0xe4xx/0xe7xx`. This
makes UTF-8 byte bigrams highly discriminative for language identification
with zero changes to the scoring infrastructure.

### Training (`scripts/train.py`)

Add `"utf-8": [all 48 languages]` to `ENCODING_LANG_MAP`. The existing
pipeline downloads CulturaX text, encodes to UTF-8, computes byte bigrams,
normalizes, prunes, and serializes. No other training changes needed.

Produces 48 new models: `ar/utf-8`, `fr/utf-8`, `ja/utf-8`, etc.

### Scoring (`src/chardet/pipeline/orchestrator.py`)

Add Tier 3 to `_fill_language`:

1. **Tier 1** (existing): single-language encoding via hardcoded map
2. **Tier 2** (existing): multi-language encoding via `score_best_language`
3. **Tier 3** (new): decode data to str, re-encode as UTF-8, score against
   UTF-8 language models

Tier 3 fires for any result still at `language=None` with a non-None
encoding. Logic:

- Short-circuit for UTF-8: use raw `data` directly (already UTF-8 bytes)
- Other encodings: `data.decode(encoding, errors="ignore").encode("utf-8")`
- Build a `BigramProfile` lazily (once per call, separate from tier 2)
- `score_best_language(utf8_data, "utf-8", profile=utf8_profile)`

### Model file impact

- models.bin: 716KB -> ~860KB (+144KB for 48 UTF-8 models)
- In-memory: +3MB for 48 cached bytearrays (lazy loaded on first detect)
- Scoring: one BigramProfile construction + 48 model variant scores

### Expected coverage

| Category | Files | Result |
|---|---|---|
| UTF-8 | 160 | language detected |
| UTF-16/32 (6 variants) | 861 | language detected |
| UTF-8-sig | 2 | language detected |
| cp855/cp866/maccyrillic etc. | ~50 | language detected |
| ASCII (pure 7-bit) | ~5 | likely still None |

~1073 of 1087 remaining `language=None` files should get language filled in.

## Files changed

1. `scripts/train.py` — add `"utf-8"` entry to `ENCODING_LANG_MAP`
2. `src/chardet/pipeline/orchestrator.py` — add Tier 3 to `_fill_language`
3. `src/chardet/models/models.bin` — retrained with UTF-8 models
