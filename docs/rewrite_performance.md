# chardet-rewrite Performance Comparison

Benchmarked on 2026-02-27 against 2161 test files using
`scripts/compare_detectors.py -c 6.0.0 -c 5.2.0 --cn-variants --cchardet`.
All detectors run in isolated subprocesses for consistent measurement. All
detectors are evaluated with the same equivalence rules: directional superset
and bidirectional groups, plus decoded-output equivalence (base-letter matching
after NFKD normalization and currency/euro symbol equivalence). Directional
supersets include ISO-to-Windows mappings (e.g., detecting windows-1252 when
iso-8859-1 is expected counts as correct).

The chardet-rewrite numbers below are pure Python (CPython 3.12). See
"mypyc Compilation" section below for compiled performance.

## Overall Accuracy

| Detector | Correct | Accuracy | Detection Time |
|---|---|---|---|
| **chardet-rewrite** | **2052/2161** | **95.0%** | 5.17s |
| chardet 6.0.0 | 2042/2161 | 94.5% | 183.69s |
| charset-normalizer | 1924/2161 | 89.0% | 35.75s |
| charset-normalizer (pure) | 1924/2161 | 89.0% | 53.37s |
| chardet 5.2.0 | 1469/2161 | 68.0% | 34.35s |
| cchardet | 1228/2161 | 56.8% | 0.75s |

The rewrite leads all detectors on accuracy: **+0.5pp** vs chardet 6.0.0,
**+6.0pp** vs charset-normalizer, **+27.0pp** vs chardet 5.2.0, and
**+38.2pp** vs cchardet. Speed-wise, the rewrite is **35.5x faster** than
chardet 6.0.0, **6.9x faster** than charset-normalizer, and **6.6x faster**
than chardet 5.2.0.

cchardet (C/C++ uchardet engine via faust-cchardet) is the fastest at 0.75s
but has the lowest accuracy at 56.8% -- over 38pp behind the rewrite. It
lacks support for many encodings the rewrite handles (EBCDIC, Mac encodings,
Baltic, etc.).

The two charset-normalizer variants produce identical accuracy (1924/2161).
The pure-Python build is 1.5x slower (53.37s vs 35.75s).

## Detection Runtime Distribution

| Detector | Total | Mean | Median | p90 | p95 |
|---|---|---|---|---|---|
| cchardet | 742ms | 0.34ms | 0.07ms | 0.72ms | 0.95ms |
| chardet-rewrite | 5,148ms | 2.38ms | 0.27ms | 5.18ms | 6.06ms |
| chardet 5.2.0 | 34,327ms | 15.88ms | 2.94ms | 12.49ms | 22.95ms |
| charset-normalizer | 35,720ms | 16.53ms | 5.16ms | 53.07ms | 74.55ms |
| charset-normalizer (pure) | 53,337ms | 24.68ms | 7.80ms | 79.22ms | 113.68ms |
| chardet 6.0.0 | 183,650ms | 84.98ms | 16.59ms | 130.18ms | 316.52ms |

The rewrite has the lowest median latency (0.27ms) among all pure-Python
detectors, matching cchardet's order of magnitude despite being pure Python.
Its p95 (6.06ms) is well below charset-normalizer's (75ms) and chardet
6.0.0's (317ms).

## Startup & Memory

| Detector | Import Time | Traced Import | Traced Peak | RSS After |
|---|---|---|---|---|
| cchardet | 0.521s | 23.5 KiB | 27.1 KiB | 60.2 MiB |
| chardet-rewrite | 0.016s | 2.3 MiB | 19.4 MiB | 87.1 MiB |
| chardet 6.0.0 | 0.686s | 12.8 MiB | 29.2 MiB | 98.9 MiB |
| chardet 5.2.0 | 0.145s | 3.1 MiB | 64.0 MiB | 129.5 MiB |
| charset-normalizer | 0.543s | 1.1 MiB | 101.7 MiB | 263.0 MiB |
| charset-normalizer (pure) | 0.030s | 1.2 MiB | 101.7 MiB | 264.5 MiB |

Among pure-Python detectors, the rewrite has the best memory profile:

- **43x faster import** than chardet 6.0.0 (0.016s vs 0.686s)
- **5.6x less import memory** than chardet 6.0.0 (2.3 MiB vs 12.8 MiB)
- **1.5x less peak memory** than chardet 6.0.0 (19.4 MiB vs 29.2 MiB)
- **5.2x less peak memory** than charset-normalizer (19.4 MiB vs 101.7 MiB)
- **3.0x less RSS** than charset-normalizer (87.1 MiB vs 263.0 MiB)

cchardet has near-zero Python-level memory (C extension) but these numbers
reflect only tracemalloc-visible allocations. Its RSS advantage (60.2 MiB)
is modest, as the baseline interpreter itself accounts for ~59 MiB.

## Rewrite vs chardet 6.0.0 (pairwise)

### Rewrite wins (18 encodings)

Biggest leads:

- cp424 (+75pp), iso-8859-7 (+41.2pp, 17 files)
- cp1026/cp720/macturkish/windows-1253 (+33.3pp each)
- cp857/windows-1254 (+25pp), windows-1251 (+24.5pp, 53 files)
- iso-8859-9 (+22.2pp), cp500 (+21.7pp, 46 files)
- windows-1250 (+14.3pp, 28 files), iso-8859-3 (+11.1pp)

### chardet 6.0.0 wins (15 encodings)

Biggest leads:

- cp874 (+40pp)
- cp037 (+25.5pp, 47 files) -- EBCDIC confusion
- cp949 (+25pp), cp865 (+16.7pp), cp852 (+15pp)
- cp932 (+14.3pp), cp858 (+13pp)
- windows-1255 (+11.1pp), windows-1257 (+10pp, 10 files)
- macroman (+9.5pp, 42 files)

### Tied (48 encodings)

utf-16, utf-32, iso-8859-5, iso-8859-6, koi8-r, koi8-t, shift_jis, euc-jp,
euc-kr, gb2312, etc.

## Rewrite vs charset-normalizer (pairwise)

### Rewrite wins (34 encodings)

Strongest in legacy Western European (iso-8859-1/15, windows-1252), DOS
codepages (cp437/cp850/cp858), Mac encodings (macroman, maciceland), and
Baltic/Central European (iso-8859-2/4/13, windows-1257).

### charset-normalizer wins (6 encodings)

Strongest in EBCDIC (cp037 +23.4pp), cp932/cp949, cp424, and windows-1255.

### Tied (41 encodings)

## Rewrite vs cchardet (pairwise)

### Rewrite wins (49 encodings)

The rewrite dominates on encoding breadth: 25 encodings at +100pp where
cchardet returns 0%. These include EBCDIC (cp037/cp500/cp875/cp1026), Mac
encodings, Baltic (cp775), UTF-16/32 BOM-less variants, and many legacy
single-byte encodings that cchardet's uchardet engine simply doesn't support.

### cchardet wins (4 encodings)

cchardet is stronger on cp949 (+25pp), windows-1255 (+11.1pp), cp852 (+5pp),
and cp866 (+3.4pp). The expanded superset equivalences (ISO-to-Windows
mappings) eliminated many former cchardet wins where both detectors find
valid supersets.

### Tied (28 encodings)

## Rewrite vs chardet 5.2.0 (pairwise)

Massive improvement: rewrite wins on 51 encodings vs 5.2.0 winning on only
7. The rewrite gained all the 6.0 encoding-era support (EBCDIC, Baltic,
Central European, etc.) that 5.2.0 completely lacked. The 5.2.0 wins are
in traditional chardet strengths (cp949, cp932, windows-1255, windows-1252,
iso-8859-15, cp866, iso-8859-1) where the older statistical models had a
small edge.

## charset-normalizer: mypyc vs pure Python

The two charset-normalizer variants (mypyc default, pure-Python venv) produce
**identical accuracy** (1924/2161 = 89.0%). The mypyc build is 1.5x faster
(35.75s vs 53.37s). Both have identical peak memory (~101.7 MiB traced,
~264 MiB RSS).

## mypyc Compilation

The rewrite supports optional mypyc compilation for an additional speedup on
CPython. When built with `HATCH_BUILD_HOOK_ENABLE_MYPYC=true`, four hot-path
modules are compiled to C extensions: `models/__init__.py` (bigram profiling
and scoring), `pipeline/structural.py` (CJK byte-scanning),
`pipeline/validity.py` (decode filtering), and `pipeline/statistical.py`
(scoring orchestration).

In-process timing (best of 3 runs, 2161 files, pre-loaded into memory):

| Build | Total | Per-file mean | Speedup |
|---|---|---|---|
| Pure Python | 5,331ms | 2.47ms | baseline |
| mypyc compiled | 3,692ms | 1.71ms | **1.44x** |

The 1.44x speedup comes primarily from the bigram scoring inner loop
(`BigramProfile.__init__` and `_score_with_profile`), which accounts for
the majority of detection runtime. mypyc converts the Python dict iteration
and integer arithmetic to native C operations.

The speedup is modest compared to the theoretical maximum because:

- Deterministic stages (BOM, ASCII, UTF-8, escape) are already near-instant
- `filter_by_validity` delegates to CPython's built-in `.decode()` (already C)
- Model loading uses `struct.unpack_from` (already C)

Pure Python wheels are published alongside mypyc wheels for PyPy and
platforms without prebuilt binaries. No runtime dependencies are added.

## Key Takeaways

1. **The rewrite achieves 95.0% accuracy with dramatic speed/memory gains**
   vs chardet 6.0.0. It detects in ~5.2s what 6.0.0 takes 184s for, imports
   43x faster, and uses 5.6x less import memory -- while being +0.5pp more
   accurate. With mypyc compilation, detection time drops to ~3.7s (50x
   faster than chardet 6.0.0).

2. **Remaining accuracy gaps vs chardet 6.0.0**: EBCDIC confusion
   (cp037 at 72.3% vs 97.9%), cp874, and DOS codepages where 6.0.0 has a
   slight edge (cp850/cp858). These are niche encodings that need either
   model retraining with more data or encoding-specific structural probes.

3. **The rewrite beats all competitors** on accuracy among pure-Python
   detectors. It leads chardet 6.0.0 by +0.5pp, charset-normalizer by
   +6.0pp, and chardet 5.2.0 by +27.0pp.

4. **charset-normalizer is slowest on peak memory** (101.7 MiB traced peak,
   264 MiB RSS) despite moderate accuracy. The rewrite beats it on both
   fronts.

5. **cchardet is unbeatable on raw speed** (0.75s) but pays for it with the
   lowest accuracy (56.8%) and zero support for many encoding families. It's
   a poor choice when encoding breadth matters.
