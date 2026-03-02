# Full Python Character Encoding Coverage

## Goal

Enable chardet to claim support for every character encoding Python can decode
(excluding 7 transform codecs: base64, bz2, hex, quopri, rot-13, uu, zlib).

## Approach: Aliases with Flipped Supersets

Add 15 missing encodings to the registry. Where a missing encoding is the
*superset* of an existing primary, flip the relationship: the superset becomes
the primary entry and the former primary becomes an alias. This follows the
principle of returning the broadest encoding that can decode the bytes, to
minimize UnicodeDecodeError risk on unseen portions of the input.

## Registry Changes

### Big5 Family (flip)

- **New primary:** `big5hkscs` (`python_codec="big5hkscs"`)
- **Aliases:** `big5`, `big5-tw`, `csbig5`, `cp950`
- **Replaces:** current `big5` entry

### GB Family (no flip, already broadest)

- **Primary:** `gb18030` (unchanged)
- **New aliases added:** `gb2312`, `gbk`

### EUC-JP Family (flip)

- **New primary:** `euc-jis-2004` (`python_codec="euc_jis_2004"`)
- **Aliases:** `euc-jp`, `eucjp`, `ujis`, `u-jis`, `euc-jisx0213`
- **Replaces:** current `euc-jp` entry

### Shift-JIS Family (flip JIS X 0213 branch; cp932 stays separate)

- **New primary:** `shift_jis_2004` (`python_codec="shift_jis_2004"`)
- **Aliases:** `shift_jis`, `sjis`, `shiftjis`, `s_jis`, `shift-jisx0213`
- **Replaces:** current `shift_jis` entry
- **cp932** remains its own entry (Microsoft extensions branch independently)

### ISO-2022-JP Family (three separate branch entries)

Currently one entry (`iso-2022-jp`). Split into three entries, one per branch:

1. **`iso2022-jp-2`** (multinational branch)
   - `python_codec="iso2022_jp_2"`
   - Aliases: `iso-2022-jp`, `csiso2022jp`, `iso2022-jp-1`
   - Handles: JIS X 0208, JIS X 0212, ISO 8859-1, ISO 8859-7, GB2312, KSC5601

2. **`iso2022-jp-2004`** (modern Japanese branch)
   - `python_codec="iso2022_jp_2004"`
   - Aliases: `iso2022-jp-3`
   - Handles: JIS X 0208, JIS X 0213:2004

3. **`iso2022-jp-ext`** (katakana branch)
   - `python_codec="iso2022_jp_ext"`
   - Aliases: *(none)*
   - Handles: JIS X 0208, JIS X 0212, half-width katakana (SI/SO)

### EBCDIC (flip)

- **New primary:** `cp1140` (`python_codec="cp1140"`)
- **Aliases:** `cp037`
- **Replaces:** current `cp037` entry (cp1140 = cp037 + euro sign at byte 0x9F)
- `cp500` remains its own entry (International Latin-1 EBCDIC, differs from cp037 at 7 positions)

### Thai (alias only)

- **Primary:** `tis-620` (unchanged)
- **New alias added:** `iso-8859-11`

## Pipeline Changes

### Escape Detector Enhancement (`escape.py`)

The escape detector currently returns `"iso-2022-jp"` for any ISO-2022 Japanese
escape sequence. Enhance it to differentiate between the three branch variants
by scanning for variant-specific escape codes:

| Escape codes detected            | Return encoding       |
|----------------------------------|-----------------------|
| `\x1b$(A`, `\x1b$(C`, `\x1b-A`, `\x1b-F` | `iso2022-jp-2`   |
| `\x1b$(O`, `\x1b$(P`            | `iso2022-jp-2004`     |
| SI/SO (0x0E/0x0F) for katakana   | `iso2022-jp-ext`      |
| Only base codes (`\x1b$B`, `\x1b$@`, `\x1b(J`) | `iso2022-jp-2` (default broadest) |

### Model Loading (`models/__init__.py`)

`get_enc_index()` builds an index from encoding name to model list. After
renaming entries (e.g., `big5` -> `big5hkscs`), model keys like `zh/big5` no
longer match the primary name.

Fix: when building the index, also check each registry entry's aliases. If
model key `zh/big5` exists and `big5` is an alias of `big5hkscs`, register the
model under `big5hkscs`.

### Equivalences (`equivalences.py`)

Update `SUPERSETS` to reflect new primary names. All broadest-per-branch
variants are acceptable detections of narrower subsets:

- `iso-2022-jp` expected -> `iso2022-jp-2`, `iso2022-jp-2004`, or
  `iso2022-jp-ext` all correct
- `big5` expected -> `big5hkscs` correct
- `euc-jp` expected -> `euc-jis-2004` correct
- `shift_jis` expected -> `shift_jis_2004` correct
- `cp037` expected -> `cp1140` correct

The three ISO-2022-JP branch variants should be bidirectionally equivalent
(detecting any branch when another was expected is acceptable, since they all
decode base ISO-2022-JP correctly).

## What Stays the Same

- **Statistical models:** No retraining. Bigram frequency data for `big5` is
  valid for `big5hkscs` (same byte patterns, broader character coverage).
- **Structural probing:** Works on byte patterns, not encoding names.
- **Validity checking:** Uses `python_codec` to try decoding. Broader codecs
  accept everything narrower ones did.
- **Other pipeline stages:** BOM, UTF-16/32, binary, markup, ASCII, UTF-8 are
  unaffected.

## Encoding Count

After this change:
- **Registry entries:** 84 current + 2 new ISO-2022-JP branches + 0 net new
  (15 added as aliases or replacements) = 86 entries
- **Python character encodings covered:** all of them (excluding transforms)
