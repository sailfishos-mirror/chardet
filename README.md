# chardet

Universal character encoding detector.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Documentation](https://readthedocs.org/projects/chardet/badge/?version=latest)](https://chardet.readthedocs.io)

chardet 7.0 is a ground-up, MIT-licensed rewrite of [chardet](https://github.com/chardet/chardet).
Same package name, same public API — drop-in replacement for chardet 5.x/6.x.
Python 3.10+, zero runtime dependencies, works on PyPy.

## Why chardet 7.0?

| Feature | chardet 7.0 | [charset-normalizer] |
|---|:---:|:---:|
| License | MIT | MIT |
| Streaming detection | **yes** | no |
| Encoding era filtering | **yes** | no |
| Detect spoken language | **yes** | yes |
| Byte-validity filtering | **yes** | yes |
| Native Python | **yes** | yes |
| Optional mypyc compilation | **yes** | yes |
| Supported encodings | 84 | 99 |

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
# {'encoding': 'Windows-1252', 'confidence': 1.0, 'language': 'pl'}

# UTF-8 with typographic punctuation
chardet.detect("It\u2019s a lovely day \u2014 let\u2019s grab coffee.".encode("utf-8"))
# {'encoding': 'utf-8', 'confidence': 0.99, 'language': 'hu'}

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
- **`EncodingEra` filtering** — scope detection to modern web encodings, legacy ISO/Mac/DOS, mainframe, or all
- **Optional mypyc compilation** for C-level performance on hot paths
- **Same API** — `detect()`, `detect_all()`, `UniversalDetector`, and the `chardetect` CLI all work as before

## Documentation

Full documentation is available at [chardet.readthedocs.io](https://chardet.readthedocs.io).

## License

[MIT](LICENSE)
