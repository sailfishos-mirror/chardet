# Restore Mark Pilgrim-era History — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Graft Mark Pilgrim's original chardet commits (2006–2009) into this repository via an orphan branch and `git replace` graft, preserving historical provenance without modifying any existing SHAs.

**Architecture:** Download the 1.0 PyPI sdist and clone `puzzlet/chardet` to extract Pilgrim's real commits. Build an orphan branch `history/pilgrim` with three commits (one synthetic, two real). Create a `git replace --graft` to connect David Cramer's first commit to the 1.0.1 Pilgrim commit. Add annotated tags. Verify rename detection works for `git blame`. Add documentation to README.

**Tech Stack:** git (low-level: `commit-tree`, `replace --graft`), curl, tar

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Modify | `README.md` | Add "Project History" section with graft fetch instructions |

No source code files are created or modified. All work is git plumbing.

---

### Task 1: Prepare Source Material

Download the chardet 1.0 sdist from PyPI and clone the puzzlet/chardet repo
that contains Mark Pilgrim's real git commits. All work happens in `/tmp`.

**Files:**
- Create: `/tmp/chardet-pilgrim-history/` (working directory)

- [ ] **Step 1: Create working directory and download chardet 1.0 sdist**

```bash
mkdir -p /tmp/chardet-pilgrim-history
curl -sL -o /tmp/chardet-pilgrim-history/chardet-1.0.tar.gz \
  https://files.pythonhosted.org/packages/source/c/chardet/chardet-1.0.tar.gz
```

Expected: File downloaded, ~153KB.

- [ ] **Step 2: Extract the sdist and verify contents**

```bash
mkdir /tmp/chardet-pilgrim-history/sdist-1.0
tar xzf /tmp/chardet-pilgrim-history/chardet-1.0.tar.gz \
  -C /tmp/chardet-pilgrim-history/sdist-1.0
ls /tmp/chardet-pilgrim-history/sdist-1.0/chardet-1.0/
```

Expected: Directory contains `chardet/` (with 35 `.py` files), `setup.py`, and `PKG-INFO`.

- [ ] **Step 3: Clone puzzlet/chardet**

```bash
git clone https://github.com/puzzlet/chardet.git \
  /tmp/chardet-pilgrim-history/puzzlet-chardet
```

Expected: Cloned repo with default branch `MarkPilgrim`.

- [ ] **Step 4: Verify the two Pilgrim commits exist and match expected SHAs**

```bash
git -C /tmp/chardet-pilgrim-history/puzzlet-chardet log \
  --format="%H %ai %an <%ae> %s" MarkPilgrim
```

Expected output (two commits, newest first):
```
0a848dc4d7291efb03252d8addaa635732694061 2009-11-10 17:29:46 +0300 Mark Pilgrim <mark@diveintomark.org> version 2.0.1
cd02f30a5104b479889a8fcba8e45a5b607571aa 2009-11-08 23:54:15 +0300 Mark Pilgrim <mark@diveintomark.org> moved project to Google Code
```

---

### Task 2: Create the Orphan Branch with Synthetic 1.0 Commit

Create the `history/pilgrim` orphan branch in the chardet repo. The first
commit is synthetic, built from the PyPI sdist with Mark Pilgrim as author
and Dan Blanchard as committer.

**Files:**
- Create: branch `history/pilgrim` in `/Users/danblanchard/repos/chardet`

- [ ] **Step 1: Prepare a clean staging area for the 1.0 tree**

Create a temporary directory with only the files we want in the commit
(`chardet/` package + `setup.py`, no `PKG-INFO`):

```bash
mkdir -p /tmp/chardet-pilgrim-history/tree-1.0
cp -r /tmp/chardet-pilgrim-history/sdist-1.0/chardet-1.0/chardet \
  /tmp/chardet-pilgrim-history/tree-1.0/
cp /tmp/chardet-pilgrim-history/sdist-1.0/chardet-1.0/setup.py \
  /tmp/chardet-pilgrim-history/tree-1.0/
ls /tmp/chardet-pilgrim-history/tree-1.0/
```

Expected: `chardet/` directory and `setup.py`.

- [ ] **Step 2: Build a git tree object from the 1.0 source**

Use a temporary git index to create the tree object inside the chardet repo:

```bash
cd /Users/danblanchard/repos/chardet

# Use a temporary index to avoid touching the working tree
export GIT_INDEX_FILE=$(mktemp)

# Add all files from the 1.0 tree
git --work-tree=/tmp/chardet-pilgrim-history/tree-1.0 add -A

# Write the tree object
TREE_1_0=$(git write-tree)
echo "Tree SHA: $TREE_1_0"

# Clean up temp index
rm "$GIT_INDEX_FILE"
unset GIT_INDEX_FILE
```

Expected: A tree SHA is printed.

- [ ] **Step 3: Create the synthetic 1.0 commit**

```bash
cd /Users/danblanchard/repos/chardet

COMMIT_1_0=$(
  GIT_AUTHOR_NAME="Mark Pilgrim" \
  GIT_AUTHOR_EMAIL="mark@diveintomark.org" \
  GIT_AUTHOR_DATE="2006-12-23T00:00:00+0000" \
  git commit-tree "$TREE_1_0" -m "$(cat <<'COMMITMSG'
chardet 1.0

Initial release of chardet, a Python port of Mozilla's universal
charset detection library.

[Reconstructed from PyPI sdist: chardet-1.0.tar.gz]
COMMITMSG
)"
)
echo "Commit 1 (1.0): $COMMIT_1_0"
```

The committer name/email/date are taken from the current git config and
current time (this is the desired behavior — Dan Blanchard as committer).

Expected: A commit SHA is printed. This is a root commit (no parent).

- [ ] **Step 4: Create the orphan branch pointing to this commit**

```bash
git -C /Users/danblanchard/repos/chardet branch history/pilgrim "$COMMIT_1_0"
```

Expected: Branch created. Verify with:

```bash
git -C /Users/danblanchard/repos/chardet log history/pilgrim --oneline
```

Should show one commit.

- [ ] **Step 5: Verify the commit metadata**

```bash
git -C /Users/danblanchard/repos/chardet log history/pilgrim \
  --format="Author: %an <%ae> %ai%nCommitter: %cn <%ce> %ci%nMessage: %s"
```

Expected:
- Author: Mark Pilgrim, date 2006-12-23
- Committer: Dan Blanchard, date today
- Message: "chardet 1.0"

---

### Task 3: Add the Real Pilgrim Commits to the Orphan Branch

Recreate Pilgrim's two real commits from `puzzlet/chardet` on top of the
synthetic 1.0 commit, preserving exact trees, authorship, and timestamps.

We use `git commit-tree` with the original tree SHAs (which we import via
a fetch) rather than cherry-pick, because the originals are root commits
and cherry-pick would not produce the exact same tree.

- [ ] **Step 1: Fetch puzzlet/chardet objects into the chardet repo**

```bash
git -C /Users/danblanchard/repos/chardet remote add puzzlet \
  https://github.com/puzzlet/chardet.git
git -C /Users/danblanchard/repos/chardet fetch puzzlet MarkPilgrim
```

Expected: Objects fetched. The tree objects from Pilgrim's commits are now
available locally.

- [ ] **Step 2: Extract the original commit metadata**

```bash
# Commit 2 (1.0.1 / "moved project to Google Code")
git -C /Users/danblanchard/repos/chardet cat-file -p cd02f30a5104b479889a8fcba8e45a5b607571aa

# Commit 3 (unreleased 2.0.1)
git -C /Users/danblanchard/repos/chardet cat-file -p 0a848dc4d7291efb03252d8addaa635732694061
```

Expected: Shows tree SHAs, author/committer lines with dates. Record these:
- Commit 2 tree: `644dda9b145501b6f134d3c626e6cf812f63adf7`
- Commit 2 author date: `2009-11-08 23:54:15 +0300`
- Commit 3 tree: `57982f45f7e68d7484c6d49704b0a143452bd8ec`
- Commit 3 author date: `2009-11-10 17:29:46 +0300`

- [ ] **Step 3: Create commit 2 with commit 1 as parent**

Use the original tree, author, date, and message. Set both author AND
committer to Mark Pilgrim (these are real commits, not synthetic):

```bash
cd /Users/danblanchard/repos/chardet

COMMIT_1_0_1=$(
  GIT_AUTHOR_NAME="Mark Pilgrim" \
  GIT_AUTHOR_EMAIL="mark@diveintomark.org" \
  GIT_AUTHOR_DATE="2009-11-08 23:54:15 +0300" \
  GIT_COMMITTER_NAME="Mark Pilgrim" \
  GIT_COMMITTER_EMAIL="mark@diveintomark.org" \
  GIT_COMMITTER_DATE="2009-11-08 23:54:15 +0300" \
  git commit-tree 644dda9b145501b6f134d3c626e6cf812f63adf7 \
    -p "$COMMIT_1_0" \
    -m "moved project to Google Code"
)
echo "Commit 2 (1.0.1): $COMMIT_1_0_1"
```

Expected: A new commit SHA (different from the puzzlet original because it
has a parent now).

- [ ] **Step 4: Create commit 3 with commit 2 as parent**

```bash
cd /Users/danblanchard/repos/chardet

COMMIT_2_0_1=$(
  GIT_AUTHOR_NAME="Mark Pilgrim" \
  GIT_AUTHOR_EMAIL="mark@diveintomark.org" \
  GIT_AUTHOR_DATE="2009-11-10 17:29:46 +0300" \
  GIT_COMMITTER_NAME="Mark Pilgrim" \
  GIT_COMMITTER_EMAIL="mark@diveintomark.org" \
  GIT_COMMITTER_DATE="2009-11-10 17:29:46 +0300" \
  git commit-tree 57982f45f7e68d7484c6d49704b0a143452bd8ec \
    -p "$COMMIT_1_0_1" \
    -m "version 2.0.1"
)
echo "Commit 3 (unreleased-2.0.1): $COMMIT_2_0_1"
```

Expected: A new commit SHA.

- [ ] **Step 5: Update the orphan branch to point to commit 3 (the tip)**

```bash
git -C /Users/danblanchard/repos/chardet update-ref refs/heads/history/pilgrim "$COMMIT_2_0_1"
```

- [ ] **Step 6: Verify the full branch history**

```bash
git -C /Users/danblanchard/repos/chardet log history/pilgrim \
  --format="%h %ai %an - %s" --reverse
```

Expected (three commits, oldest first):
```
<sha1> 2006-12-23 00:00:00 +0000 Mark Pilgrim - chardet 1.0
<sha2> 2009-11-08 23:54:15 +0300 Mark Pilgrim - moved project to Google Code
<sha3> 2009-11-10 17:29:46 +0300 Mark Pilgrim - version 2.0.1
```

- [ ] **Step 7: Remove the puzzlet remote (no longer needed)**

```bash
git -C /Users/danblanchard/repos/chardet remote remove puzzlet
```

---

### Task 4: Create Annotated Tags

Create annotated tags on each of the three commits. Tag dates for 1.0 and
1.0.1 use the PyPI release dates, not the git commit dates.

- [ ] **Step 1: Tag the synthetic 1.0 commit**

```bash
cd /Users/danblanchard/repos/chardet

GIT_COMMITTER_DATE="2006-12-23T00:00:00+0000" \
  git tag -a "1.0" "$COMMIT_1_0" -m "chardet 1.0 (2006-12-23)"
```

- [ ] **Step 2: Tag the 1.0.1 commit**

The tag date uses the PyPI release date (2008-04-19), not the commit date
(2009-11-08), because 1.0.1 was released on PyPI well before Mark moved
the project to Google Code.

```bash
cd /Users/danblanchard/repos/chardet

GIT_COMMITTER_DATE="2008-04-19T00:00:00+0000" \
  git tag -a "1.0.1" "$COMMIT_1_0_1" -m "chardet 1.0.1 (2008-04-19)"
```

- [ ] **Step 3: Tag the unreleased 2.0.1 commit**

```bash
cd /Users/danblanchard/repos/chardet

GIT_COMMITTER_DATE="2009-11-10T17:29:46+0300" \
  git tag -a "unreleased-2.0.1" "$COMMIT_2_0_1" \
    -m "chardet 2.0.1 (unreleased, never published to PyPI)"
```

- [ ] **Step 4: Verify all three tags**

```bash
git -C /Users/danblanchard/repos/chardet tag -l --sort=creatordate \
  "1.0" "1.0.1" "unreleased-2.0.1"
git -C /Users/danblanchard/repos/chardet show 1.0 --quiet
git -C /Users/danblanchard/repos/chardet show 1.0.1 --quiet
git -C /Users/danblanchard/repos/chardet show unreleased-2.0.1 --quiet
```

Expected: Three tags listed. Each `show` displays the tag message and
points to the correct commit.

---

### Task 5: Create the Graft

Connect the current repo's root commit (David Cramer, 2011-10-25) to the
1.0.1 Pilgrim commit so `git log` shows continuous history.

- [ ] **Step 1: Create the graft**

The graft targets commit 2 (1.0.1), not commit 3 (unreleased 2.0.1),
because Cramer's code descends from the 1.0.1 source.

```bash
git -C /Users/danblanchard/repos/chardet replace --graft \
  0526d2e0dfd284a064868d1e865801e047c1b545 "$COMMIT_1_0_1"
```

Expected: No output (success).

- [ ] **Step 2: Verify the graft — git log should show Pilgrim commits**

```bash
git -C /Users/danblanchard/repos/chardet log --oneline --reverse | head -10
```

Expected: The first commits shown should be the three Pilgrim-era commits,
followed by Cramer's commits:
```
<sha1> chardet 1.0
<sha2> moved project to Google Code
<sha3> version 2.0.1
0526d2e Initial commit with fix for utf8prober when char is out of range
6b2f4fa Clean up a bunch of detection logic to fail gracefully
...
```

Wait — commit 3 (unreleased-2.0.1) should NOT appear in the main lineage.
The graft connects Cramer's commit to commit 2, not commit 3. So commit 3
is a dangling tip on the orphan branch. Verify:

```bash
git -C /Users/danblanchard/repos/chardet log --oneline --reverse | head -5
```

Expected:
```
<sha1> chardet 1.0
<sha2> moved project to Google Code
0526d2e Initial commit with fix for utf8prober when char is out of range
6b2f4fa Clean up a bunch of detection logic to fail gracefully
...
```

Only commits 1 and 2 from Pilgrim appear in the main lineage. Commit 3
is reachable only via `history/pilgrim`.

---

### Task 6: Verify Rename Detection

Confirm that `git blame` follows file renames from `src-python2/chardet/`
(Pilgrim's tree) to `chardet/` (Cramer's tree) across the graft boundary.

- [ ] **Step 1: Test git blame on a file that existed in Pilgrim's 1.0**

```bash
git -C /Users/danblanchard/repos/chardet blame \
  0526d2e -- chardet/__init__.py | head -5
```

Expected: If rename detection works, some lines should be attributed to
Mark Pilgrim with 2009 dates (from the 1.0.1 commit where the file lived
at `src-python2/chardet/__init__.py`).

If all lines show David Cramer, rename detection is not following across
the directory restructuring.

- [ ] **Step 2: Try aggressive rename detection if needed**

```bash
git -C /Users/danblanchard/repos/chardet blame -C -C \
  0526d2e -- chardet/__init__.py | head -5
```

The `-C -C` flag enables cross-file copy detection, which should catch the
`src-python2/chardet/` → `chardet/` move.

- [ ] **Step 3: Document findings**

Record whether rename detection works out of the box, requires `-C -C`, or
does not work at all. This information goes into the README documentation
added in Task 7.

---

### Task 7: Add Documentation to README

Add a "Project History" section to `README.md` explaining the Pilgrim-era
history and how to enable the graft.

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add a Project History section to README.md**

Add the following section before the `## License` section at the end of
`README.md`:

````markdown
## Project History

chardet was originally created by [Mark Pilgrim](https://en.wikipedia.org/wiki/Mark_Pilgrim)
in 2006 as a Python port of [Mozilla's universal charset detection library](https://www-archive.mozilla.org/projects/intl/chardet.html).
He released versions 1.0 (2006) and 1.0.1 (2008) on PyPI, then developed
an unreleased Python 3 port (2.0.1) on Google Code. After Mark
[deleted his online accounts](https://en.wikipedia.org/wiki/Mark_Pilgrim#%22Infocide%22)
in 2011, the project was continued by David Cramer, Erik Rose, Dan Blanchard,
and Ian Cordasco.

The `history/pilgrim` branch preserves Mark's original commits. To see
the full history from 2006 to present in `git log`, fetch the graft refs:

```
git fetch origin 'refs/replace/*:refs/replace/*'
```
````

- [ ] **Step 2: Verify README renders correctly**

Visually inspect the markdown. Ensure the nested code block renders properly
(the inner block uses triple backticks inside the outer markdown — may need
adjustment to use indented code block or different fence characters).

- [ ] **Step 3: Commit the README change**

```bash
git -C /Users/danblanchard/repos/chardet add README.md
git -C /Users/danblanchard/repos/chardet commit -m "docs: add Project History section with Pilgrim-era graft instructions"
```

---

### Task 8: Push Everything

Push the orphan branch, tags, and graft refs to the remote. All operations
are additive — no force push required.

- [ ] **Step 1: Push the orphan branch**

```bash
git -C /Users/danblanchard/repos/chardet push origin history/pilgrim
```

- [ ] **Step 2: Push the tags**

```bash
git -C /Users/danblanchard/repos/chardet push origin 1.0 1.0.1 unreleased-2.0.1
```

- [ ] **Step 3: Push the graft refs**

```bash
git -C /Users/danblanchard/repos/chardet push origin 'refs/replace/*'
```

- [ ] **Step 4: Push the README commit**

```bash
git -C /Users/danblanchard/repos/chardet push origin main
```

- [ ] **Step 5: Verify on a fresh clone**

```bash
cd /tmp
git clone git@github.com:chardet/chardet.git chardet-verify
cd chardet-verify

# Verify orphan branch exists
git branch -a | grep history/pilgrim

# Verify tags exist
git tag -l "1.0" "1.0.1" "unreleased-2.0.1"

# Verify graft is NOT active by default
git log --oneline --reverse | head -3
# Should show Cramer's commit first (no Pilgrim history)

# Enable graft and verify
git fetch origin 'refs/replace/*:refs/replace/*'
git log --oneline --reverse | head -5
# Should now show Pilgrim commits first

# Clean up
rm -rf /tmp/chardet-verify
```

---

### Task 9: Clean Up

Remove temporary files created during the process.

- [ ] **Step 1: Remove working directory**

```bash
rm -rf /tmp/chardet-pilgrim-history
```
