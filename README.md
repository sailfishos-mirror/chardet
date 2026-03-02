# chardet

Universal character encoding detector.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Documentation](https://readthedocs.org/projects/chardet/badge/?version=latest)](https://chardet.readthedocs.io)

chardet 7.0 is a ground-up, MIT-licensed rewrite of [chardet](https://github.com/chardet/chardet).
Same package name, same public API — drop-in replacement for chardet 5.x/6.x.
Python 3.10+, zero runtime dependencies, works on PyPy.

## Why chardet 7.0?

**96.6% accuracy** on 2,161 test files. **27x faster** than chardet 6.0.0.
**5x faster** than charset-normalizer. **Language detection** for every
result. **MIT licensed.**

| | chardet 7.0 | chardet 6.0.0 | [charset-normalizer] |
|---|:---:|:---:|:---:|
| Accuracy (2,161 files) | **96.6%** | 94.5% | 89.0% |
| Speed (pure Python) | **334 files/s** | 12 files/s | 66 files/s |
| Language detection | **90.9%** | 47.0% | -- |
| Peak memory | **22.5 MiB** | 16.4 MiB | 102.2 MiB |
| Streaming detection | **yes** | yes | no |
| Encoding era filtering | **yes** | no | no |
| Supported encodings | 99 | 84 | 99 |
| Optional mypyc compilation | **yes** | no | yes |
| License | MIT | LGPL | MIT |

[charset-normalizer]: https://github.com/jawah/charset_normalizer

## Installation

```bash
pip install chardet
```

## Quick Start

```python
import chardet

# Plain ASCII is reported as its superset Windows-1252 by default
chardet.detect(b"Hello, world!")
# {'encoding': 'Windows-1252', 'confidence': 1.0, 'language': 'en'}

# UTF-8 with typographic punctuation
chardet.detect("It\u2019s a lovely day \u2014 let\u2019s grab coffee.".encode("utf-8"))
# {'encoding': 'utf-8', 'confidence': 0.99, 'language': 'es'}

# Japanese EUC-JP
chardet.detect("これは日本語のテストです。文字コードの検出を行います。".encode("euc-jp"))
# {'encoding': 'euc-jp', 'confidence': 1.0, 'language': 'ja'}

# Get all candidate encodings ranked by confidence
text = "Le café est une boisson très populaire en France et dans le monde entier."
results = chardet.detect_all(text.encode("windows-1252"))
for r in results:
    print(r["encoding"], r["confidence"])
# windows-1252 0.44
# windows-1250 0.32
# windows-1254 0.27
# windows-1257 0.25
```

### Streaming Detection

For large files or network streams, use `UniversalDetector` to feed data incrementally:

```python
from chardet import UniversalDetector

detector = UniversalDetector()
with open("unknown.txt", "rb") as f:
    for line in f:
        detector.feed(line)
        if detector.done:
            break
result = detector.close()
print(result)
```

### Encoding Era Filtering

Restrict detection to specific encoding eras to reduce false positives:

```python
from chardet import detect
from chardet.enums import EncodingEra

# Only consider modern web encodings (the default)
detect("Cześć, jak się masz? Dziękuję bardzo za pomoc.".encode("utf-8"))
# {'encoding': 'utf-8', 'confidence': 0.99, 'language': 'pl'}

# Include legacy encodings too
detect("Η Αθήνα είναι η πρωτεύουσα και μεγαλύτερη πόλη της Ελλάδας.".encode("iso-8859-7"),
       encoding_era=EncodingEra.ALL)
# {'encoding': 'iso-8859-7', 'confidence': 0.52, 'language': 'el'}
```

## CLI

```bash
chardetect somefile.txt
# somefile.txt: utf-8 with confidence 0.99

chardetect --minimal somefile.txt
# utf-8

# Include legacy encodings
chardetect --legacy somefile.txt

# Pipe from stdin
cat somefile.txt | chardetect
```

## What's New in 7.0

- **MIT license** (previous versions were LGPL)
- **Ground-up rewrite** — 11-stage detection pipeline using BOM detection, structural probing, byte validity filtering, and bigram statistical models
- **27x faster** than chardet 6.0.0, **5x faster** than charset-normalizer (pure Python)
- **96.6% accuracy** — +2.1pp vs chardet 6.0.0, +7.6pp vs charset-normalizer
- **Language detection** — 90.9% accuracy across 48 languages, returned with every result
- **99 encodings** — full coverage including EBCDIC, Mac, DOS, and Baltic/Central European families
- **`EncodingEra` filtering** — scope detection to modern web encodings, legacy ISO/Mac/DOS, mainframe, or all
- **Optional mypyc compilation** — 1.45x additional speedup on CPython
- **Thread-safe** — `detect()` and `detect_all()` are safe to call concurrently; scales on free-threaded Python
- **Same API** — `detect()`, `detect_all()`, `UniversalDetector`, and the `chardetect` CLI all work as before

## Documentation

Full documentation is available at [chardet.readthedocs.io](https://chardet.readthedocs.io).

## License

[MIT](LICENSE)
