# Performance Doc Update Design

## Goal

Update `docs/rewrite_performance.md` with fresh benchmark numbers after
thread safety changes, and add a new Thread Safety section.

## Approach: Append-only (minimal structural change)

### 1. Re-benchmark (rewrite only)

Update existing tables with fresh chardet-rewrite numbers. Keep all other
detectors' numbers from prior runs.

**Tables to update:**
- Overall Accuracy — rewrite row
- Detection Runtime Distribution — rewrite row
- Startup & Memory — rewrite row
- mypyc Compilation — rewrite timing table

**Procedure:**
- Remove stale `.so` files from `src/chardet/` before pure Python runs
- Run `compare_detectors.py` with rewrite only for accuracy + timing
- Run `benchmark_memory.py` for rewrite only
- Build with mypyc, repeat for mypyc section
- Update comparison prose ("+1.9pp", "35.7x faster", etc.) if numbers changed

**Pairwise sections:** Update the note about prior accuracy (95.0%) to the
new number. Do not re-run pairwise comparisons (those require all detectors).

### 2. New Thread Safety section

**Placement:** After "mypyc Compilation", before "Key Takeaways".

**Subsections:**

1. **Guarantees** — `detect()`/`detect_all()` are safe from any thread.
   Each call creates its own `PipelineContext`. Single `UniversalDetector`
   instances are NOT thread-safe (use one per thread).

2. **Design** — Per-run `PipelineContext` dataclass eliminates shared
   mutable state. Five load-once global caches use double-checked locking
   (zero overhead after first call). mypyc-compatible.

3. **Free-threaded Python** — CI tests on 3.13t and 3.14t with GIL
   disabled. Cold-cache race tests and high-concurrency tests pass.

4. **Performance impact** — Two tables:
   - Table 1: Thread safety overhead (single-threaded, CPython 3.12).
     Pure Python and mypyc, before vs after. Shows negligible overhead.
   - Table 2: Free-threaded Python (3.13t, GIL disabled). Single-threaded
     baseline, then 2/4/8 threads. Shows scaling behavior.
   - Install 3.13t locally via `uv run --python 3.13t`.

### 3. Key Takeaways update

Add one new bullet: thread-safe and free-threading ready, negligible
overhead. Update existing numbers if accuracy/speed changed.
