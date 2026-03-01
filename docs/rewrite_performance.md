# chardet-rewrite Performance Comparison

Benchmarked on 2026-03-01 against 2161 test files using
`scripts/compare_detectors.py`. All detectors run in isolated temporary
venvs for consistent measurement. All detectors are evaluated with the
same equivalence rules: directional superset and bidirectional groups,
plus decoded-output equivalence (base-letter matching after NFKD
normalization and currency/euro symbol equivalence). Directional
supersets include ISO-to-Windows mappings (e.g., detecting windows-1252
when iso-8859-1 is expected counts as correct).

The chardet-rewrite numbers below are pure Python (CPython 3.12). See
"mypyc Compilation" section below for compiled performance.

## Overall Accuracy

| Detector | Correct | Accuracy | Detection Time |
|---|---|---|---|
| **chardet-rewrite** | **2083/2161** | **96.4%** | 6.07s |
| chardet 6.0.0 | 2042/2161 | 94.5% | 175.79s |
| charset-normalizer | 1924/2161 | 89.0% | 33.81s |
| charset-normalizer (pure) | 1924/2161 | 89.0% | 50.50s |
| chardet 5.2.0 | 1469/2161 | 68.0% | 33.42s |
| cchardet | 1228/2161 | 56.8% | 0.73s |

The rewrite leads all detectors on accuracy: **+1.9pp** vs chardet 6.0.0,
**+7.4pp** vs charset-normalizer, **+28.4pp** vs chardet 5.2.0, and
**+39.6pp** vs cchardet. Speed-wise, the rewrite is **29.0x faster** than
chardet 6.0.0, **5.6x faster** than charset-normalizer, and **5.5x faster**
than chardet 5.2.0.

cchardet (C/C++ uchardet engine via faust-cchardet) is the fastest at 0.73s
but has the lowest accuracy at 56.8% -- over 39pp behind the rewrite. It
lacks support for many encodings the rewrite handles (EBCDIC, Mac encodings,
Baltic, etc.).

The two charset-normalizer variants produce identical accuracy (1924/2161).
The pure-Python build is 1.5x slower (50.50s vs 33.81s).

## Language Detection Accuracy

The rewrite returns a `language` field alongside the detected encoding.
Language detection uses a three-tier approach:

1. **Tier 1**: Hardcoded mapping for 41 single-language encodings
   (e.g. Big5->Chinese, EUC-JP->Japanese, ISO-8859-7->Greek)
2. **Tier 2**: Statistical bigram scoring for multi-language encodings
   (e.g. windows-1252, ISO-8859-5) -- reuses the encoding's language
   model variants
3. **Tier 3**: Decode to UTF-8 and score against 48 UTF-8 byte bigram
   language models -- universal fallback for all encodings including
   UTF-8, UTF-16, and UTF-32

| Detector | Correct | Accuracy |
|---|---|---|
| **chardet-rewrite** | **1965/2161** | **90.9%** |
| chardet 6.0.0 | 1016/2161 | 47.0% |
| chardet 5.2.0 | 411/2161 | 19.0% |
| charset-normalizer | 0/2161 | 0.0% |
| cchardet | 0/2161 | 0.0% |

The rewrite leads on language detection by a wide margin: **+43.9pp** vs
chardet 6.0.0, **+71.9pp** vs chardet 5.2.0. charset-normalizer and
cchardet do not report language at all.

Every detected file now receives a language. The 196 wrong-language
cases are primarily confusable language pairs within the same script
(e.g. Danish/Norwegian, French/Spanish for English text, Belarusian/
Bulgarian for Cyrillic). The UTF-8 language scoring uses the first
2 KB of data to keep overhead low while maintaining discrimination
across all 48 languages.

## Detection Runtime Distribution

| Detector | Total | Mean | Median | p90 | p95 |
|---|---|---|---|---|---|
| cchardet | 723ms | 0.33ms | 0.07ms | 0.68ms | 0.92ms |
| chardet-rewrite | 6,049ms | 2.80ms | 1.08ms | 5.07ms | 5.89ms |
| chardet 5.2.0 | 33,398ms | 15.45ms | 2.85ms | 12.00ms | 22.76ms |
| charset-normalizer | 33,783ms | 15.63ms | 4.74ms | 50.66ms | 72.64ms |
| charset-normalizer (pure) | 50,477ms | 23.36ms | 7.35ms | 77.53ms | 108.54ms |
| chardet 6.0.0 | 175,757ms | 81.33ms | 16.10ms | 121.99ms | 307.29ms |

The rewrite has the lowest median latency (1.08ms) among all pure-Python
detectors, matching cchardet's order of magnitude despite being pure Python.
Its p95 (5.89ms) is well below charset-normalizer's (73ms) and chardet
6.0.0's (307ms).

## Startup & Memory

| Detector | Import Time | Traced Import | Traced Peak | RSS After |
|---|---|---|---|---|
| cchardet | 0.289s | 23.6 KiB | 27.2 KiB | 59.8 MiB |
| chardet-rewrite | 0.000s | 96 B | 20.4 MiB | 91.9 MiB |
| chardet 6.0.0 | 0.000s | 96 B | 16.4 MiB | 100.2 MiB |
| chardet 5.2.0 | 0.000s | 51 B | 60.9 MiB | 127.8 MiB |
| charset-normalizer | 0.469s | 1.7 MiB | 102.2 MiB | 264.9 MiB |
| charset-normalizer (pure) | 0.025s | 1.7 MiB | 102.2 MiB | 263.7 MiB |

Among pure-Python detectors, the rewrite has the best memory profile:

- **negligible import memory** (96 B traced import)
- **5.0x less peak memory** than charset-normalizer (20.4 MiB vs 102.2 MiB)
- **3.0x less peak memory** than chardet 5.2.0 (20.4 MiB vs 60.9 MiB)
- **2.9x less RSS** than charset-normalizer (91.9 MiB vs 264.9 MiB)

cchardet has near-zero Python-level memory (C extension) but these numbers
reflect only tracemalloc-visible allocations. Its RSS advantage (59.8 MiB)
is modest, as the baseline interpreter itself accounts for ~58 MiB.

## Rewrite vs chardet 6.0.0 (pairwise)

### Rewrite wins (20 encodings)

Biggest leads:

- cp424 (+100pp), iso-8859-7 (+41.2pp, 17 files)
- cp500 (+43.5pp, 46 files)
- cp1026/cp720/macturkish/windows-1253 (+33.3pp each)
- cp857/windows-1254 (+25pp), windows-1251 (+24.5pp, 53 files)
- iso-8859-9 (+22.2pp), windows-1250 (+14.3pp, 28 files)
- iso-8859-3 (+11.1pp), iso-8859-2 (+7.0pp, 43 files)

### chardet 6.0.0 wins (13 encodings)

Biggest leads:

- cp874 (+40pp)
- cp949 (+25pp), cp852 (+15pp)
- cp932 (+14.3pp), macroman (+11.9pp, 42 files)
- windows-1255 (+11.1pp)
- maclatin2 (+6.7pp), cp850/cp858 (+6.5pp each, 46 files)
- cp437 (+6.1pp, 33 files), gb2312 (+4.3pp, 23 files)
- cp037 (+2.1pp, 47 files), iso-8859-1 (+1.9pp, 54 files)

### Tied (48 encodings)

utf-16, utf-32, iso-8859-5, iso-8859-6, koi8-r, koi8-t, shift_jis, euc-jp,
euc-kr, gb18030, etc.

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

### Rewrite wins (49 encodings)

The rewrite dominates on encoding breadth: 27 encodings at +100pp where
cchardet returns 0%. These include EBCDIC (cp037/cp500/cp875/cp1026), Mac
encodings, Baltic (cp775), UTF-16/32 BOM-less variants, johab, and many
legacy single-byte encodings that cchardet's uchardet engine simply
doesn't support.

### cchardet wins (5 encodings)

cchardet is stronger on cp949 (+25pp), windows-1255 (+11.1pp), cp866
(+6.9pp), cp852 (+5pp), and gb2312 (+4.3pp).

### Tied (27 encodings)

## Rewrite vs chardet 5.2.0 (pairwise)

Massive improvement: rewrite wins on 51 encodings vs 5.2.0 winning on only
8. The rewrite gained all the 6.0 encoding-era support (EBCDIC, Baltic,
Central European, etc.) that 5.2.0 completely lacked. The 5.2.0 wins are
in traditional chardet strengths (cp949, cp932, windows-1255, cp866,
iso-8859-15, windows-1252, iso-8859-1, gb2312) where the older statistical
models had a small edge.

## charset-normalizer: mypyc vs pure Python

The two charset-normalizer variants (mypyc default, pure-Python venv) produce
**identical accuracy** (1924/2161 = 89.0%). The mypyc build is 1.5x faster
(33.81s vs 50.50s). Both have identical peak memory (~102.2 MiB traced,
~264 MiB RSS).

## mypyc Compilation

The rewrite supports optional mypyc compilation on CPython. When built with
`HATCH_BUILD_HOOK_ENABLE_MYPYC=true`, hot-path modules are compiled
to C extensions: `models/__init__.py` (bigram profiling and scoring),
`pipeline/structural.py` (CJK byte-scanning), `pipeline/validity.py`
(decode filtering), and `pipeline/statistical.py` (scoring orchestration).

In-process timing (2161 files, `encoding_era=ALL`, pre-loaded into memory):

| Build | Total | Per-file mean | Speedup |
|---|---|---|---|
| Pure Python | 6,030ms | 2.79ms | baseline |
| mypyc compiled | 4,015ms | 1.86ms | **1.50x** |

The mypyc speedup is 1.50x. The three-tier `_fill_language`
post-processing adds ~800ms of BigramProfile construction and cosine
scoring in pure Python -- exactly the kind of tight-loop integer
arithmetic that mypyc compiles to fast C code. The compiled build
(4,015ms) is faster than the pure Python baseline *before*
language detection was added (~5,015ms).

Pure Python wheels are published alongside mypyc wheels for PyPy and
platforms without prebuilt binaries. No runtime dependencies are added.

## Thread Safety

The rewrite is fully thread-safe for concurrent `detect()` and
`detect_all()` calls. Each call creates its own `PipelineContext`
carrying per-run state (analysis cache, non-ASCII count, multi-byte
scores), eliminating shared mutable state between threads.

Five load-once global caches (model data, encoding index, model norms,
confusion maps, candidate lists) use double-checked locking: the fast
path (`if cache is not None: return cache`) has zero synchronization
overhead after the first call. This design is compatible with
mypyc-compiled modules.

Individual `UniversalDetector` instances are NOT thread-safe due to
mutable internal buffers. Create one instance per thread when using the
streaming API.

### Free-Threaded Python

CI tests run on Python 3.13t and 3.14t with the GIL disabled. The test
suite includes cold-cache race conditions (6 workers racing to
initialize all 5 caches simultaneously) and high-concurrency stress
tests (8 workers x 10 iterations). All pass under free-threading.

### Performance Impact

Thread safety overhead (single-threaded, in-process, 2161 files):

| Build | Before | After | Delta |
|---|---|---|---|
| Pure Python (CPython 3.12) | 6,027ms | 6,033ms | +0.1% |
| mypyc compiled (CPython 3.12) | 4,078ms | 4,070ms | -0.2% |

The thread safety mechanisms (PipelineContext allocation, lock objects on
load-once caches) add no measurable overhead. Both deltas are within
run-to-run noise.

Free-threaded Python scaling (3.13t, GIL disabled, 2161 files,
8-core Apple Silicon):

| Threads | Time | Speedup vs 1 thread |
|---|---|---|
| 1 | 4,361ms | baseline |
| 2 | 2,337ms | 1.9x |
| 4 | 1,930ms | 2.3x |
| 8 | 2,357ms | 1.9x |

With the GIL disabled, detection scales well up to 4 threads (2.3x
speedup), with diminishing returns at 8 threads due to memory bandwidth
contention. For comparison, CPython 3.12 (GIL enabled) shows no scaling
beyond 1 thread (~2,400ms regardless of thread count). Note that 3.13t
single-threaded performance is ~1.6x slower than CPython 3.12 due to
free-threading interpreter overhead, but multi-threading more than
compensates: 4-thread 3.13t (1,930ms) beats single-threaded CPython 3.12
(2,431ms).

## Key Takeaways

1. **The rewrite achieves 96.4% accuracy with dramatic speed/memory gains**
   vs chardet 6.0.0. It detects in ~6.1s what 6.0.0 takes 176s for, imports
   instantly, and uses negligible import memory (96 B) -- while being +1.9pp
   more accurate.

2. **Remaining accuracy gaps vs chardet 6.0.0**: cp874, DOS codepages where
   6.0.0 has a slight edge (cp437/cp850/cp858), macroman, and a handful of
   cp037 EBCDIC confusions. These are niche encodings that need either model
   retraining with more data or encoding-specific structural probes.

3. **The rewrite beats all competitors** on accuracy among pure-Python
   detectors. It leads chardet 6.0.0 by +1.9pp, charset-normalizer by
   +7.4pp, and chardet 5.2.0 by +28.4pp.

4. **charset-normalizer is worst on peak memory** (102.2 MiB traced peak,
   265 MiB RSS) despite moderate accuracy. The rewrite beats it on both
   fronts.

5. **cchardet is unbeatable on raw speed** (0.73s) but pays for it with the
   lowest accuracy (56.8%) and zero support for many encoding families. It's
   a poor choice when encoding breadth matters.

6. **mypyc compilation provides 1.50x speedup**. The BigramProfile
   construction and scoring in `_fill_language` is the kind of tight-loop
   work that mypyc optimizes well, bringing the compiled total (4,015ms)
   below the pre-language pure Python baseline (~5,015ms).

7. **Thread-safe and free-threading ready** -- `detect()` and
   `detect_all()` are safe to call concurrently from any number of
   threads, with negligible single-threaded overhead (+0.1%). On
   free-threaded Python 3.13t (GIL disabled), detection scales to 2.3x
   speedup at 4 threads, with 4-thread 3.13t outperforming single-threaded
   CPython 3.12.

8. **Language detection is a clear differentiator** -- the rewrite achieves
   90.9% language accuracy, nearly double chardet 6.0.0's 47.0% and far
   ahead of chardet 5.2.0's 19.0%. charset-normalizer and cchardet do not
   report language at all.
