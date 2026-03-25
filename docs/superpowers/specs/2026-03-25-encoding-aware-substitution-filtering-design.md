# Encoding-Aware Substitution Filtering

**Date:** 2026-03-25
**Status:** Approved

## Problem

The training script's `_UNIVERSAL_SUBSTITUTIONS` table unconditionally replaces
typographic characters (smart quotes, em dashes, etc.) with ASCII equivalents
for all encodings. This was originally motivated by two concerns:

1. Avoiding overfitting to "smart quote + letter" patterns instead of learning
   the general "quotation mark precedes letter" pattern.
2. Enabling training for encodings that lack these characters.

However, this discards valuable signal for encodings that *do* support these
characters. For example, Windows-1252 natively encodes smart quotes, em dashes,
and other typographic punctuation — these byte patterns are strong
distinguishing features vs. ISO-8859-1 (which lacks them). By flattening
everything to ASCII, we lose that discriminative power.

## Solution

Modify `get_substitutions()` to filter substitutions based on encodability:
only substitute characters that the target encoding cannot represent. Characters
the encoding supports natively are left intact so the training data preserves
their actual byte patterns.

### Changes to `get_substitutions`

After assembling all substitutions (universal + encoding-specific), attempt to
encode each source character into the target charset. If the source character is
encodable, drop that substitution.

### Uniform filtering across all tables

The encodability filter applies uniformly to all substitution tables — universal
and encoding-specific alike. If a character is encodable in the target charset,
the substitution is dropped regardless of which table it came from. This is
correct because the same principle applies everywhere: if the encoding can
represent a character natively, its actual byte pattern is informative signal.

For example, `_ARABIC_SUBSTITUTIONS` maps Arabic comma (U+060C) to ASCII comma.
CP864 and ISO-8859-6 can encode U+060C natively, so the filter correctly drops
that substitution for those encodings — the Arabic comma's native byte position
is a distinguishing feature. The substitution still applies for encodings that
genuinely cannot represent it.

Vietnamese decomposition lives in `normalize_text()`, not in
`get_substitutions()`, so it is unaffected by this change.

### Pseudocode

```python
def get_substitutions(charset_name: str, langs: list[str]) -> dict[str, str]:
    subs = dict(_UNIVERSAL_SUBSTITUTIONS)
    # ... add encoding-specific subs as before ...

    # Validate codec upfront — a bad charset_name is a caller bug
    codecs.lookup(charset_name)

    # Filter: only keep substitutions for unencodable characters
    filtered = {}
    for char, replacement in subs.items():
        try:
            char.encode(charset_name, errors="strict")
        except UnicodeEncodeError:
            filtered[char] = replacement

    return filtered
```

**Note on NO-BREAK SPACE (U+00A0):** This character is in `_UNIVERSAL_SUBSTITUTIONS`
(mapped to ASCII space) and is encodable in virtually every single-byte encoding
(byte 0xA0). With this change, NBSP will be preserved as 0xA0 instead of being
normalized to 0x20 for most encodings. This is intentional — NBSP usage patterns
are real signal, and 0xA0 bigrams are informative. If accuracy testing reveals
NBSP noise from web-scraped data is harmful, it can be excluded from the filter
as a follow-up.

## Measuring Impact

1. Retrain models with the change.
2. Run accuracy tests and compare against 98.6% baseline (2483/2518).
3. If accuracy drops, investigate whether high-byte bigrams are being pruned
   that weren't previously (more high-byte bigrams now compete for the 0-255
   weight range). If so, evaluate whether increasing `--max-samples` recovers
   the lost accuracy.

## Scope

- **Modified:** `scripts/substitutions.py` (`get_substitutions` function)
- **Unchanged:** All other substitution tables, `normalize_text`,
  `apply_substitutions`, training pipeline, runtime detection code
