# Performance Doc Update Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Update `docs/rewrite_performance.md` with fresh post-thread-safety benchmark numbers and a new Thread Safety section.

**Architecture:** Run benchmarks at two git states (pre- and post-thread-safety) in both pure Python and mypyc builds. Collect numbers, then edit the doc in place: update existing rewrite rows, add a Thread Safety section before Key Takeaways, and update the takeaways.

**Tech Stack:** Python benchmark scripts (`scripts/compare_detectors.py`, `scripts/benchmark_time.py`, `scripts/benchmark_memory.py`), `uv run --python 3.13t` for free-threaded Python, mypyc via `HATCH_BUILD_HOOK_ENABLE_MYPYC=true uv build`.

---

### Task 1: Collect pre-thread-safety baseline (pure Python)

**Goal:** Get single-threaded detection time at the last commit before thread safety changes, to compare "before vs after" overhead.

**Files:**
- Read: `scripts/benchmark_time.py`, `scripts/benchmark_memory.py`

**Step 1: Create a worktree at the pre-thread-safety commit**

```bash
git worktree add /tmp/chardet-baseline 06fd801
```

**Step 2: Run pure Python timing benchmark in the worktree**

```bash
cd /tmp/chardet-baseline && uv sync && uv run python scripts/benchmark_time.py --json-only --pure 2>/dev/null | tail -1
```

Record the `total_ms` from the `__timing__` summary line.

**Step 3: Run pure Python memory benchmark**

```bash
cd /tmp/chardet-baseline && uv run python scripts/benchmark_memory.py --json-only --pure
```

Record traced_import, traced_peak, rss_after.

**Step 4: Record the numbers**

Save all baseline numbers to a temporary file for reference:

```bash
cat > /tmp/chardet-perf-baseline.txt << 'EOF'
Pre-thread-safety baseline (commit 06fd801, pure Python):
Total detection time: <from step 2>
Import time: <from step 2>
Traced import: <from step 3>
Traced peak: <from step 3>
RSS after: <from step 3>
EOF
```

**Step 5: Clean up worktree**

```bash
cd /Users/danblanchard/Documents/chardet_rewrite && git worktree remove /tmp/chardet-baseline
```

---

### Task 2: Collect post-thread-safety numbers (pure Python)

**Goal:** Get current (post-thread-safety) pure Python numbers on HEAD.

**Files:**
- Read: `scripts/benchmark_time.py`, `scripts/benchmark_memory.py`

**Step 1: Ensure no stale .so files**

```bash
find src/chardet/ -name '*.so' -o -name '*.pyd' | head -5
# Should print nothing. If any exist:
# find src/chardet/ -name '*.so' -delete && find src/chardet/ -name '*.pyd' -delete
```

**Step 2: Run the full comparison script (rewrite only, pure Python)**

```bash
uv run python scripts/compare_detectors.py --pure 2>&1 | tee /tmp/chardet-perf-current.txt
```

This gives accuracy, timing distribution, and memory in one run.
Record: correct/total, accuracy%, total time, mean, median, p90, p95,
import time, traced import, traced peak, RSS.

**Step 3: Also capture JSON timing for the before/after comparison**

```bash
uv run python scripts/benchmark_time.py --json-only --pure 2>/dev/null | tail -1
```

Record `total_ms` to compare with Task 1 baseline.

---

### Task 3: Collect post-thread-safety numbers (mypyc)

**Goal:** Get mypyc-compiled timing for the mypyc section update.

**Step 1: Build with mypyc**

```bash
HATCH_BUILD_HOOK_ENABLE_MYPYC=true uv build
```

**Step 2: Install the mypyc wheel**

```bash
uv pip install dist/chardet-*.whl --force-reinstall
```

**Step 3: Verify mypyc is active**

```bash
uv run python -c "import chardet; from pathlib import Path; print([p.name for p in Path(chardet.__file__).parent.rglob('*.so')])"
```

Should list .so files for the compiled modules.

**Step 4: Run timing benchmark**

```bash
uv run python scripts/benchmark_time.py --json-only 2>/dev/null | tail -1
```

Record total_ms and per-file mean.

**Step 5: Clean up — reinstall pure Python**

```bash
find src/chardet/ -name '*.so' -delete 2>/dev/null
uv sync
```

Verify pure is restored:

```bash
uv run python scripts/benchmark_time.py --pure --json-only 2>/dev/null | tail -1
# Should succeed (no .so abort)
```

---

### Task 4: Collect free-threaded Python numbers

**Goal:** Get single-threaded and multi-threaded performance on Python 3.13t.

**Step 1: Verify 3.13t is available**

```bash
uv run --python 3.13t python -c "import sys; print(sys.version); print('GIL disabled:', sys._is_gil_enabled() if hasattr(sys, '_is_gil_enabled') else 'N/A')"
```

Should show Python 3.13 and GIL disabled.

**Step 2: Run single-threaded timing on 3.13t**

```bash
uv run --python 3.13t python scripts/benchmark_time.py --json-only --pure 2>/dev/null | tail -1
```

Record total_ms as the 3.13t single-threaded baseline.

**Step 3: Write a small multi-threaded benchmark script**

Create `/tmp/chardet_mt_bench.py`:

```python
"""Multi-threaded chardet benchmark for free-threaded Python."""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from scripts.utils import collect_test_files


def detect_file(args: tuple[bytes, str]) -> float:
    """Detect a single file and return elapsed time."""
    import chardet
    data, _expected = args
    start = time.perf_counter()
    chardet.detect(data)
    return time.perf_counter() - start


def main() -> None:
    test_files = collect_test_files()
    # Pre-read all files
    file_data = [(path.read_bytes(), enc) for enc, path in test_files]

    # Warm up caches with a single detection
    import chardet
    chardet.detect(b"hello")

    results = {}
    for n_threads in [1, 2, 4, 8]:
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=n_threads) as pool:
            list(pool.map(detect_file, file_data))
        elapsed = time.perf_counter() - start
        results[n_threads] = round(elapsed * 1000)

    print(json.dumps(results))


if __name__ == "__main__":
    main()
```

**Step 4: Run multi-threaded benchmark on 3.13t**

```bash
uv run --python 3.13t python /tmp/chardet_mt_bench.py
```

Record the JSON output: `{1: ms, 2: ms, 4: ms, 8: ms}`.

**Step 5: Also run multi-threaded on regular CPython 3.12 for comparison**

```bash
uv run python /tmp/chardet_mt_bench.py
```

Record for comparison (GIL-bound, should show no scaling).

---

### Task 5: Update existing tables in performance doc

**Goal:** Update the chardet-rewrite rows in all existing tables with numbers from Tasks 2-3.

**Files:**
- Modify: `docs/rewrite_performance.md`

**Step 1: Update Overall Accuracy table (line ~22)**

Replace the chardet-rewrite row with new numbers from Task 2:

```markdown
| **chardet-rewrite** | **XXXX/2161** | **XX.X%** | X.XXs |
```

**Step 2: Update comparison prose (lines ~29-33)**

Recalculate the "+X.Xpp" and "X.Xx faster" comparisons using the new
rewrite numbers against the existing other-detector numbers.

**Step 3: Update Detection Runtime Distribution table (line ~80)**

Replace the chardet-rewrite row with new numbers from Task 2.

**Step 4: Update Startup & Memory table (line ~96)**

Replace the chardet-rewrite row with new numbers from Task 2.

**Step 5: Update mypyc Compilation table (line ~213)**

Replace both rows (Pure Python and mypyc compiled) with numbers from
Tasks 2 and 3. Recalculate the speedup ratio.

**Step 6: Update pairwise section notes**

Update the notes at lines ~117, ~165, ~187 that say "the rewrite was at
95.0% accuracy" to say the current accuracy number.

---

### Task 6: Add Thread Safety section

**Goal:** Add the new Thread Safety section after mypyc Compilation.

**Files:**
- Modify: `docs/rewrite_performance.md`

**Step 1: Insert the Thread Safety section before Key Takeaways**

Insert after the mypyc section (after line ~233) and before "## Key
Takeaways":

```markdown
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

Thread safety overhead (single-threaded, CPython 3.12, 2161 files):

| Build | Before | After | Delta |
|---|---|---|---|
| Pure Python | <X>ms | <X>ms | <+/- X%> |
| mypyc compiled | <X>ms | <X>ms | <+/- X%> |

Free-threaded Python scaling (3.13t, GIL disabled, 2161 files):

| Threads | Time | Speedup vs 1 thread |
|---|---|---|
| 1 | <X>ms | baseline |
| 2 | <X>ms | <X>x |
| 4 | <X>ms | <X>x |
| 8 | <X>ms | <X>x |

For comparison, CPython 3.12 (GIL enabled) shows no scaling beyond 1
thread: <X>ms regardless of thread count.
```

Fill in `<X>` placeholders with actual numbers from Tasks 1-4.

---

### Task 7: Update Key Takeaways and commit

**Goal:** Add thread safety bullet and update any changed numbers.

**Files:**
- Modify: `docs/rewrite_performance.md`

**Step 1: Update existing takeaway numbers**

If accuracy or speed ratios changed, update bullets 1-5 accordingly.

**Step 2: Add new thread safety bullet**

Add as bullet 7 (after the mypyc bullet):

```markdown
7. **Thread-safe and free-threading ready** — `detect()` and
   `detect_all()` are safe to call concurrently from any number of
   threads, with negligible single-threaded overhead. Tested on
   free-threaded Python 3.13t and 3.14t with GIL disabled, showing
   <describe scaling behavior from Task 4 data>.
```

**Step 3: Commit**

```bash
git add docs/rewrite_performance.md
git commit -m "docs: update performance doc with thread safety results"
```

**Step 4: Clean up temporary files**

```bash
rm -f /tmp/chardet-perf-baseline.txt /tmp/chardet-perf-current.txt /tmp/chardet_mt_bench.py
```
