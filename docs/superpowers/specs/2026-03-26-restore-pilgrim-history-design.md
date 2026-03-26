# Restore Mark Pilgrim-era History

## Summary

Recover and graft Mark Pilgrim's original chardet commits (2006-2009) into
this repository for historical record-keeping. The Pilgrim-era code predates
David Cramer's 2011 fork that became `chardet/chardet`. We use a hybrid
approach: an orphan branch stores the commits durably, and a `git replace`
graft makes `git log` show continuous history from 2006 to present.

No existing SHAs change. No force push required. Purely additive.

## Background

Mark Pilgrim created chardet as a Python port of Mozilla's universal charset
detection library. He released versions 1.0 (2006-12-23) and 1.0.1
(2008-04-19) on PyPI, then moved the project to Google Code in November 2009
where he restructured it into Python 2 and Python 3 source trees (version
2.0.1, never released to PyPI). In October 2011, Pilgrim deleted all his
online accounts ("infosuicide"). David Cramer created a new GitHub repo from
the 1.0.1 source with a bug fix, which became the basis for the current
`chardet/chardet` repository.

### Surviving sources

| Source | Contents | Status |
|--------|----------|--------|
| PyPI `chardet-1.0.tar.gz` | Full sdist of 1.0 release | Still downloadable |
| PyPI `chardet-1.0.1.tar.gz` | Full sdist of 1.0.1 release | Still downloadable |
| `puzzlet/chardet` GitHub repo, `MarkPilgrim` branch | Two real git commits by Mark Pilgrim (2009-11-08, 2009-11-10) with the Google Code project contents | Still available |
| Google Code SVN dump | Original SVN history | 403 Forbidden (lost) |

### What changed between versions

**1.0 -> 1.0.1** (3 files changed):
- `setup.py`: `distutils.core` -> `setuptools`, version bump
- `chardet/__init__.py`: version string update
- `chardet/escsm.py`: ISO2022JP char length table corrected from 8 to 10 entries
- `chardet/universaldetector.py`: UTF-16 LE BOM check fixed (`aBuf[:4]` -> `aBuf[:2]`)

**1.0.1 -> Cramer's first commit** (1 file changed + restructuring):
- `chardet/codingstatemachine.py`: Added try/except IndexError guard for out-of-range chars
- Extracted `src-python2/chardet/` to top-level `chardet/`
- Dropped website, tarballs, tests, Makefile, py3 source
- Added `.gitignore`, `setup.cfg`, new `setup.py`

## Design

### Orphan branch: `history/pilgrim`

Three commits, oldest to newest:

| # | Type | Date | Author | Committer | Tag |
|---|------|------|--------|-----------|-----|
| 1 | Synthetic | 2006-12-23 | Mark Pilgrim `<mark@diveintomark.org>` | Dan Blanchard | `1.0` |
| 2 | Real | 2009-11-08 | Mark Pilgrim `<mark@diveintomark.org>` | Mark Pilgrim `<mark@diveintomark.org>` | `1.0.1` |
| 3 | Real | 2009-11-10 | Mark Pilgrim `<mark@diveintomark.org>` | Mark Pilgrim `<mark@diveintomark.org>` | `unreleased-2.0.1` |

#### Commit 1: chardet 1.0 (synthetic)

Created from the PyPI sdist `chardet-1.0.tar.gz`. Contents:
- `chardet/` package source (all `.py` files)
- `setup.py`

Excluded: `PKG-INFO` (packaging artifact; the full sdist remains on PyPI).

Commit message:
```
chardet 1.0

Initial release of chardet, a Python port of Mozilla's universal
charset detection library.

[Reconstructed from PyPI sdist: chardet-1.0.tar.gz]
```

Author: `Mark Pilgrim <mark@diveintomark.org>` (GIT_AUTHOR_NAME/EMAIL)
Committer: `Dan Blanchard <dan.blanchard@gmail.com>` (GIT_COMMITTER_NAME/EMAIL)
Author date: 2006-12-23 (GIT_AUTHOR_DATE)
Committer date: current date (GIT_COMMITTER_DATE)

#### Commits 2 and 3: Real Pilgrim commits

Taken from `puzzlet/chardet` `MarkPilgrim` branch (`cd02f30` and `0a848dc`).
Trees preserved exactly as-is (includes website, download tarballs, docbook
XML, etc.). Author, author date, and commit messages preserved verbatim.

Commit 2 is created with commit 1 as its parent (replacing the original root
commit status). The tree is taken directly from the original commit object —
not cherry-picked — to ensure exact content preservation.

Commit 3 is created with commit 2 as its parent, same approach.

### Graft

```
git replace --graft 0526d2e <commit-2-sha>
```

This makes David Cramer's first commit (2011-10-25, `0526d2e`) appear to have
the 1.0.1 commit (commit 2) as its parent. The graft points to commit 2, not
commit 3, because Cramer's code descends from the 1.0.1 source, not the
unreleased 2.0.1 py2/py3 restructuring.

### Tags

| Tag | Points to | Annotated? |
|-----|-----------|------------|
| `1.0` | Commit 1 | Yes — message: `chardet 1.0 (2006-12-23)` |
| `1.0.1` | Commit 2 | Yes — message: `chardet 1.0.1 (2008-04-19)` |
| `unreleased-2.0.1` | Commit 3 | Yes — message: `chardet 2.0.1 (unreleased, never published to PyPI)` |

Note: The `1.0.1` tag date uses the PyPI release date (2008-04-19), not the
git commit date (2009-11-08), since the commit represents "moved project to
Google Code" which happened later. The tag message clarifies the actual release
date.

### Push plan

All operations are additive — no force push:

```bash
git push origin history/pilgrim          # orphan branch
git push origin 1.0 1.0.1 unreleased-2.0.1  # tags
git push origin 'refs/replace/*'         # graft refs
```

### Rename detection verification

After creating the graft, verify that `git blame` follows file renames from
`src-python2/chardet/` to `chardet/` across the graft boundary:

```bash
git blame 0526d2e -- chardet/__init__.py
```

If rename detection doesn't work automatically, try `git blame -C -C` for more
aggressive detection. Document findings and any required workarounds.

### Documentation

Add a section to `README.rst` (or `CONTRIBUTING.md` if more appropriate)
explaining:

1. That the repo contains historical commits from Mark Pilgrim's original work
2. How to enable the graft for seamless `git log`:
   ```
   git fetch origin 'refs/replace/*:refs/replace/*'
   ```
3. That the `history/pilgrim` branch can be browsed directly for the
   Pilgrim-era code

## Out of scope

- Recovering the Google Code SVN history (the dump returns 403)
- Modifying any existing commits or SHAs
- Synthesizing intermediate commits between known releases
- Any changes to the current codebase
