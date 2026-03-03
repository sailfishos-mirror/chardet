# Test Data Coverage Design

Fill all encoding-language gaps in the `chardet/test-data` repository so every
encoding chardet can detect has test files for every language it was
historically used with.

## Current State

- **87 registered encodings** in `src/chardet/registry.py`
- **~2,178 test files** across **588 directories** covering **83 encodings**
- **6 encodings with zero test data**: cp1006, cp1140, cp273, cp864,
  hp-roman8, utf-7
- **2 more with zero data**: iso-2022-jp-2004, iso-2022-jp-ext
- **utf-8-sig** has only 1 of 46 languages
- **19 encodings** have partial language coverage
- **~147 missing encoding-language directories** total

## Approach

Tiered: real-world sources first, CulturaX transcoding as fallback.

### Tier 1 — Mechanical (91 directories)

**utf-8-sig** (45 dirs): Take 3 existing `utf-8-{lang}/` files per language,
prepend `\xEF\xBB\xBF` BOM.

**utf-7** (46 dirs): Take 3 existing `utf-8-{lang}/` files per language,
re-encode as UTF-7. Mix in any real-world UTF-7 files found by the sourcing
step.

### Tier 2 — Real-World Sourcing (niche encodings)

Search archive.org, Usenet archives, mailing list archives for authentic
documents:

| Encoding | Sources | Rationale |
|----------|---------|-----------|
| utf-7 | Usenet/mailing list archives | RFC 2152; email-native encoding |
| hp-roman8 | archive.org HP-UX docs, HP calc programs | Only context for this encoding |
| cp273 | archive.org German mainframe docs/JCL | EBCDIC German |
| cp1140 | Post-1999 EBCDIC docs with euro sign | EBCDIC Western + Euro |
| cp864 | Arabic Usenet, archive.org DOS-era Arabic | DOS Arabic |
| cp1006 | Urdu computing archives | Urdu DOS text |
| iso-2022-jp-2004/ext | Japanese mailing list archives | Extended JIS escape sequences |
| Farsi gaps | Farsi Usenet (soc.culture.iranian) | Pre-Unicode Farsi in Arabic encodings |

Copyright: prefer public domain, CC-licensed, government documents.
Usenet posts treated as fair use for short excerpts in a test corpus.

### Tier 3 — CulturaX Generation (remaining gaps)

Load text via HuggingFace `datasets` library (same as `scripts/train.py`).
Apply normalization, substitutions, encode to target. 3 files per directory,
mixed sizes (~500B, ~2KB, ~5KB).

## Scripts

Both live in `~/repos/test-data/scripts/`.

### `find_real_test_data.py`

Searches public archives for real-world encoded files. Downloads and saves
to `{encoding}-{language}/` directories. Records provenance in
`scripts/manifest.json`.

### `generate_test_files.py`

Fills all remaining gaps after real-world sourcing:

1. Loads CulturaX text for target language via HuggingFace `datasets`
2. Applies `normalize_text()` + substitutions (see below)
3. Encodes with `errors="ignore"`
4. Quality gates: reject if >20% chars dropped, if >95% ASCII, if
   round-trip fails
5. Handles mechanical tiers (utf-8-sig BOM prepend, utf-7 re-encode)
6. Writes manifest entries
7. Updates CATALOG.md

## Substitution Tables

Reuse from `train.py`:
- Universal typographic punctuation to ASCII
- Arabic punctuation to ASCII (cp720, cp864, iso-8859-6)
- CP866: i to и (Ukrainian/Belarusian)
- Romanian: comma-below to cedilla
- Vietnamese: NFC decomposition for Windows-1258

New substitutions for test data generation:

### CP866 — Ukrainian (extends existing)

```
ї → и   (Ukrainian Yi → Russian I)
є → е   (Ukrainian Ye → Russian Ye)
ґ → г   (Ukrainian Ghe → Russian Ghe)
```

### CP866 — Belarusian

```
ў → у   (Belarusian Short U → Russian U)
```

(Combined with existing і → и.)

### CP866 — Serbian Cyrillic

```
ђ → д   (Dje → De)
ј → й   (Je → Short I)
љ → л   (Lje → El)
њ → н   (Nje → En)
ћ → ч   (Tshe → Che)
џ → ц   (Dzhe → Tse)
```

CP855 was the standard Serbian DOS codepage, but CP866 was used on
Russian-locale machines. These are standard transliteration fallbacks.

### CP866 — Macedonian Cyrillic

```
ѓ → г   (Gje → Ghe)
ѕ → з   (Dze → Ze)
ј → й   (Je → Short I)
ќ → к   (Kje → Ka)
љ → л   (Lje → El)
њ → н   (Nje → En)
џ → ц   (Dzhe → Tse)
```

### ISO-8859-6 — Farsi

ISO-8859-6 has only the 28 basic Arabic consonants. Farsi-specific letters
use their Arabic base forms:

```
پ → ب   (Pe → Ba)
چ → ج   (Che → Jim)
ژ → ز   (Zhe → Za)
گ → ک   (Gaf → Kaf)
ی → ي   (Farsi Yeh → Arabic Yeh)
ک → ك   (Farsi Kaf → Arabic Kaf)
```

Windows-1256 has all Farsi characters and does not need these.

### Croatian Normalization

```
ð → đ   (Latin small eth → Latin small d with stroke)
Ð → Đ   (Latin capital eth → Latin capital d with stroke)
```

Common OCR/copy-paste confusion in Croatian digital text.

## File Naming

- CulturaX-sourced: `culturax_{subset}_{row_id}.txt` (matches existing)
- Real-world: descriptive (e.g., `usenet_soc.culture.arab_19970315.txt`)
- utf-8-sig: same filename as utf-8 source

## Directory Naming

Matches existing test-data repo convention (`cp866`, `utf-7`, `hp-roman8`,
`iso-8859-6`) — not Python codec canonical names.

## Provenance Tracking

`scripts/manifest.json` records per file:
- `path`: relative path in test-data repo
- `source`: "archive.org", "culturax", "usenet", etc.
- `url`: original URL (real-world files)
- `culturax_id`: dataset row ID (generated files)
- `retrieved`: ISO 8601 date
- `method`: "downloaded", "transcoded", "bom-prepend"
- `notes`: free text

## CATALOG.md Update

Final step: read manifest, compute file sizes, generate markdown tables
matching existing format, insert alphabetically into CATALOG.md. Update
summary counts at top. Add new source types to Sources table.

## Validation

1. `check_test_data.py` (existing) — decode correctness, mojibake, control
   chars, language/script mismatch
2. Generation script quality gates:
   - Encoding ratio: reject if `len(encoded) / len(utf8_bytes) < 0.5`
   - Non-ASCII ratio: reject if encoded bytes >95% ASCII
   - Round-trip sanity: `decode(encode(text))` matches after substitutions
3. chardet detection accuracy is NOT gated — new known failures added to
   `_KNOWN_FAILURES` if needed

## Complete Gap List

### Zero Coverage (8 encodings, 80 directories)

- **cp1006**: urdu
- **cp1140**: danish, dutch, english, finnish, french, german, icelandic,
  indonesian, italian, norwegian, portuguese, spanish, swedish, turkish
- **cp273**: german
- **cp864**: arabic
- **hp-roman8**: danish, dutch, english, finnish, french, german, icelandic,
  indonesian, italian, norwegian, portuguese, spanish, swedish
- **iso-2022-jp-2004**: japanese
- **iso-2022-jp-ext**: japanese
- **utf-7**: all 46 test-suite languages

### Partial Coverage (11 encodings, 22 directories)

- **cp437**: danish, portuguese
- **cp866**: macedonian, serbian
- **iso-8859-10**: finnish
- **iso-8859-16**: croatian, slovak
- **iso-8859-6**: farsi
- **cp720**: farsi
- **cp852**: croatian
- **mac-latin2**: croatian
- **windows-1250**: romanian
- **windows-1256**: farsi
- **mac-roman**: icelandic

### Expansion (2 encodings, 45 directories)

- **utf-8-sig**: all languages except english (45 dirs)
