# chardet-rewrite Performance Comparison

Benchmarked on 2026-02-26 against 2161 test files using
`scripts/compare_detectors.py -c 6.0.0 -c 5.2.0`. All detectors are
evaluated with the same directional equivalence rules (superset and
bidirectional groups).

## Overall Accuracy

| Detector | Correct | Accuracy | Detection Time |
|---|---|---|---|
| chardet 6.0.0 | 1748/2161 | **80.9%** | 172.31s |
| chardet-rewrite | 1695/2161 | **78.4%** | 13.67s |
| charset-normalizer | 1650/2161 | **76.4%** | 31.80s |
| chardet 5.2.0 | 1241/2161 | **57.4%** | 33.07s |

The rewrite is 2.5 percentage points behind chardet 6.0.0 but ahead of both
charset-normalizer (+2.0pp) and chardet 5.2.0 (+21.0pp). Speed-wise, the
rewrite is **12.6x faster** than chardet 6.0.0.

## Startup & Memory

| Detector | Import Time | Traced Import | Traced Peak | RSS After |
|---|---|---|---|---|
| chardet-rewrite | **0.045s** | **2.0 MiB** | **9.5 MiB** | **71.6 MiB** |
| charset-normalizer | 0.046s | 1.3 MiB | 101.9 MiB | 263.2 MiB |
| chardet 6.0.0 | 4.083s | 13.0 MiB | 29.4 MiB | 99.3 MiB |
| chardet 5.2.0 | 0.226s | 3.1 MiB | 63.9 MiB | 126.8 MiB |

The rewrite has the best import profile across the board:

- **91x faster import** than chardet 6.0.0 (0.045s vs 4.083s)
- **6.5x less import memory** than chardet 6.0.0 (2.0 MiB vs 13.0 MiB)
- **3.1x less peak memory** than chardet 6.0.0 (9.5 MiB vs 29.4 MiB)
- **10.7x less peak memory** than charset-normalizer (9.5 MiB vs 101.9 MiB)

## Rewrite vs chardet 6.0.0 (pairwise)

### Rewrite wins (20 encodings)

Biggest leads:

- windows-1253 (+100pp), windows-1254 (+75pp), windows-1257 (+70pp)
- iso-8859-1 (+59.3pp, 54 files) -- a high-volume win
- cp500 (+50pp, 46 files), cp866 (+48.3pp), windows-1252 (+48pp, 50 files)
- windows-1251 (+18.9pp, 53 files)

### chardet 6.0.0 wins (25 encodings)

Biggest leads:

- iso-8859-13 (+100pp), koi8-t (+100pp), johab (+85.7pp)
- gb18030 (+84pp, 25 files) -- the rewrite barely detects this
- iso-8859-15 (+63pp, 46 files), cp850 (+60.9pp, 46 files) -- high-volume gaps
- cp037 (+48.9pp, 47 files), macroman (+28.6pp, 42 files)

### Tied (35 encodings)

utf-16, utf-32, iso-8859-5, koi8-r, shift_jis, etc.

## Rewrite vs charset-normalizer (pairwise)

### Rewrite wins (26 encodings)

Strongest in legacy Western European (iso-8859-1/windows-1252), EBCDIC
(cp500), and Mac encodings (macroman, maciceland).

### charset-normalizer wins (20 encodings)

Strongest in EBCDIC (cp037), windows-1250/1255, johab, and UTF-16 BOM-less
variants.

### Tied (34 encodings)

## Rewrite vs chardet 5.2.0 (pairwise)

Massive improvement: rewrite wins on 48 encodings vs 5.2.0 winning on only
10. The rewrite gained all the 6.0 encoding-era support (EBCDIC, Baltic,
Central European, etc.) that 5.2.0 completely lacked. The 5.2.0 wins are
mostly in traditional chardet strengths (cp866, iso-8859-7, iso-8859-1,
macroman, euc-jp) where the older statistical models had an edge.

## Key Takeaways

1. **The rewrite trades ~2.5% accuracy for dramatic speed/memory gains** vs
   chardet 6.0.0. It detects in 13.7s what 6.0.0 takes 172s for, imports
   91x faster, and uses 6.5x less import memory.

2. **Biggest accuracy gaps to close vs 6.0.0**: gb18030 (16% vs 100%),
   iso-8859-15 (0% vs 63%), cp850 (0% vs 61%), iso-8859-13 (0% vs 100%),
   iso-8859-16 (37.5% vs 93.8%). These are mostly Western/Central European
   encodings where the rewrite's bigram models need more training data or the
   probers need tuning.

3. **The rewrite already beats 6.0.0** on iso-8859-1 (+59pp),
   windows-1252 (+48pp), windows-1251 (+19pp), and windows-1257 (+70pp) --
   high-value modern Western encodings.

4. **charset-normalizer is slowest on peak memory** (101.9 MiB traced peak,
   263 MiB RSS) despite moderate accuracy. The rewrite beats it on both
   fronts.
