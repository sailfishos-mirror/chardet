# chardet-rewrite Performance Comparison

Benchmarked on 2026-02-28 against 2161 test files using
`scripts/compare_detectors.py`. chardet-rewrite and charset-normalizer
numbers are from the current run. chardet 6.0.0, chardet 5.2.0, and
cchardet numbers are from a prior run (2026-02-27) using the same test
data and equivalence rules. All detectors run in isolated subprocesses
for consistent measurement. All detectors are evaluated with the same
equivalence rules: directional superset and bidirectional groups, plus
decoded-output equivalence (base-letter matching after NFKD normalization
and currency/euro symbol equivalence). Directional supersets include
ISO-to-Windows mappings (e.g., detecting windows-1252 when iso-8859-1 is
expected counts as correct).

The chardet-rewrite numbers below are pure Python (CPython 3.12). See
"mypyc Compilation" section below for compiled performance.

## Overall Accuracy

| Detector | Correct | Accuracy | Detection Time |
|---|---|---|---|
| **chardet-rewrite** | **2083/2161** | **96.4%** | 5.15s |
| chardet 6.0.0 | 2042/2161 | 94.5% | 183.69s |
| charset-normalizer | 1924/2161 | 89.0% | 32.59s |
| charset-normalizer (pure) | 1924/2161 | 89.0% | 53.37s |
| chardet 5.2.0 | 1469/2161 | 68.0% | 34.35s |
| cchardet | 1228/2161 | 56.8% | 0.75s |

The rewrite leads all detectors on accuracy: **+1.9pp** vs chardet 6.0.0,
**+7.4pp** vs charset-normalizer, **+28.4pp** vs chardet 5.2.0, and
**+39.6pp** vs cchardet. Speed-wise, the rewrite is **35.7x faster** than
chardet 6.0.0, **6.3x faster** than charset-normalizer, and **6.7x faster**
than chardet 5.2.0.

cchardet (C/C++ uchardet engine via faust-cchardet) is the fastest at 0.75s
but has the lowest accuracy at 56.8% -- over 39pp behind the rewrite. It
lacks support for many encodings the rewrite handles (EBCDIC, Mac encodings,
Baltic, etc.).

The two charset-normalizer variants produce identical accuracy (1924/2161).
The pure-Python build is 1.5x slower (53.37s vs 35.75s).

## Language Detection Accuracy

The rewrite returns a `language` field alongside the detected encoding.
For single-language encodings (e.g. Big5→Chinese, EUC-JP→Japanese,
ISO-8859-7→Greek), the language is inferred automatically from a
hardcoded mapping of 41 encodings. For multi-language encodings (e.g.
windows-1252, ISO-8859-5), the language comes from statistical bigram
scoring. Universal encodings (UTF-8, UTF-16, UTF-32) have no inherent
language signal and always return `language=None`.

| Metric | Count |
|---|---|
| Correct language | 930/2161 (43.0%) |
| Wrong language | 64/2161 (3.0%) |
| No language returned | 1167/2161 (54.0%) |

Of the 1167 files with no language returned:

- **1002** are universal encodings (UTF-8/16/32) where language cannot be
  determined from encoding alone
- **165** are multi-language encodings detected via early pipeline stages
  (markup charset, ASCII) that bypass statistical scoring

When a language *is* returned, it is correct **93.6%** of the time
(930 correct out of 994 non-None results). The 64 wrong-language cases
are primarily multi-language encodings where the statistical scorer picks
a plausible but incorrect language (e.g. EBCDIC cp037/cp500, iso-8859-1,
iso-8859-14).

## Detection Runtime Distribution

| Detector | Total | Mean | Median | p90 | p95 |
|---|---|---|---|---|---|
| cchardet | 742ms | 0.34ms | 0.07ms | 0.72ms | 0.95ms |
| chardet-rewrite | 5,138ms | 2.38ms | 0.28ms | 4.96ms | 5.71ms |
| chardet 5.2.0 | 34,327ms | 15.88ms | 2.94ms | 12.49ms | 22.95ms |
| charset-normalizer | 32,568ms | 15.07ms | 4.69ms | 49.02ms | 70.13ms |
| charset-normalizer (pure) | 53,337ms | 24.68ms | 7.80ms | 79.22ms | 113.68ms |
| chardet 6.0.0 | 183,650ms | 84.98ms | 16.59ms | 130.18ms | 316.52ms |

The rewrite has the lowest median latency (0.28ms) among all pure-Python
detectors, matching cchardet's order of magnitude despite being pure Python.
Its p95 (5.71ms) is well below charset-normalizer's (70ms) and chardet
6.0.0's (317ms).

## Startup & Memory

| Detector | Import Time | Traced Import | Traced Peak | RSS After |
|---|---|---|---|---|
| cchardet | 0.521s | 23.5 KiB | 27.1 KiB | 60.2 MiB |
| chardet-rewrite | 0.016s | 2.8 MiB | 20.3 MiB | 87.8 MiB |
| chardet 6.0.0 | 0.686s | 12.8 MiB | 29.2 MiB | 98.9 MiB |
| chardet 5.2.0 | 0.145s | 3.1 MiB | 64.0 MiB | 129.5 MiB |
| charset-normalizer | 0.654s | 1.7 MiB | 102.2 MiB | 263.6 MiB |
| charset-normalizer (pure) | 0.030s | 1.2 MiB | 101.7 MiB | 264.5 MiB |

Among pure-Python detectors, the rewrite has the best memory profile:

- **43x faster import** than chardet 6.0.0 (0.016s vs 0.686s)
- **4.6x less import memory** than chardet 6.0.0 (2.8 MiB vs 12.8 MiB)
- **1.4x less peak memory** than chardet 6.0.0 (20.3 MiB vs 29.2 MiB)
- **5.0x less peak memory** than charset-normalizer (20.3 MiB vs 102.2 MiB)
- **3.0x less RSS** than charset-normalizer (87.8 MiB vs 263.6 MiB)

cchardet has near-zero Python-level memory (C extension) but these numbers
reflect only tracemalloc-visible allocations. Its RSS advantage (60.2 MiB)
is modest, as the baseline interpreter itself accounts for ~59 MiB.

## Rewrite vs chardet 6.0.0 (pairwise)

*Note: These pairwise results are from the 2026-02-27 run when the rewrite
was at 95.0% accuracy. The rewrite has since improved to 96.4%; re-running
would likely shift several ties and losses into wins.*

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

### Rewrite wins (33 encodings)

Strongest in legacy Western European (iso-8859-1/15, windows-1252), DOS
codepages (cp437/cp850/cp858), Mac encodings (macroman, maciceland), and
Baltic/Central European (iso-8859-2/4/13, windows-1257). Also leads on
EBCDIC (cp500 +41.3pp, cp1026 +100pp), escape-based encodings
(hz-gb-2312, iso-2022-jp), and UTF-8-sig (+100pp).

### charset-normalizer wins (5 encodings)

cp949 (+25pp), cp932 (+14.3pp), windows-1255 (+11.1pp), maclatin2
(+6.7pp), and utf-8 (+0.6pp).

### Tied (43 encodings)

## Rewrite vs cchardet (pairwise)

*Note: These pairwise results are from the 2026-02-27 run when the rewrite
was at 95.0% accuracy.*

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

*Note: These pairwise results are from the 2026-02-27 run when the rewrite
was at 95.0% accuracy.*

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

The rewrite supports optional mypyc compilation on CPython. When built with
`HATCH_BUILD_HOOK_ENABLE_MYPYC=true`, four hot-path modules are compiled
to C extensions: `models/__init__.py` (bigram profiling and scoring),
`pipeline/structural.py` (CJK byte-scanning), `pipeline/validity.py`
(decode filtering), and `pipeline/statistical.py` (scoring orchestration).

In-process timing (2161 files, `encoding_era=ALL`, pre-loaded into memory):

| Build | Total | Per-file mean | Speedup |
|---|---|---|---|
| Pure Python | 5,066ms | 2.34ms | baseline |
| mypyc compiled | 4,982ms | 2.31ms | **1.02x** |

The mypyc speedup is now negligible (1.02x) compared to the previous 1.44x.
The cosine similarity refactor in the bigram scoring engine shifted the
bottleneck away from the Python dict iteration and integer arithmetic that
mypyc could optimize. The current hot path is dominated by operations that
CPython already handles via C: `struct.unpack_from` for model loading,
`bytes` iteration for bigram extraction, and built-in `.decode()` for
validity filtering.

Pure Python wheels are published alongside mypyc wheels for PyPy and
platforms without prebuilt binaries. No runtime dependencies are added.

## Key Takeaways

1. **The rewrite achieves 96.4% accuracy with dramatic speed/memory gains**
   vs chardet 6.0.0. It detects in ~5.1s what 6.0.0 takes 184s for, imports
   43x faster, and uses 4.6x less import memory -- while being +1.9pp more
   accurate.

2. **Remaining accuracy gaps vs chardet 6.0.0**: cp874, DOS codepages where
   6.0.0 has a slight edge (cp850/cp858), and a handful of cp037 EBCDIC
   confusions. These are niche encodings that need either model retraining
   with more data or encoding-specific structural probes.

3. **The rewrite beats all competitors** on accuracy among pure-Python
   detectors. It leads chardet 6.0.0 by +1.9pp, charset-normalizer by
   +7.4pp, and chardet 5.2.0 by +28.4pp.

4. **charset-normalizer is slowest on peak memory** (102.2 MiB traced peak,
   264 MiB RSS) despite moderate accuracy. The rewrite beats it on both
   fronts.

5. **cchardet is unbeatable on raw speed** (0.75s) but pays for it with the
   lowest accuracy (56.8%) and zero support for many encoding families. It's
   a poor choice when encoding breadth matters.

6. **mypyc compilation provides minimal speedup** (1.02x) after the cosine
   similarity refactor. The pure Python path is now fast enough that the
   remaining bottleneck is in already-C operations. mypyc wheels are still
   published for marginal gains and forward compatibility.
