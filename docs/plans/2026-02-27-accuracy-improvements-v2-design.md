# Accuracy Improvements v2 — Design

**Date:** 2026-02-27
**Current accuracy:** 2052/2161 = 95.0% (109 failures)
**Goal:** Maximize test pass count using `is_correct` + `is_equivalent_detection`

## 1. Training Metadata

After every training run, `train.py` writes
`src/chardet/models/training_metadata.yaml` alongside `models.bin`.

**Contents:**

```yaml
training_date: "2026-02-27T14:30:00Z"
max_samples: 25000
models:
  tg/koi8-t:
    language: tg
    encoding: koi8-t
    samples_used: 25000
    bigram_entries: 796
    source: culturax
  # ... all models
```

**Fields:**

- `training_date` — ISO 8601 timestamp
- `max_samples` — cap passed to the training script
- Per-model: `samples_used` (actual count; may be less than max if the
  language has fewer available), `bigram_entries` (non-zero entries in the
  sparse table), `source` (data source name)

Generated automatically — no manual maintenance.

## 2. Retrain at 25K Samples

Bump `max_samples` default to 25,000 (up from 15,000). Retrain all models
and measure accuracy. If meaningful improvement, commit. If not, investigate
whether specific weak models (KOI8-T, mac-roman, DOS codepages) improved.

Decide whether to bump higher based on measured results.

**Disk impact:** ~7.7 GB total training cache (up from 4.6 GB).

**Stdout flushing:** Ensure `train.py` flushes stdout on every progress
update so output is visible when piped through `tee`.

## 3. KOI8-T Pipeline Heuristic

**Problem:** KOI8-T and KOI8-R share the entire 0xC0–0xFF Cyrillic letter
block (identical byte-to-codepoint mappings for all 64 bytes). The bigram
models built from that shared range score similarly, and KOI8-R wins because
Russian training data is more abundant. Result: 0/3 KOI8-T test files pass.

**Discriminating signal:** KOI8-T maps 12 bytes in 0x80–0xBF to
Tajik-specific Cyrillic letters. KOI8-R maps those same positions to
box-drawing characters, which are extremely rare in natural language text.

**Discriminating bytes:**

| Byte | KOI8-T char | Unicode |
|------|-------------|---------|
| 0x80 | қ | U+049B |
| 0x81 | ғ | U+0493 |
| 0x83 | Ғ | U+0492 |
| 0x8A | ҳ | U+04B3 |
| 0x8C | Ҳ | U+04B2 |
| 0x8D | ҷ | U+04B7 |
| 0x8E | Ҷ | U+04B6 |
| 0x90 | Қ | U+049A |
| 0xA1 | ӯ | U+04EF |
| 0xA2 | Ӯ | U+04EE |
| 0xA5 | ӣ | U+04E3 |
| 0xB5 | Ӣ | U+04E2 |

**Heuristic (in orchestrator, same pattern as `_ISO_8859_10_DISTINGUISHING`):**

After statistical scoring, if KOI8-R is the top candidate and KOI8-T is
also a candidate:

- Check if any of the 12 discriminating bytes are present in the data.
- If yes → promote KOI8-T above KOI8-R.
- If no → keep KOI8-R (the text is likely Russian).

## 4. CJK False Positive Gating

**Problem:** 7 European single-byte files are falsely detected as johab or
cp932 because scattered accented characters accidentally form valid
multibyte pairs. The existing `_gate_cjk_candidates` thresholds
(structural pair ratio, minimum non-ASCII count, byte coverage) are not
catching these.

**Root cause:** Johab lead bytes start at 0x84 — overlapping Latin
accented characters in 0xC0–0xFF. Trail bytes include 0x31–0x7E (most of
printable ASCII). So a high byte followed by a lowercase letter "looks"
like a valid multibyte pair.

**Proposed fix — lead byte diversity check:**

Genuine CJK text uses lead bytes spread across the encoding's full lead
byte range (characters drawn from a large repertoire). European false
positives cluster in a narrow band (e.g., 0xC0–0xDF for Latin accented
characters).

Add a fourth gating check in `_gate_cjk_candidates`:

- Count the number of **distinct lead byte values** in valid multibyte
  pairs.
- If the count is below a threshold (needs empirical tuning, likely ~4–8
  distinct values), reject the candidate.
- Cheap to compute: just a set of observed lead bytes during the
  structural scan already being performed.

## 5. Mac-Roman

**Current status:** 32/42 pass (76%). The bigram models work — mac-roman
wins statistical scoring on most files. The 10 failures break down as:

- 7 files with very few high bytes (1–8 total) — insufficient signal for
  any statistical model
- 1 CJK false positive (covered by Section 4)
- 2 Irish files where iso-8859-14 wins, then demotion pushes to
  windows-1252

**Decision:** Retrain first at 25K samples, then reassess. No pipeline
changes in this round.

## 6. Equivalences

**No new equivalences.** Rigorous byte-level analysis confirmed that all
true superset relationships are already defined in `equivalences.py`:

- `tis-620` → `{iso-8859-11, cp874}` (iso-8859-11 is a true superset of
  tis-620; cp874 is not a true superset but was already present)
- `iso-8859-11` → `{cp874}` (not a true superset — 9 bytes differ in
  0x80–0x97)
- `euc-kr` → `{cp949}` (cp949 is a true superset — zero differences on
  all 8225 shared two-byte sequences)

All other pairs investigated (cp850/cp858, cp037/cp500/cp1026,
shift_jis/cp932, cp866/cp1125, iso-8859-1/iso-8859-15,
iso-8859-6/windows-1256, iso-8859-7/windows-1253,
iso-8859-8/windows-1255, iso-8859-2/windows-1250) have at least one byte
where both encodings decode to different valid codepoints — not true
supersets in either direction.

The existing `is_equivalent_detection` function already handles cases
where a superset is detected for a file that only uses subset-range bytes.
