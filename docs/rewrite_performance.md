# chardet-rewrite Performance Comparison

Benchmarked on 2026-02-26 against 2161 test files using
`scripts/compare_detectors.py -c 6.0.0 -c 5.2.0 --cn-variants --cchardet`.
All detectors run in isolated subprocesses for consistent measurement. All
detectors are evaluated with the same directional equivalence rules (superset
and bidirectional groups), plus decoded-output equivalence (base-letter
matching after NFKD normalization and currency/euro symbol equivalence).

## Overall Accuracy

| Detector | Correct | Accuracy | Detection Time |
|---|---|---|---|
| **chardet-rewrite** | **2062/2161** | **95.4%** | 13.11s* |
| chardet 6.0.0 | 1748/2161 | **80.9%** | 173.15s |
| charset-normalizer | 1650/2161 | **76.4%** | 32.51s |
| charset-normalizer (mypyc) | 1650/2161 | **76.4%** | 32.93s |
| charset-normalizer (pure) | 1650/2161 | **76.4%** | 49.43s |
| chardet 5.2.0 | 1241/2161 | **57.4%** | 33.01s |
| cchardet | 1061/2161 | **49.1%** | 0.79s |

*Detection time for the rewrite may differ from the original benchmark due to
the addition of per-language models, mess detection, and encoding demotion.

The rewrite is now **14.5 percentage points ahead** of chardet 6.0.0, and
ahead of charset-normalizer (+19.0pp) and chardet 5.2.0 (+38.0pp). Speed-wise,
the rewrite is **13.2x faster** than chardet 6.0.0, **2.5x faster** than
charset-normalizer (in-process), and **3.8x faster** than charset-normalizer
(pure Python).

cchardet (C/C++ uchardet engine via faust-cchardet) is the fastest at 0.79s
but has the lowest accuracy at 49.1% -- nearly 30pp behind the rewrite. It
lacks support for many encodings the rewrite handles (EBCDIC, Mac encodings,
Baltic, etc.).

The three charset-normalizer variants produce identical accuracy (1650/2161).
The mypyc-compiled version shows no measurable speed advantage over the
in-process version in subprocess measurement (both ~32-33s). The pure-Python
variant is 1.5x slower (49.43s).

## Detection Runtime Distribution

| Detector | Total | Mean | Median | p90 | p95 |
|---|---|---|---|---|---|
| cchardet | 704ms | 0.33ms | 0.07ms | 0.62ms | 0.91ms |
| chardet-rewrite | 12,968ms | 6.00ms | 0.32ms | 17.23ms | 19.41ms |
| charset-normalizer | 32,315ms | 14.95ms | 4.68ms | 48.84ms | 69.42ms |
| charset-normalizer (mypyc) | 32,730ms | 15.15ms | 4.66ms | 49.36ms | 70.34ms |
| chardet 5.2.0 | 32,858ms | 15.21ms | 2.82ms | 11.83ms | 22.00ms |
| charset-normalizer (pure) | 49,207ms | 22.77ms | 7.20ms | 75.65ms | 104.55ms |
| chardet 6.0.0 | 172,926ms | 80.02ms | 15.98ms | 119.09ms | 314.90ms |

The rewrite has the lowest median latency (0.32ms) among all pure-Python
detectors, matching cchardet's order of magnitude despite being pure Python.
Its p95 (19.41ms) is well below charset-normalizer's (69-70ms) and chardet
6.0.0's (314.90ms).

## Startup & Memory

| Detector | Import Time | Traced Import | Traced Peak | RSS After |
|---|---|---|---|---|
| cchardet | **0.002s** | **23.2 KiB** | **90.9 KiB** | **61.1 MiB** |
| chardet-rewrite | 0.040s | 1.5 MiB | 9.0 MiB | 73.8 MiB |
| charset-normalizer | 0.036s | 1.1 MiB | 101.7 MiB | 266.0 MiB |
| charset-normalizer (mypyc) | 0.037s | 1.1 MiB | 101.7 MiB | 266.6 MiB |
| charset-normalizer (pure) | 0.035s | 1.2 MiB | 101.7 MiB | 264.1 MiB |
| chardet 5.2.0 | 0.214s | 3.1 MiB | 64.0 MiB | 128.0 MiB |
| chardet 6.0.0 | 4.018s | 12.8 MiB | 29.2 MiB | 99.7 MiB |

Among pure-Python detectors, the rewrite has the best memory profile:

- **100x faster import** than chardet 6.0.0 (0.040s vs 4.018s)
- **8.5x less import memory** than chardet 6.0.0 (1.5 MiB vs 12.8 MiB)
- **3.2x less peak memory** than chardet 6.0.0 (9.0 MiB vs 29.2 MiB)
- **11.3x less peak memory** than charset-normalizer (9.0 MiB vs 101.7 MiB)
- **3.6x less RSS** than charset-normalizer (73.8 MiB vs 266.0 MiB)

cchardet has near-zero Python-level memory (C extension) but these numbers
reflect only tracemalloc-visible allocations. Its RSS advantage (61.1 MiB)
is modest, as the baseline interpreter itself accounts for ~59 MiB.

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

## Rewrite vs cchardet (pairwise)

### Rewrite wins (39 encodings)

The rewrite dominates on encoding breadth: 21 encodings at +100pp where
cchardet returns 0%. These include EBCDIC (cp037/cp500/cp875/cp1026), Mac
encodings, Baltic (cp775), UTF-32 variants, and many legacy single-byte
encodings that cchardet's uchardet engine simply doesn't support.

### cchardet wins (17 encodings)

cchardet is stronger on gb18030 (+84pp), Central/Eastern European (iso-8859-2
at +41.9pp, windows-1250 at +42.9pp), and cp866 (+41.4pp). These are encodings
where cchardet's C-level statistical models (inherited from Mozilla's uchardet)
have strong training.

### Tied (24 encodings)

## Rewrite vs chardet 5.2.0 (pairwise)

Massive improvement: rewrite wins on 48 encodings vs 5.2.0 winning on only
10. The rewrite gained all the 6.0 encoding-era support (EBCDIC, Baltic,
Central European, etc.) that 5.2.0 completely lacked. The 5.2.0 wins are
mostly in traditional chardet strengths (cp866, iso-8859-7, iso-8859-1,
macroman, euc-jp) where the older statistical models had an edge.

## charset-normalizer: mypyc vs pure Python

The three charset-normalizer variants (in-process, mypyc venv, pure-Python
venv) produce **identical accuracy** (1650/2161 = 76.4%). The mypyc build
shows no significant speed advantage in subprocess measurement (~32.7s vs
~32.5s). The pure-Python build is 1.5x slower (49.2s). All three have
identical peak memory (~101.7 MiB traced, ~265 MiB RSS).

## Key Takeaways

1. **The rewrite achieves 95.4% accuracy with dramatic speed/memory gains**
   vs chardet 6.0.0. It detects in ~13s what 6.0.0 takes 173s for, imports
   100x faster, and uses 8.5x less import memory — while being 14.5pp more
   accurate.

2. **Remaining accuracy gaps**: EBCDIC confusion (cp037/cp500/cp1026, ~24
   failures), DOS codepages (cp437/cp850/cp858, ~36 failures), and Johab
   (6 failures). These are niche encodings that need either model
   retraining with more data or encoding-specific structural probes.

3. **The rewrite beats all competitors** on accuracy, speed, and memory
   among pure-Python detectors. It leads chardet 6.0.0 by +14.5pp,
   charset-normalizer by +19.0pp, and chardet 5.2.0 by +38.0pp.

4. **charset-normalizer is slowest on peak memory** (101.7 MiB traced peak,
   266 MiB RSS) despite moderate accuracy. The rewrite beats it on both
   fronts. The mypyc build provides no meaningful advantage over pure Python
   in this workload.

5. **cchardet is unbeatable on raw speed** (0.79s) but pays for it with the
   lowest accuracy (49.1%) and zero support for many encoding families. It's
   a poor choice when encoding breadth matters.
