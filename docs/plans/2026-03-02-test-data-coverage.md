# Test Data Coverage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fill all ~147 missing encoding-language directories in `~/repos/test-data/` so every chardet-registered encoding has test files for every language it was historically used with.

**Architecture:** Two scripts in `~/repos/test-data/scripts/`: `find_real_test_data.py` (searches archives for real-world encoded files) and `generate_test_files.py` (fills remaining gaps via CulturaX transcoding and mechanical re-encoding). Both write provenance to `scripts/manifest.json`. Final step updates `CATALOG.md`.

**Tech Stack:** Python 3.10+ stdlib, HuggingFace `datasets` library (for CulturaX), `requests` (for archive.org), `codecs` (encoding/decoding). No chardet dependency — scripts are self-contained in the test-data repo.

**Working directories:** Scripts are created in `~/repos/test-data/scripts/`. Output files go to `~/repos/test-data/{encoding}-{language}/`. The chardet repo at `~/repos/chardet/` is only used for reading `registry.py` language mappings.

---

### Task 1: Create `scripts/` Directory and Gap Analysis Module

**Files:**
- Create: `~/repos/test-data/scripts/__init__.py` (empty)
- Create: `~/repos/test-data/scripts/encoding_gaps.py`

**Step 1: Create the scripts directory**

```bash
mkdir -p ~/repos/test-data/scripts
touch ~/repos/test-data/scripts/__init__.py
```

**Step 2: Write `encoding_gaps.py`**

This module defines:
- `ISO_TO_LANGUAGE` — ISO 639-1 code to English language name mapping (copied from `chardet/scripts/utils.py:113-162`)
- `ENCODING_LANGUAGES` — dict mapping each encoding's test-data directory prefix to the list of language names it should cover (derived from the chardet registry's language tuples)
- `ENCODING_CODEC` — dict mapping test-data directory prefix to Python codec name (for encodings where they differ, e.g., `"iso-2022-jp-2004"` → `"iso2022-jp-2004"`)
- `find_gaps(base_dir)` — scans existing directories, returns list of `(encoding, language)` tuples that are missing

The encoding-language mapping must cover ALL registered encodings. Use the registry's language tuples:
- `_WESTERN` = en, fr, de, es, pt, it, nl, da, sv, no, fi, is, id, ms
- `_WESTERN_TR` = _WESTERN + tr
- `_CYRILLIC` = ru, bg, uk, sr, mk, be
- `_CENTRAL_EU` = pl, cs, hu, hr, ro, sk, sl
- `_CENTRAL_EU_NO_RO` = pl, cs, hu, hr, sk, sl
- `_BALTIC` = et, lt, lv
- `_ARABIC` = ar, fa

Map each encoding to its languages. CJK encodings get their single language. Unicode encodings (utf-8, utf-16/32 variants, utf-8-sig, utf-7) get ALL languages. Single-language encodings (cp273=de, cp1006=ur, johab=ko, etc.) get just that language.

For `ENCODING_CODEC`, map directory prefixes that don't match Python codec names:
```python
"iso-2022-jp-2004": "iso2022-jp-2004",
"iso-2022-jp-ext": "iso2022-jp-ext",
"iso-8859-11": "iso8859-11",
"macroman": "mac-roman",
"maccyrillic": "mac-cyrillic",
"macgreek": "mac-greek",
"maciceland": "mac-iceland",
"maclatin2": "mac-latin2",
"macturkish": "mac-turkish",
# ... etc — verify each by running codecs.lookup()
```

The `find_gaps()` function should:
1. List all existing `{encoding}-{language}/` directories
2. Compare against `ENCODING_LANGUAGES`
3. Return missing `(dir_prefix, language_name)` tuples

**Step 3: Test interactively**

```bash
cd ~/repos/test-data
python3 -c "from scripts.encoding_gaps import find_gaps; gaps = find_gaps('.'); print(f'{len(gaps)} gaps'); print(gaps[:10])"
```

Expected: ~147 gaps listed.

**Step 4: Commit**

```bash
cd ~/repos/test-data
git add scripts/
git commit -m "scripts: add encoding gap analysis module"
```

---

### Task 2: Create Substitution Tables Module

**Files:**
- Create: `~/repos/test-data/scripts/substitutions.py`

**Step 1: Write `substitutions.py`**

Port the substitution tables from `~/repos/chardet/scripts/train.py` (lines 67-258) plus the new substitution groups from the design doc. This is our own MIT-licensed code so copying is fine.

The module must contain:
- `UNIVERSAL_SUBSTITUTIONS` — typographic punctuation → ASCII (from train.py lines 67-104)
- `ARABIC_SUBSTITUTIONS` — Arabic punctuation → ASCII (from train.py lines 107-111)
- `CP866_SUBSTITUTIONS` — existing і→и (from train.py lines 114-117)
- `CP866_UKRAINIAN_SUBSTITUTIONS` — ї→и, є→е, ґ→г (NEW)
- `CP866_BELARUSIAN_SUBSTITUTIONS` — ў→у (NEW)
- `CP866_SERBIAN_SUBSTITUTIONS` — ђ→д, ј→й, љ→л, њ→н, ћ→ч, џ→ц (NEW)
- `CP866_MACEDONIAN_SUBSTITUTIONS` — ѓ→г, ѕ→з, ј→й, ќ→к, љ→л, њ→н, џ→ц (NEW)
- `ISO8859_6_FARSI_SUBSTITUTIONS` — پ→ب, چ→ج, ژ→ز, گ→ک, ی→ي, ک→ك (NEW)
- `CROATIAN_NORMALIZE` — ð→đ, Ð→Đ (NEW)
- `ROMANIAN_CEDILLA_SUBSTITUTIONS` — from train.py lines 120-125
- `VIETNAMESE_DECOMPOSITION` — from train.py lines 129-258
- `normalize_text(text, encoding)` — from train.py `normalize_text()` (lines 277-285)
- `get_substitutions(encoding, language)` — extended version of train.py's (lines 261-274) that also applies the new substitution groups based on encoding+language
- `apply_substitutions(text, subs)` — from train.py (lines 288-293)

The `get_substitutions()` function logic:
```python
def get_substitutions(encoding: str, language: str) -> dict[str, str]:
    subs = dict(UNIVERSAL_SUBSTITUTIONS)
    enc_upper = encoding.upper()

    # Arabic encodings
    if enc_upper in ("CP720", "CP864", "ISO-8859-6"):
        subs.update(ARABIC_SUBSTITUTIONS)

    # CP866 Cyrillic
    if enc_upper == "CP866":
        subs.update(CP866_SUBSTITUTIONS)  # і→и
        if language == "ukrainian":
            subs.update(CP866_UKRAINIAN_SUBSTITUTIONS)
        elif language == "belarusian":
            subs.update(CP866_BELARUSIAN_SUBSTITUTIONS)
        elif language == "serbian":
            subs.update(CP866_SERBIAN_SUBSTITUTIONS)
        elif language == "macedonian":
            subs.update(CP866_MACEDONIAN_SUBSTITUTIONS)

    # ISO-8859-6 Farsi
    if enc_upper == "ISO-8859-6" and language == "farsi":
        subs.update(ISO8859_6_FARSI_SUBSTITUTIONS)

    # Croatian normalization (any encoding)
    if language == "croatian":
        subs.update(CROATIAN_NORMALIZE)

    # Romanian cedilla (all encodings except ISO-8859-16)
    if language == "romanian" and enc_upper != "ISO-8859-16":
        subs.update(ROMANIAN_CEDILLA_SUBSTITUTIONS)

    return subs
```

**Step 2: Verify substitution tables are correct**

```bash
cd ~/repos/test-data
python3 -c "
from scripts.substitutions import get_substitutions
# Verify CP866 Serbian has all 6 chars
subs = get_substitutions('cp866', 'serbian')
assert '\u0452' in subs  # ђ
assert '\u0458' in subs  # ј
print('CP866 Serbian: OK')
# Verify ISO-8859-6 Farsi has all 6 chars
subs = get_substitutions('iso-8859-6', 'farsi')
assert '\u067e' in subs  # پ
assert '\u0686' in subs  # چ
print('ISO-8859-6 Farsi: OK')
# Verify Vietnamese decomposition is loaded
from scripts.substitutions import VIETNAMESE_DECOMPOSITION
assert len(VIETNAMESE_DECOMPOSITION) > 100
print(f'Vietnamese: {len(VIETNAMESE_DECOMPOSITION)} mappings')
print('All OK')
"
```

**Step 3: Commit**

```bash
cd ~/repos/test-data
git add scripts/substitutions.py
git commit -m "scripts: add encoding substitution tables for test data generation"
```

---

### Task 3: Build `generate_test_files.py` — Core Infrastructure

**Files:**
- Create: `~/repos/test-data/scripts/generate_test_files.py`

**Step 1: Write the script skeleton**

The script should:
1. Parse args: `--base-dir` (default `.`), `--encodings` (filter), `--dry-run`, `--manifest` (default `scripts/manifest.json`)
2. Call `find_gaps()` from `encoding_gaps.py` to get all missing directories
3. Group gaps by generation method:
   - `mechanical_bom`: utf-8-sig gaps (copy utf-8 files + prepend BOM)
   - `mechanical_utf7`: utf-7 gaps (re-encode utf-8 files as UTF-7)
   - `culturax`: everything else (load from CulturaX, transcode)
4. Process each group
5. Write manifest.json
6. Print summary

Core functions needed:

```python
def generate_bom_files(base_dir, language, manifest):
    """Copy 3 utf-8 files, prepend BOM, write to utf-8-sig-{language}/."""

def generate_utf7_files(base_dir, language, manifest):
    """Read 3 utf-8 files, re-encode as UTF-7, write to utf-7-{language}/."""

def generate_culturax_files(base_dir, encoding, language, manifest):
    """Load CulturaX text, apply substitutions, encode, write 3 files."""

def load_culturax_texts(iso_lang, max_texts=20):
    """Load texts from CulturaX via HuggingFace datasets. Cache locally."""

def encode_and_validate(text, encoding, codec, language):
    """Apply substitutions, encode, run quality gates. Return bytes or None."""

def write_manifest(manifest, path):
    """Write manifest list to JSON file."""

def select_source_files(base_dir, encoding, language, count=3):
    """Pick existing files from a directory, preferring varied sizes."""
```

**Step 2: Implement the mechanical generators first (utf-8-sig, utf-7)**

`generate_bom_files()`:
- Look for `utf-8-{language}/` directory
- Pick 3 files (varied sizes if possible)
- For each: read raw bytes, prepend `b"\xef\xbb\xbf"`, write to `utf-8-sig-{language}/`
- Preserve original filename
- Add manifest entry with `method: "bom-prepend"`

`generate_utf7_files()`:
- Look for `utf-8-{language}/` directory
- Pick 3 files
- For each: read bytes, decode as utf-8, re-encode as utf-7, write to `utf-7-{language}/`
- Preserve original filename
- Add manifest entry with `method: "transcoded"`

**Step 3: Test mechanical generation with a dry run**

```bash
cd ~/repos/test-data
python3 scripts/generate_test_files.py --dry-run --encodings utf-8-sig utf-7
```

Expected: lists files it would create without writing them.

**Step 4: Run mechanical generation for real**

```bash
cd ~/repos/test-data
python3 scripts/generate_test_files.py --encodings utf-8-sig utf-7
```

Verify:
```bash
ls utf-8-sig-french/ utf-7-french/
python3 check_test_data.py . 2>&1 | grep -E "error|Error"
```

Expected: 45 new utf-8-sig directories, 46 new utf-7 directories, no decode errors.

**Step 5: Commit mechanical files**

```bash
cd ~/repos/test-data
git add utf-8-sig-* utf-7-* scripts/generate_test_files.py scripts/manifest.json
git commit -m "test-data: add utf-8-sig and utf-7 test files for all languages

Mechanical generation: utf-8-sig files are utf-8 with BOM prepended,
utf-7 files are utf-8 re-encoded as UTF-7."
```

---

### Task 4: Build `generate_test_files.py` — CulturaX Transcoding

**Files:**
- Modify: `~/repos/test-data/scripts/generate_test_files.py`

**Step 1: Implement CulturaX loading**

`load_culturax_texts()`:
- Uses HuggingFace `datasets` library: `from datasets import load_dataset`
- Streams CulturaX for the target ISO 639-1 language code
- Caches downloaded articles to `scripts/.cache/culturax/{lang}/` as individual `.txt` files (same pattern as `train.py`)
- Returns list of text strings
- Loads up to `max_texts` articles (default 20 — we only need 3 good ones after quality gates, so fetch extra)

```python
def load_culturax_texts(iso_lang: str, cache_dir: str, max_texts: int = 20) -> list[str]:
    cache_path = Path(cache_dir) / "culturax" / iso_lang
    cache_path.mkdir(parents=True, exist_ok=True)

    # Load from cache first
    cached = sorted(cache_path.glob("*.txt"))
    if len(cached) >= max_texts:
        return [f.read_text(encoding="utf-8") for f in cached[:max_texts]]

    # Download more
    from datasets import load_dataset
    ds = load_dataset("uonlp/CulturaX", iso_lang, split="train", streaming=True)
    texts = [f.read_text(encoding="utf-8") for f in cached]
    for i, example in enumerate(ds):
        if len(texts) >= max_texts:
            break
        text = example.get("text", "")
        if text and len(text) > 50:
            idx = len(cached) + (i - len(cached))
            (cache_path / f"{idx:06d}.txt").write_text(text, encoding="utf-8")
            texts.append(text)
    return texts
```

**Step 2: Implement encode_and_validate()**

Quality gates from the design doc:
1. Apply `normalize_text()` and substitutions via `get_substitutions()`
2. Encode with `errors="ignore"`
3. Reject if `len(encoded) / len(text.encode("utf-8")) < 0.5` (too many chars dropped)
4. Reject if encoded bytes are >95% ASCII (not enough encoding-specific bytes to detect)
5. Round-trip sanity: decode the encoded bytes, verify they produce valid text

```python
def encode_and_validate(
    text: str, encoding: str, codec: str, language: str
) -> bytes | None:
    text = normalize_text(text, encoding)
    subs = get_substitutions(encoding, language)
    text = apply_substitutions(text, subs)
    try:
        encoded = text.encode(codec, errors="ignore")
    except (LookupError, UnicodeEncodeError):
        return None
    if len(encoded) < 20:
        return None
    # Quality gate: encoding ratio
    utf8_len = len(text.encode("utf-8", errors="ignore"))
    if utf8_len > 0 and len(encoded) / utf8_len < 0.5:
        return None
    # Quality gate: non-ASCII ratio (skip for EBCDIC/CJK where all bytes are "non-ASCII")
    if not is_ebcdic(encoding) and not is_multibyte(encoding):
        ascii_count = sum(1 for b in encoded if b < 128)
        if len(encoded) > 0 and ascii_count / len(encoded) > 0.95:
            return None
    # Round-trip sanity
    try:
        encoded.decode(codec)
    except UnicodeDecodeError:
        return None
    return encoded
```

**Step 3: Implement generate_culturax_files()**

```python
def generate_culturax_files(
    base_dir: str, encoding: str, codec: str, language: str,
    iso_lang: str, cache_dir: str, manifest: list,
) -> int:
    """Generate 3 test files for encoding-language from CulturaX data."""
    texts = load_culturax_texts(iso_lang, cache_dir)
    if not texts:
        print(f"  SKIP {encoding}-{language}: no CulturaX data for {iso_lang}")
        return 0

    out_dir = Path(base_dir) / f"{encoding}-{language}"
    out_dir.mkdir(exist_ok=True)

    # Target 3 files with varied sizes
    target_sizes = [
        (500, 1500),    # short: 500-1500 bytes
        (1500, 4000),   # medium: 1500-4000 bytes
        (4000, 10000),  # long: 4000-10000 bytes
    ]

    files_written = 0
    text_idx = 0
    for size_min, size_max in target_sizes:
        if files_written >= 3:
            break
        # Try texts until we find one that encodes to target size range
        while text_idx < len(texts):
            text = texts[text_idx]
            text_idx += 1
            encoded = encode_and_validate(text, encoding, codec, language)
            if encoded is None:
                continue
            # Trim or skip based on size targets
            if len(encoded) < size_min:
                continue
            if len(encoded) > size_max:
                encoded = trim_to_size(encoded, codec, size_max)
            # Write file
            filename = f"culturax_{text_idx:05d}.txt"
            filepath = out_dir / filename
            filepath.write_bytes(encoded)
            manifest.append({...})
            files_written += 1
            break

    # If we couldn't hit all 3 size targets, just write whatever we can
    while files_written < 3 and text_idx < len(texts):
        text = texts[text_idx]
        text_idx += 1
        encoded = encode_and_validate(text, encoding, codec, language)
        if encoded is not None:
            filename = f"culturax_{text_idx:05d}.txt"
            (out_dir / filename).write_bytes(encoded)
            manifest.append({...})
            files_written += 1

    return files_written
```

**Step 4: Test with a small encoding gap**

```bash
cd ~/repos/test-data
python3 scripts/generate_test_files.py --encodings cp437 --dry-run
```

Expected: shows it would create `cp437-danish/` and `cp437-portuguese/` (the 2 cp437 gaps).

```bash
python3 scripts/generate_test_files.py --encodings cp437
python3 check_test_data.py cp437-danish/
```

Expected: 3 files created, no decode errors, no language mismatch.

**Step 5: Commit**

```bash
cd ~/repos/test-data
git add scripts/generate_test_files.py scripts/.cache/ cp437-*/
git commit -m "scripts: add CulturaX transcoding to generate_test_files.py

Fills encoding-language gaps by loading CulturaX web text, applying
language-specific substitutions, and encoding to target charset."
```

---

### Task 5: Build `find_real_test_data.py`

**Files:**
- Create: `~/repos/test-data/scripts/find_real_test_data.py`

This script searches public archives for authentic encoded text files.
It's best-effort — whatever it finds supplements the generated data.

**Step 1: Write the script**

The script should:
1. Take `--base-dir` (default `.`), `--manifest` (default `scripts/manifest.json`)
2. For each target encoding, search appropriate archives:
   - **archive.org**: Use the Wayback Machine CDX API (`web.archive.org/cdx/search/cdx`) to find old pages in specific encodings. Also search archive.org items/collections.
   - **Usenet/mailing list archives**: Search MARC.info, Gmane mirrors, or archive.org's Usenet collections
3. Download, validate encoding, trim to reasonable size
4. Save to `{encoding}-{language}/` with descriptive filenames
5. Record provenance in manifest

Key functions:

```python
def search_archive_org(encoding: str, language: str, query: str) -> list[dict]:
    """Search archive.org for items matching the query.
    Returns list of {url, title, description} dicts."""

def download_and_validate(url: str, encoding: str, codec: str) -> bytes | None:
    """Download URL content, verify it decodes in the expected encoding.
    Return raw bytes if valid, None if not."""

def search_usenet_archives(encoding: str, language: str) -> list[dict]:
    """Search Usenet archives for posts in the target encoding."""
```

Target encodings for real-world sourcing (from design doc):
- utf-7: email archives (Content-Transfer-Encoding: 7bit with UTF-7 charset)
- hp-roman8: HP-UX documentation
- cp273: German EBCDIC mainframe text
- cp1140: EBCDIC with euro sign
- cp864: Arabic DOS text
- cp1006: Urdu text
- iso-2022-jp-2004, iso-2022-jp-ext: Japanese email
- Farsi in cp720, iso-8859-6, windows-1256

**Step 2: Test with one encoding**

```bash
cd ~/repos/test-data
python3 scripts/find_real_test_data.py --encodings utf-7 --dry-run
```

Expected: prints URLs it would try to download.

**Step 3: Run for all target encodings**

```bash
cd ~/repos/test-data
python3 scripts/find_real_test_data.py
```

Record what was found vs what still needs generation.

**Step 4: Commit any real-world files found**

```bash
cd ~/repos/test-data
git add scripts/find_real_test_data.py
# Add any downloaded files
git add *-*/  # Only new directories
git commit -m "scripts: add real-world test data sourcing script

Searches archive.org and Usenet archives for authentic encoded text."
```

---

### Task 6: Run Full Generation Pipeline

**Step 1: Run find_real_test_data.py first**

```bash
cd ~/repos/test-data
python3 scripts/find_real_test_data.py
```

Note which gaps were filled by real data vs which remain.

**Step 2: Run generate_test_files.py to fill all remaining gaps**

```bash
cd ~/repos/test-data
python3 scripts/generate_test_files.py
```

This fills everything not already covered by real-world sourcing or
existing data.

**Step 3: Validate everything**

```bash
cd ~/repos/test-data
python3 check_test_data.py .
```

Expected: no errors (warnings are OK — existing data already has some).
Fix any errors in the generated data before proceeding.

**Step 4: Verify gap count is zero**

```bash
python3 -c "from scripts.encoding_gaps import find_gaps; gaps = find_gaps('.'); print(f'{len(gaps)} remaining gaps'); [print(f'  {e}-{l}') for e,l in gaps]"
```

Expected: 0 remaining gaps.

**Step 5: Commit all generated files**

```bash
cd ~/repos/test-data
git add .
git commit -m "test-data: fill all encoding-language coverage gaps

147 new encoding-language directories added. Every chardet-registered
encoding now has test files for all languages it historically supported.

Sources: CulturaX web text (transcoded), utf-8 re-encoding (utf-7,
utf-8-sig), archive.org/Usenet (niche encodings)."
```

---

### Task 7: Update CATALOG.md

**Files:**
- Modify: `~/repos/test-data/CATALOG.md`
- Modify: `~/repos/test-data/scripts/generate_test_files.py` (add `update_catalog()` function)

**Step 1: Add `update_catalog()` to generate_test_files.py**

This function:
1. Reads `scripts/manifest.json` to get provenance for new files
2. For each new directory, computes file sizes from disk
3. Generates a markdown table in the same format as existing entries:

```markdown
#### `{encoding}-{language}/` — {N} files

| File | Source | Size | Notes |
|------|--------|-----:|-------|
| {filename} | {source} | {size} | {notes} |
```

4. Reads existing CATALOG.md
5. Inserts new entries in alphabetical order within the correct section
6. Updates the summary line at the top: `**N files** across **M directories** covering **K encodings**`
7. Adds any new source types to the Sources table

The function should identify the correct section for each encoding:
- Unicode section: utf-7, utf-8-sig (utf-8, utf-16, utf-32 variants already there)
- The rest go in existing encoding-family sections, alphabetically

**Step 2: Run the catalog update**

```bash
cd ~/repos/test-data
python3 scripts/generate_test_files.py --update-catalog-only
```

**Step 3: Verify CATALOG.md looks correct**

```bash
# Check that new entries are present
grep -c "^####" CATALOG.md  # Should show total directory count
head -10 CATALOG.md  # Verify summary line updated
grep "cp864-arabic" CATALOG.md  # Spot-check a new entry
grep "utf-7-english" CATALOG.md  # Spot-check another
```

**Step 4: Commit**

```bash
cd ~/repos/test-data
git add CATALOG.md scripts/generate_test_files.py scripts/manifest.json
git commit -m "docs: update CATALOG.md with all new test data entries

All 147 new encoding-language directories documented with file sizes,
sources, and provenance."
```

---

### Task 8: Run chardet Tests Against New Data

**Files:**
- Possibly modify: `~/repos/chardet/tests/test_accuracy.py` (add new known failures)

**Step 1: Update chardet's cached test data**

```bash
cd ~/repos/chardet
# Remove cached test data so it re-clones from the test-data repo
rm -rf tests/data/
```

Wait — the test data is cloned from GitHub, but we haven't pushed our test-data changes yet. Instead, symlink or copy:

```bash
cd ~/repos/chardet
rm -rf tests/data
ln -s ~/repos/test-data tests/data
```

**Step 2: Run chardet accuracy tests**

```bash
cd ~/repos/chardet
uv run python -m pytest tests/test_accuracy.py -x --tb=short 2>&1 | tail -40
```

**Step 3: Identify new failures**

Any test failures on new test data are expected — these are encoding-language combos that didn't have coverage before. Add them to `_KNOWN_FAILURES` in `tests/test_accuracy.py` with a comment explaining they're new coverage gaps.

```bash
cd ~/repos/chardet
uv run python -m pytest tests/test_accuracy.py --tb=line 2>&1 | grep "FAILED" | head -20
```

For each failure, add to `_KNOWN_FAILURES`:
```python
# New test data coverage — detection not yet tuned for these combos
"cp864-arabic/culturax_00001.txt",
```

**Step 4: Verify all tests pass with known failures**

```bash
cd ~/repos/chardet
uv run python -m pytest tests/test_accuracy.py -v
```

Expected: all pass (some xfail).

**Step 5: Commit any chardet test changes**

```bash
cd ~/repos/chardet
git add tests/test_accuracy.py
git commit -m "tests: add known failures for new test data coverage

New encoding-language test data added to test-data repo. Detection
accuracy for these combos will be improved incrementally."
```

---

### Task 9: Push Test Data and Final Verification

**Step 1: Final validation in test-data repo**

```bash
cd ~/repos/test-data
python3 check_test_data.py .
python3 -c "from scripts.encoding_gaps import find_gaps; gaps = find_gaps('.'); assert len(gaps) == 0, f'{len(gaps)} gaps remain'"
```

**Step 2: Review manifest completeness**

```bash
cd ~/repos/test-data
python3 -c "
import json
m = json.load(open('scripts/manifest.json'))
print(f'{len(m)} files in manifest')
sources = set(e['source'] for e in m)
print(f'Sources: {sources}')
methods = set(e['method'] for e in m)
print(f'Methods: {methods}')
"
```

**Step 3: Push test-data repo**

```bash
cd ~/repos/test-data
git push origin main
```

**Step 4: Clean up chardet symlink and re-clone**

```bash
cd ~/repos/chardet
rm tests/data  # Remove symlink
uv run python -m pytest tests/test_accuracy.py -v  # This will re-clone from GitHub
```

**Step 5: Commit chardet changes if any remain**

```bash
cd ~/repos/chardet
git status
# Commit any remaining changes
```
