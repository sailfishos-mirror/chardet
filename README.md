# chardet

Universal character encoding detector -- MIT-licensed rewrite of [chardet](https://github.com/chardet/chardet).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This is a drop-in replacement for chardet 6.x with the same package name and public API.
Python 3.10+, zero runtime dependencies.

## Installation

```bash
pip install chardet
```

## Usage

```python
import chardet

# Detect encoding of a byte string
result = chardet.detect(b"\xc0\xc1\xc2")
print(result)
# {'encoding': '...', 'confidence': 0.99, 'language': '...'}

# Get all candidate encodings
results = chardet.detect_all(b"\xc0\xc1\xc2")
```

## CLI

```bash
chardetect somefile.txt
chardetect --all somefile.txt
```

## License

[MIT](LICENSE)
