# Session-aware Stop hook — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Teach `cc-repo-hygiene-hook.py` to distinguish dirty files Claude touched this session (block, as today) from dirty files left by prior sessions (warn on stderr, exit 0).

**Architecture:** Read the transcript at `transcript_path` from the Stop hook input. Build a set of paths touched by `Edit` / `Write` / `NotebookEdit` tool_uses, plus any path that appears as a substring in `Bash` commands (conservative — errs toward "this session"). Partition the dirty paths from git status against that set. Touched → existing block path. Untouched → stderr warning. Fail closed on any transcript error.

**Tech Stack:** Python 3, subprocess for git, pytest for tests. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-20-stop-hook-session-aware-design.md`

---

## File Structure

**Modify:** `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py`
- Add two helpers: `_read_transcript_tool_uses()` and `_classify_paths()`.
- Replace Checks 1–3 (staged / unstaged / untracked) with a path-enumerating version that partitions each bucket by session origin, feeds the this-session bucket into `violations` (existing block path), and collects the prior-session bucket into a `warnings` list.
- At the end of `main()`, emit any warnings to stderr regardless of whether we block.

**Create:** `claude-optimizing/tests/test_session_aware_hook.py`
- Integration tests using the existing `local_git_repo` fixture. Synthesizes JSONL transcripts, invokes the hook as a subprocess, asserts the block/warn output shape.

No other files change.

---

## Task 1: Enumerate dirty paths (refactor, no behavior change)

**Files:**
- Modify: `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py` (Checks 1–3 at lines 159–173)

Checks 1–3 currently use `git diff --quiet` and `ls-files --others` with only a count. We need the actual paths so the classifier can partition them. This task only switches to enumeration — the violation messages are updated to include paths, but no classification yet.

- [ ] **Step 1: Update Checks 1–3 to enumerate paths**

Replace lines 159–173 of `cc-repo-hygiene-hook.py`:

```python
    # Check 1: Staged changes
    out, _ = run(["git", "-C", cwd, "diff", "--cached", "--name-only"])
    staged_paths = [p for p in out.splitlines() if p]
    if staged_paths:
        violations.append(
            "Staged changes not committed: " + ", ".join(staged_paths)
        )

    # Check 2: Unstaged changes
    out, _ = run(["git", "-C", cwd, "diff", "--name-only"])
    unstaged_paths = [p for p in out.splitlines() if p]
    if unstaged_paths:
        violations.append(
            "Unstaged changes to tracked files: " + ", ".join(unstaged_paths)
        )

    # Check 3: Untracked files
    out, _ = run(["git", "-C", cwd, "ls-files", "--others", "--exclude-standard"])
    untracked_paths = [p for p in out.splitlines() if p]
    if untracked_paths:
        violations.append(
            f"{len(untracked_paths)} untracked file(s) not in .gitignore: "
            + ", ".join(untracked_paths)
        )
```

- [ ] **Step 2: Run existing hook tests — confirm they still pass**

Run: `cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/stop-hook-session-aware/claude-optimizing && pytest tests/test_repo_hygiene_hook.py -v`
Expected: PASS. This test exercises Check 5b (orphan remote branch), not Checks 1–3, so it must still pass.

- [ ] **Step 3: Commit**

```bash
git add claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py
git commit -m "stop-hook: enumerate dirty paths in Checks 1-3

No behavior change in classification — still blocks all dirty paths.
Enumeration prep for session-origin partitioning in the next commit.
"
```

---

## Task 2: Add `_read_transcript_tool_uses()` helper

**Files:**
- Modify: `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py` (add helper near top)

Claude Code transcripts are JSONL. Each assistant message contains a `content` list; tool_use blocks have `type == "tool_use"`, a `name`, and an `input` dict. Extract `file_path` from `Edit`/`Write`/`NotebookEdit` and `command` strings from `Bash`.

- [ ] **Step 1: Add the helper above `_find_squash_merged_orphans`**

Insert after line 20 (after `run()`):

```python
def _read_transcript_tool_uses(transcript_path):
    """Return (edit_paths, bash_commands) from the Claude Code transcript.

    edit_paths: set of absolute paths from Edit / Write / NotebookEdit
        tool_use file_path inputs.
    bash_commands: list of command strings from Bash tool_use inputs.

    Returns (None, None) on any failure (missing file, IO error, malformed
    JSON line, or unexpected structure). Callers treat None as "fail
    closed" — classify every dirty path as this-session.
    """
    if not transcript_path:
        return None, None
    try:
        edit_paths = set()
        bash_commands = []
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    return None, None
                msg = obj.get("message") or {}
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue
                    name = block.get("name")
                    inp = block.get("input") or {}
                    if not isinstance(inp, dict):
                        continue
                    if name in ("Edit", "Write", "NotebookEdit"):
                        fp = inp.get("file_path")
                        if isinstance(fp, str) and fp:
                            edit_paths.add(os.path.realpath(fp))
                    elif name == "Bash":
                        cmd = inp.get("command")
                        if isinstance(cmd, str) and cmd:
                            bash_commands.append(cmd)
        return edit_paths, bash_commands
    except (OSError, IOError):
        return None, None
```

- [ ] **Step 2: Quick smoke test in the REPL**

Run:

```bash
cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/stop-hook-session-aware
python3 -c "
import sys, json, tempfile, os
sys.path.insert(0, 'claude-optimizing/scripts-hooks')
# Load via importlib since the file has a hyphen
import importlib.util
spec = importlib.util.spec_from_file_location('hook', 'claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

tmp = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False)
tmp.write(json.dumps({'message': {'content': [{'type': 'tool_use', 'name': 'Write', 'input': {'file_path': '/tmp/foo.py'}}]}}) + '\n')
tmp.write(json.dumps({'message': {'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'git add bar.py'}}]}}) + '\n')
tmp.close()
ep, bc = m._read_transcript_tool_uses(tmp.name)
os.unlink(tmp.name)
print('edit_paths:', ep)
print('bash_commands:', bc)
assert '/tmp/foo.py' in ep or os.path.realpath('/tmp/foo.py') in ep
assert any('bar.py' in c for c in bc)
print('OK')
"
```

Expected:
```
edit_paths: {'/private/tmp/foo.py'}   # or /tmp/foo.py depending on symlink
bash_commands: ['git add bar.py']
OK
```

- [ ] **Step 3: Commit**

```bash
git add claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py
git commit -m "stop-hook: add _read_transcript_tool_uses helper

Parses Claude Code JSONL transcripts and extracts the Edit/Write/
NotebookEdit file_path inputs plus Bash command strings. Returns
(None, None) on any failure so callers can fail closed.
"
```

---

## Task 3: Add `_classify_paths()` helper

**Files:**
- Modify: `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py` (add helper below the one from Task 2)

Partitions a list of repo-relative paths into (touched, untouched) based on the transcript data. Bash matching checks both the relative and absolute forms of each path.

- [ ] **Step 1: Add the helper**

Insert after `_read_transcript_tool_uses`:

```python
def _classify_paths(rel_paths, cwd, edit_paths, bash_commands):
    """Partition repo-relative paths into (touched, untouched) by session.

    A path is "touched" by the current session if:
      - its absolute form appears in edit_paths (from Edit/Write/
        NotebookEdit tool_use file_path inputs), OR
      - its relative form or absolute form appears as a substring in any
        Bash command string.

    The Bash substring check is intentionally loose: false positives
    (warn-eligible paths promoted to block) are safe; false negatives
    (Claude-touched paths demoted to warn) would let real session dirt
    slip past Stop with only a warning, which is the dangerous direction.
    """
    touched, untouched = [], []
    for rel in rel_paths:
        abs_path = os.path.realpath(os.path.join(cwd, rel))
        is_touched = abs_path in edit_paths
        if not is_touched:
            for cmd in bash_commands:
                if rel in cmd or abs_path in cmd:
                    is_touched = True
                    break
        if is_touched:
            touched.append(rel)
        else:
            untouched.append(rel)
    return touched, untouched
```

- [ ] **Step 2: Smoke test**

```bash
cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/stop-hook-session-aware
python3 -c "
import importlib.util, os
spec = importlib.util.spec_from_file_location('hook', 'claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

cwd = '/tmp'
edit_paths = {os.path.realpath('/tmp/foo.py')}
bash_commands = ['sed -i s/x/y/ bar.py', 'echo hi']
touched, untouched = m._classify_paths(['foo.py', 'bar.py', 'baz.py'], cwd, edit_paths, bash_commands)
print('touched:', touched)
print('untouched:', untouched)
assert touched == ['foo.py', 'bar.py']
assert untouched == ['baz.py']
print('OK')
"
```

Expected:
```
touched: ['foo.py', 'bar.py']
untouched: ['baz.py']
OK
```

- [ ] **Step 3: Commit**

```bash
git add claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py
git commit -m "stop-hook: add _classify_paths helper

Partitions dirty paths into this-session vs prior-session based on
the Edit/Write/NotebookEdit and Bash tool_use data extracted from
the transcript.
"
```

---

## Task 4: Wire classification into Checks 1–3

**Files:**
- Modify: `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py` (replace the enumeration from Task 1 with classification-aware versions; add stderr emit near end)

- [ ] **Step 1: Read the transcript once, before Checks 1–3**

Find the lines added in Task 1 (Checks 1–3). Immediately before them, add:

```python
    transcript_path = input_json.get("transcript_path") or ""
    edit_paths, bash_commands = _read_transcript_tool_uses(transcript_path)
    classify_enabled = edit_paths is not None
    warnings = []
```

- [ ] **Step 2: Add a small helper inline in `main()`**

Just before the `violations = []` line, add this closure (so it has access to the locals):

```python
    def _split(rel_paths):
        """Return (this_session, prior_session) for a list of dirty paths.
        If classification is disabled (transcript unreadable), fail closed:
        treat everything as this-session."""
        if not classify_enabled:
            return rel_paths, []
        return _classify_paths(rel_paths, cwd, edit_paths, bash_commands)
```

- [ ] **Step 3: Rewrite Check 1 to split**

Replace the Task 1 Check 1 block with:

```python
    # Check 1: Staged changes
    out, _ = run(["git", "-C", cwd, "diff", "--cached", "--name-only"])
    staged_paths = [p for p in out.splitlines() if p]
    if staged_paths:
        this_sess, prior = _split(staged_paths)
        if this_sess:
            violations.append(
                "Staged changes not committed: " + ", ".join(this_sess)
            )
        if prior:
            warnings.append(
                "Staged changes from prior sessions: " + ", ".join(prior)
            )
```

- [ ] **Step 4: Rewrite Check 2 to split**

Replace Check 2:

```python
    # Check 2: Unstaged changes
    out, _ = run(["git", "-C", cwd, "diff", "--name-only"])
    unstaged_paths = [p for p in out.splitlines() if p]
    if unstaged_paths:
        this_sess, prior = _split(unstaged_paths)
        if this_sess:
            violations.append(
                "Unstaged changes to tracked files: " + ", ".join(this_sess)
            )
        if prior:
            warnings.append(
                "Unstaged changes from prior sessions: " + ", ".join(prior)
            )
```

- [ ] **Step 5: Rewrite Check 3 to split**

Replace Check 3:

```python
    # Check 3: Untracked files
    out, _ = run(["git", "-C", cwd, "ls-files", "--others", "--exclude-standard"])
    untracked_paths = [p for p in out.splitlines() if p]
    if untracked_paths:
        this_sess, prior = _split(untracked_paths)
        if this_sess:
            violations.append(
                f"{len(this_sess)} untracked file(s) not in .gitignore: "
                + ", ".join(this_sess)
            )
        if prior:
            warnings.append(
                f"{len(prior)} untracked file(s) from prior sessions: "
                + ", ".join(prior)
            )
```

- [ ] **Step 6: Emit warnings at the end, before exiting**

Replace the final output block (`if not violations: sys.exit(0) …`) with:

```python
    # Emit warnings to stderr regardless of whether we block — Claude Code
    # surfaces stderr in the transcript so both user and Claude can see
    # pre-existing dirt without it blocking turn-end.
    if warnings:
        print(
            "⚠ Uncommitted files from prior sessions (not blocking):",
            file=sys.stderr,
        )
        for w in warnings:
            print("  - " + w, file=sys.stderr)

    if not violations:
        sys.exit(0)

    reason = "Repo hygiene violations: " + "; ".join(violations)
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    sys.exit(0)
```

- [ ] **Step 7: Run existing hook tests — confirm they still pass**

Run: `cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/stop-hook-session-aware/claude-optimizing && pytest tests/test_repo_hygiene_hook.py -v`
Expected: PASS — the orphan-remote test asserts block + path-in-reason, and that path is a *branch name* not a file, so the change to Checks 1–3 doesn't affect it.

- [ ] **Step 8: Commit**

```bash
git add claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py
git commit -m "stop-hook: split Checks 1-3 by session origin

Files this session touched (per transcript Edit/Write/NotebookEdit
and Bash substring match) block Stop as before. Files left dirty by
prior sessions emit a stderr warning and allow Stop. Transcript
unreadable / missing fails closed to the pre-existing block behavior.
"
```

---

## Task 5: Integration test — dirty from another session → warn, exit 0

**Files:**
- Create: `claude-optimizing/tests/test_session_aware_hook.py`

- [ ] **Step 1: Write the test file with the scenario**

```python
"""Integration tests for session-aware Stop hook.

Invokes cc-repo-hygiene-hook.py as a subprocess with synthesized
transcripts and real local git repos (no GitHub required).
"""
import json
import subprocess
from pathlib import Path

HOOK_PATH = (
    Path(__file__).resolve().parent.parent / "scripts-hooks" / "cc-repo-hygiene-hook.py"
)


def _write_transcript(tmp_path, tool_uses):
    """Write a minimal JSONL transcript with the given tool_use entries.

    tool_uses: list of dicts like {"name": "Write", "input": {"file_path": "/x"}}.
    """
    path = tmp_path / "transcript.jsonl"
    with path.open("w") as f:
        for tu in tool_uses:
            block = {"type": "tool_use", **tu}
            f.write(json.dumps({"message": {"content": [block]}}) + "\n")
    return path


def _invoke_hook(cwd, transcript_path=None):
    payload = {"cwd": str(cwd), "stop_hook_active": False}
    if transcript_path is not None:
        payload["transcript_path"] = str(transcript_path)
    r = subprocess.run(
        [str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=30,
    )
    return r.stdout, r.stderr, r.returncode


def _decision(stdout):
    stdout = stdout.strip()
    if not stdout:
        return None
    return json.loads(stdout)


def test_dirty_from_other_session_warns_not_blocks(local_git_repo, tmp_path):
    """File dirty on disk, but the transcript doesn't reference it →
    treat as prior-session state, warn on stderr, allow Stop."""
    (local_git_repo / "orphan.txt").write_text("from another session\n")

    # Transcript with tool_uses for unrelated files only.
    tp = _write_transcript(tmp_path, [
        {"name": "Write", "input": {"file_path": str(local_git_repo / "other.py")}},
    ])

    out, err, rc = _invoke_hook(local_git_repo, tp)
    assert rc == 0
    assert _decision(out) is None, f"expected no block, got: {out!r}"
    assert "orphan.txt" in err, f"expected warning mentioning orphan.txt, got: {err!r}"
    assert "prior sessions" in err.lower()
```

- [ ] **Step 2: Run it — expect PASS**

Run: `cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/stop-hook-session-aware/claude-optimizing && pytest tests/test_session_aware_hook.py::test_dirty_from_other_session_warns_not_blocks -v`
Expected: PASS.

If it fails, the classification logic or stderr emit is wrong — fix in the hook before moving on.

- [ ] **Step 3: Commit**

```bash
git add claude-optimizing/tests/test_session_aware_hook.py
git commit -m "test: session-aware hook warns on prior-session dirt"
```

---

## Task 6: Integration test — dirty from this session → block

**Files:**
- Modify: `claude-optimizing/tests/test_session_aware_hook.py`

- [ ] **Step 1: Add the test**

Append:

```python
def test_dirty_from_this_session_blocks(local_git_repo, tmp_path):
    """File dirty on disk AND referenced by a Write in the transcript →
    this-session dirt → block as today."""
    target = local_git_repo / "new.py"
    target.write_text("print('hi')\n")

    tp = _write_transcript(tmp_path, [
        {"name": "Write", "input": {"file_path": str(target)}},
    ])

    out, err, rc = _invoke_hook(local_git_repo, tp)
    assert rc == 0
    d = _decision(out)
    assert d is not None and d.get("decision") == "block"
    assert "new.py" in d.get("reason", "")
```

- [ ] **Step 2: Run**

Run: `cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/stop-hook-session-aware/claude-optimizing && pytest tests/test_session_aware_hook.py::test_dirty_from_this_session_blocks -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add claude-optimizing/tests/test_session_aware_hook.py
git commit -m "test: session-aware hook blocks on this-session dirt"
```

---

## Task 7: Integration test — mixed → block and warn together

**Files:**
- Modify: `claude-optimizing/tests/test_session_aware_hook.py`

- [ ] **Step 1: Add the test**

Append:

```python
def test_mixed_blocks_and_warns(local_git_repo, tmp_path):
    """One file this session, one from prior session → block on the
    this-session path AND warn about the prior-session path."""
    mine = local_git_repo / "mine.py"
    mine.write_text("new\n")
    theirs = local_git_repo / "theirs.txt"
    theirs.write_text("old\n")

    tp = _write_transcript(tmp_path, [
        {"name": "Write", "input": {"file_path": str(mine)}},
    ])

    out, err, rc = _invoke_hook(local_git_repo, tp)
    assert rc == 0
    d = _decision(out)
    assert d is not None and d.get("decision") == "block"
    assert "mine.py" in d.get("reason", "")
    assert "theirs.py" not in d.get("reason", ""), "prior-session path must not be in block reason"
    assert "theirs.txt" in err
```

- [ ] **Step 2: Run**

Run: `cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/stop-hook-session-aware/claude-optimizing && pytest tests/test_session_aware_hook.py::test_mixed_blocks_and_warns -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add claude-optimizing/tests/test_session_aware_hook.py
git commit -m "test: mixed session dirt blocks and warns concurrently"
```

---

## Task 8: Integration test — Bash redirect in transcript counts as this-session

**Files:**
- Modify: `claude-optimizing/tests/test_session_aware_hook.py`

- [ ] **Step 1: Add the test**

Append:

```python
def test_untracked_from_bash_redirect_blocks(local_git_repo, tmp_path):
    """An untracked file whose path appears as a substring in a Bash
    command (e.g. `python foo.py > out.json`) counts as this-session
    via the conservative Bash substring match — block."""
    (local_git_repo / "out.json").write_text('{"ok": true}\n')

    tp = _write_transcript(tmp_path, [
        {"name": "Bash", "input": {"command": "python foo.py > out.json"}},
    ])

    out, err, rc = _invoke_hook(local_git_repo, tp)
    assert rc == 0
    d = _decision(out)
    assert d is not None and d.get("decision") == "block"
    assert "out.json" in d.get("reason", "")
```

- [ ] **Step 2: Run**

Run: `cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/stop-hook-session-aware/claude-optimizing && pytest tests/test_session_aware_hook.py::test_untracked_from_bash_redirect_blocks -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add claude-optimizing/tests/test_session_aware_hook.py
git commit -m "test: bash redirects promote untracked to this-session"
```

---

## Task 9: Integration test — fail closed on missing / malformed transcript

**Files:**
- Modify: `claude-optimizing/tests/test_session_aware_hook.py`

- [ ] **Step 1: Add both fail-closed tests**

Append:

```python
def test_missing_transcript_fails_closed(local_git_repo, tmp_path):
    """No transcript_path → treat all dirty as this-session → block."""
    (local_git_repo / "x.txt").write_text("x\n")

    out, err, rc = _invoke_hook(local_git_repo, transcript_path=None)
    assert rc == 0
    d = _decision(out)
    assert d is not None and d.get("decision") == "block", (
        f"expected block when transcript missing; out={out!r} err={err!r}"
    )
    assert "x.txt" in d.get("reason", "")


def test_malformed_transcript_fails_closed(local_git_repo, tmp_path):
    """Transcript exists but has bad JSON → classification disabled →
    block on every dirty path (preserves old behavior on errors)."""
    (local_git_repo / "y.txt").write_text("y\n")
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not valid json at all\n")

    out, err, rc = _invoke_hook(local_git_repo, bad)
    assert rc == 0
    d = _decision(out)
    assert d is not None and d.get("decision") == "block"
    assert "y.txt" in d.get("reason", "")
```

- [ ] **Step 2: Run**

Run: `cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/stop-hook-session-aware/claude-optimizing && pytest tests/test_session_aware_hook.py -v`
Expected: ALL tests in the file PASS (5 tests now).

- [ ] **Step 3: Commit**

```bash
git add claude-optimizing/tests/test_session_aware_hook.py
git commit -m "test: fail-closed on missing or malformed transcript"
```

---

## Task 10: Final verification + docs update

**Files:**
- Modify: `claude-optimizing/tests/README.md` (add a row for the new test file)

- [ ] **Step 1: Run the full hook test suite**

Run: `cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/stop-hook-session-aware/claude-optimizing && pytest tests/test_repo_hygiene_hook.py tests/test_session_aware_hook.py -v`
Expected: all tests PASS (1 existing + 5 new).

- [ ] **Step 2: Update tests/README.md — add the new row**

Find the "Coverage" table (~line 35) and add a row below `test_repo_hygiene_hook.py`:

```markdown
| `test_session_aware_hook.py` | `cc-repo-hygiene-hook` | Checks 1–3 classify dirty paths by transcript-declared session origin: this-session → block, prior-session → stderr warn, exit 0 |
```

- [ ] **Step 3: Commit and push the whole branch**

```bash
git add claude-optimizing/tests/README.md
git commit -m "docs: note session-aware test coverage in tests/README.md"
git push
```

- [ ] **Step 4: Open a draft PR**

```bash
gh pr create --draft --title "stop-hook: session-aware uncommitted-file handling" --body "$(cat <<'EOF'
## Summary
- Split `cc-repo-hygiene-hook.py` Checks 1–3 by session origin.
- Files this session touched (per `transcript_path` Edit/Write/NotebookEdit, plus Bash substring match) → block, as today.
- Files left dirty by prior sessions → warn on stderr, allow Stop.
- Fail-closed on missing / malformed transcript.

## Design
`docs/superpowers/specs/2026-04-20-stop-hook-session-aware-design.md`

## Test plan
- [ ] `pytest tests/test_repo_hygiene_hook.py tests/test_session_aware_hook.py -v` passes
- [ ] Manually verify: create a stray untracked file while hook is installed, run `/exit` — hook does not block, stderr shows the warning

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Task order rationale

1–3 lay the infrastructure without changing behavior, so the suite stays green through each commit.
4 is the single commit that flips behavior; existing tests still pass because the orphan-remote test doesn't touch Checks 1–3.
5–9 are TDD on the new behavior, one scenario per commit, each kept under ~20 lines of test code.
10 is the cleanup and the PR.
