# Hook scoping to current session — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scope both hooks to the current session's workflow: strip cross-worktree checks from the Stop hook; demote the ExitWorktree hook from blocking to warning.

**Architecture:** Two hook files, three test files, one doc file. Both hooks are read-only (no filesystem mutation). Tests use the existing `hook_local_repo` fixture (no real GitHub) plus one real-GitHub test that already exists and gets inverted.

**Tech Stack:** Python 3, pytest, git/gh CLIs, Claude Code Stop + PostToolUse:ExitWorktree hooks.

**Spec:** `docs/superpowers/specs/2026-04-21-hook-scope-to-current-session-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py` | Modify | Stop hook — strip Checks 4, 5, 5b, 7 + worktree scaffolding |
| `claude-optimizing/scripts-hooks/cc-exit-worktree-hook.py` | Modify | ExitWorktree hook — exit 0 instead of 2; soften wording |
| `claude-optimizing/tests/test_session_aware_hook.py` | Modify | Add two new sibling-scenario tests |
| `claude-optimizing/tests/test_repo_hygiene_hook.py` | Modify | Invert existing test to assert silence |
| `claude-optimizing/tests/test_exit_worktree_hook.py` | Modify | Flip exit-code expectations from 2 → 0 |
| `claude-optimizing/claude-additions.md` | Modify | Trim enforced-checks list; soften ExitWorktree description |

---

## Task 1: Write failing tests for Stop-hook cwd-scoping

**Files:**
- Modify: `claude-optimizing/tests/test_session_aware_hook.py` (append two new tests)
- Modify: `claude-optimizing/tests/test_repo_hygiene_hook.py:39-91` (invert the existing test)

- [ ] **Step 1.1: Append two new sibling tests to `test_session_aware_hook.py`**

Add at the end of the file:

```python
def test_stale_sibling_worktree_does_not_block(hook_local_repo, tmp_path):
    """A sibling worktree whose branch got merged into default is
    another session's concern. The Stop hook must NOT block or warn
    about it when run from the primary worktree."""
    sibling = tmp_path / "sibling"
    branch = "feat-merged"

    # Create sibling worktree on a new branch.
    subprocess.run(
        ["git", "-C", str(hook_local_repo), "worktree", "add",
         str(sibling), "-b", branch],
        check=True, capture_output=True,
    )
    # Commit something on the feature branch.
    (sibling / "feat.txt").write_text("feat\n")
    subprocess.run(["git", "-C", str(sibling), "add", "."],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(sibling), "commit", "-m", "feat"],
                   check=True, capture_output=True)
    # Merge it into main.
    subprocess.run(["git", "-C", str(hook_local_repo), "merge",
                    "--no-ff", "-m", f"merge {branch}", branch],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(hook_local_repo), "push", "origin", "main"],
                   check=True, capture_output=True)

    out, err, rc = _invoke_hook(hook_local_repo)
    assert rc == 0
    assert _decision(out) is None, (
        f"Stop hook should not block on sibling worktree; got: {out!r}"
    )
    assert branch not in err, (
        f"Stop hook should not warn about sibling branch; stderr: {err!r}"
    )


def test_merged_sibling_branch_does_not_block(hook_local_repo):
    """A local branch merged into default but still sitting on disk is
    branch-hygiene cleanup that was Check 4's job. Removed — Stop must
    no longer block on it."""
    branch = "feat-stale"

    # Create the branch, commit on it, merge back into main.
    subprocess.run(["git", "-C", str(hook_local_repo), "checkout", "-b", branch],
                   check=True, capture_output=True)
    (hook_local_repo / "other.txt").write_text("other\n")
    subprocess.run(["git", "-C", str(hook_local_repo), "add", "."],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(hook_local_repo), "commit", "-m", "feat"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(hook_local_repo), "checkout", "main"],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(hook_local_repo), "merge",
                    "--no-ff", "-m", f"merge {branch}", branch],
                   check=True, capture_output=True)
    subprocess.run(["git", "-C", str(hook_local_repo), "push", "origin", "main"],
                   check=True, capture_output=True)

    # Branch is now merged but still exists locally — Check 4's target.
    out, err, rc = _invoke_hook(hook_local_repo)
    assert rc == 0
    assert _decision(out) is None, (
        f"Stop hook should not block on merged sibling branch; got: {out!r}"
    )
```

- [ ] **Step 1.2: Invert `test_repo_hygiene_hook.py::test_hook_flags_squash_merged_orphan_remote_branch`**

Replace the assertions at `test_repo_hygiene_hook.py:80-91` (the post-`_invoke_hook` block) and rename the test:

```python
# Old: lines 80-91 end of test
    out, err, rc = _invoke_hook(MAIN_REPO)
    assert rc == 0, f"hook exited non-zero: err={err!r}"
    decision = _decision(out)
    assert decision is None, (
        f"Stop hook should no longer block on orphan remote branches "
        f"(that's the ExitWorktree hook's territory now); got: {out!r}"
    )
    assert branch not in err, (
        f"Stop hook should not warn about orphan remote branch {branch!r}; "
        f"stderr: {err!r}"
    )
```

Rename the test function (line 39) from:
```python
def test_hook_flags_squash_merged_orphan_remote_branch(test_pr):
```
to:
```python
def test_hook_ignores_squash_merged_orphan_remote_branch(test_pr):
```

Update the docstring (line 40-42) to match:
```python
    """Squash-merge a PR, leave an orphan remote branch on origin, remove
    the worktree + local branch. The Stop hook must NOT flag the orphan
    — that's the ExitWorktree hook's territory now."""
```

- [ ] **Step 1.3: Run the new and inverted tests — expect them to FAIL**

Run:
```bash
cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/hook-scope-to-current-session/claude-optimizing
python3 -m pytest tests/test_session_aware_hook.py::test_stale_sibling_worktree_does_not_block \
                   tests/test_session_aware_hook.py::test_merged_sibling_branch_does_not_block \
                   tests/test_repo_hygiene_hook.py::test_hook_ignores_squash_merged_orphan_remote_branch -v
```
Expected: **3 FAILED**. The first two fail with "Stop hook should not block ..." because Check 4/7 still blocks; the third fails because Check 5b still blocks.

- [ ] **Step 1.4: Commit the failing tests**

```bash
git add claude-optimizing/tests/test_session_aware_hook.py \
        claude-optimizing/tests/test_repo_hygiene_hook.py
git commit -m "test: assert Stop hook ignores cross-worktree state (RED)"
```

---

## Task 2: Strip cross-worktree checks from Stop hook

**Files:**
- Modify: `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py`

This task removes Checks 4, 5, 5b, 7 and their scaffolding. Check 6 (default behind remote) stays.

- [ ] **Step 2.1: Delete the `_find_squash_merged_orphans` helper**

Delete `cc-repo-hygiene-hook.py:103-154` (the entire `_find_squash_merged_orphans` function, including its docstring and the blank line after the `return` statement).

- [ ] **Step 2.2: Delete worktree-parsing and `_worktree_dirty` in `main()`**

Delete `cc-repo-hygiene-hook.py:208-236` (the block from the comment `# Parse worktrees once ...` through the `active_dirty_branches` population loop). The lines in question are:

```python
    # Parse worktrees once so later checks can cross-reference. A worktree
    # with uncommitted changes or untracked files is still "in use" even if
    # its branch has been reset to an ancestor of main by cc-merge-worktree —
    # subsequent checks skip such worktrees/branches to avoid false positives.
    wt_out, _ = run(["git", "-C", cwd, "worktree", "list", "--porcelain"])
    worktrees = []
    current_wt = {}
    for line in wt_out.splitlines():
        if line.startswith("worktree "):
            if current_wt:
                worktrees.append(current_wt)
            current_wt = {"path": line[len("worktree "):]}
        elif line.startswith("branch "):
            current_wt["branch"] = line[len("branch refs/heads/"):]
    if current_wt:
        worktrees.append(current_wt)

    def _worktree_dirty(path):
        porcelain, rc = run(["git", "-C", path, "status", "--porcelain"])
        return rc == 0 and bool(porcelain)

    # Branches backing a dirty worktree (excluding the main worktree itself —
    # dirtiness there is handled by Checks 1–3 on the session cwd).
    active_dirty_branches = set()
    for wt in worktrees[1:]:
        b = wt.get("branch")
        p = wt.get("path")
        if b and p and _worktree_dirty(p):
            active_dirty_branches.add(b)
```

- [ ] **Step 2.3: Delete Checks 4, 5, 5b, and 7**

In `cc-repo-hygiene-hook.py`, delete the blocks for Checks 4, 5, 5b, and 7.

**Check 4 + 5 + 5b** (currently at lines 297-353): delete from the comment `# Check 4: Local branches merged into default` through the end of the `# Check 5b: ...` block. Stop just before `# Check 6: Default branch behind remote`.

**Check 7** (currently at lines 368-398): delete from the comment `# Check 7: Stale worktrees (reuses worktrees parsed above).` through the end of the worktree-iteration loop. Stop just before `# Emit warnings to stderr ...`.

- [ ] **Step 2.4: Simplify Check 6 so it stands on its own**

Check 6 currently lives inside `if default_branch:` alongside the deleted checks. After deletion, restructure so Check 6 is the only thing guarded by `if default_branch:` — the block should read:

```python
    if default_branch:
        # Check 6: Default branch behind remote
        if has_remote:
            local_sha, _ = run(["git", "-C", cwd, "rev-parse", default_branch])
            remote_sha, _ = run(["git", "-C", cwd, "rev-parse", f"origin/{default_branch}"])
            if local_sha and remote_sha and local_sha != remote_sha:
                behind, _ = run(
                    ["git", "-C", cwd, "rev-list", "--count", f"{default_branch}..origin/{default_branch}"]
                )
                if behind and int(behind) > 0:
                    violations.append(
                        f"{default_branch} is {behind} commit(s) behind origin/{default_branch}"
                    )
```

- [ ] **Step 2.5: Run all Stop-hook tests — expect all GREEN**

```bash
cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/hook-scope-to-current-session/claude-optimizing
python3 -m pytest tests/test_session_aware_hook.py tests/test_repo_hygiene_hook.py -v
```
Expected: **all tests PASS** (original session-aware tests still green; the 3 new/inverted cases from Task 1 now pass).

- [ ] **Step 2.6: Commit the hook change**

```bash
git add claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py
git commit -m "stop-hook: strip cross-worktree checks (4/5/5b/7)

Only Checks 1-3 (session-aware file dirt) and Check 6 (default behind
remote) remain. Other sessions' worktrees, merged branches, and
orphan remote branches are no longer this hook's business — that's
the ExitWorktree hook's reminder territory."
```

---

## Task 3: Flip ExitWorktree test expectations (failing)

**Files:**
- Modify: `claude-optimizing/tests/test_exit_worktree_hook.py:38-78` (one test)

- [ ] **Step 3.1: Rename the test and flip `rc` assertion**

Change `test_exit_worktree_hook.py:38`:

```python
def test_hook_warns_on_squash_merged_orphan_after_action_remove(test_pr):
    """When a squash-merged PR leaves an orphan remote branch and the
    user's ExitWorktree removed the worktree+local branch, the hook
    must surface a reminder on stderr without blocking the next tool
    call (exit 0, stderr non-empty)."""
```

Then at `test_exit_worktree_hook.py:74-78` replace:

```python
    out, err, rc = _invoke_hook(MAIN_REPO)
    assert rc == 0, f"hook should warn, not block (rc=0); got rc={rc} err={err!r}"
    assert branch in err, (
        f"orphan branch {branch!r} not mentioned in hook stderr: {err!r}"
    )
```

- [ ] **Step 3.2: Run — expect FAILED**

```bash
cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/hook-scope-to-current-session/claude-optimizing
python3 -m pytest tests/test_exit_worktree_hook.py::test_hook_warns_on_squash_merged_orphan_after_action_remove -v
```
Expected: **FAIL** with `hook should warn, not block (rc=0); got rc=2`.

- [ ] **Step 3.3: Commit the failing test**

```bash
git add claude-optimizing/tests/test_exit_worktree_hook.py
git commit -m "test(exit-worktree-hook): expect warn (rc=0) instead of block (RED)"
```

---

## Task 4: Demote ExitWorktree hook to warn-only

**Files:**
- Modify: `claude-optimizing/scripts-hooks/cc-exit-worktree-hook.py`

- [ ] **Step 4.1: Update the module docstring and reword output**

Edit `cc-exit-worktree-hook.py:1-21` (the module docstring). Replace:

```python
"""PostToolUse hook for ExitWorktree — block if worktree exit left dangling state.

Fires right after Claude runs ExitWorktree. Detects two flavors of the
"I exited the worktree but forgot to run cc-merge-worktree" bug:

  1. A non-default-branch worktree is still on disk and its branch is
     already merged into origin/<default> (action:keep without follow-up).
  2. A remote branch on origin corresponds to a merged PR but the local
     branch is gone (action:remove shortcut on a repo with
     `delete_branch_on_merge: false`).

Exit codes:
  0  — nothing dangling, proceed
  2  — blocking; prints a diagnostic to stderr that the harness surfaces
       back to Claude as a tool-use error

This is the flip-side of the Stop hygiene hook: Stop catches the problem at
turn-end; this one catches it the moment ExitWorktree returns, so Claude has
to resolve it before the next tool call rather than at turn-end.
"""
```

with:

```python
"""PostToolUse hook for ExitWorktree — reminds about dangling worktree state.

Fires right after Claude runs ExitWorktree. Detects two flavors of the
"I exited the worktree but forgot to run cc-merge-worktree" bug:

  1. A non-default-branch worktree is still on disk and its branch is
     already merged into origin/<default> (action:keep without follow-up).
  2. A remote branch on origin corresponds to a merged PR but the local
     branch is gone (action:remove shortcut on a repo with
     `delete_branch_on_merge: false`).

Exit codes: always 0 — the hook writes a reminder to stderr (surfaced in
the transcript) but never blocks the next tool call. Cleanup is the
user's (or a subsequent session's) choice.
"""
```

- [ ] **Step 4.2: Change `return 2` to `return 0` and soften the first line**

Edit `cc-exit-worktree-hook.py:180-185`. Replace:

```python
    lines = [
        "ExitWorktree completed but the exit ritual left dangling state.",
        "You MUST run cc-merge-worktree to finish the ritual (see the",
        "'Exiting a Worktree' section of the global CLAUDE.md).",
        "",
    ]
```

with:

```python
    lines = [
        "Reminder: ExitWorktree left some dangling state on disk / origin.",
        "Run cc-merge-worktree to finish the ritual when you're ready. "
        "This is NOT blocking the next tool call.",
        "",
    ]
```

At `cc-exit-worktree-hook.py:200` replace:

```python
    print("\n".join(lines), file=sys.stderr)
    return 2
```

with:

```python
    print("\n".join(lines), file=sys.stderr)
    return 0
```

- [ ] **Step 4.3: Run all ExitWorktree-hook tests — expect GREEN**

```bash
cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/hook-scope-to-current-session/claude-optimizing
python3 -m pytest tests/test_exit_worktree_hook.py -v
```
Expected: **all PASS**.

- [ ] **Step 4.4: Commit**

```bash
git add claude-optimizing/scripts-hooks/cc-exit-worktree-hook.py
git commit -m "exit-worktree-hook: warn-only (exit 0), no longer blocks

Dangling worktrees/orphan remotes surface as a stderr reminder that
Claude sees in the transcript. Cleanup stays user-driven. The
cc-merge-worktree PR/branch mismatch gate (landed d1bfe99) means
even a naive follow-up is safe against cross-worktree damage."
```

---

## Task 5: Update `claude-additions.md`

**Files:**
- Modify: `claude-optimizing/claude-additions.md`

- [ ] **Step 5.1: Soften ExitWorktree hook line**

At `claude-additions.md:61`, replace:

```markdown
- `cc-exit-worktree-hook` — PostToolUse:ExitWorktree enforcer that blocks the next tool call if a merged worktree is still on disk.
```

with:

```markdown
- `cc-exit-worktree-hook` — PostToolUse:ExitWorktree reminder that surfaces dangling worktree / orphan-remote state on stderr (non-blocking).
```

- [ ] **Step 5.2: Trim the "What the Hook Enforces" list**

At `claude-additions.md:107-116`, replace the whole section:

```markdown
### What the Hook Enforces

The `Stop` hook (`~/.claude/hooks/cc-repo-hygiene-hook.py`, vendored from catherding `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py`) will **block the turn from ending** if any of these are true:

1. Staged or unstaged changes exist
2. Untracked files exist (not in `.gitignore`)
3. Local branches exist that are already merged into the default branch
4. Remote branches exist that are already merged into the default branch
5. The default branch is behind the remote
6. Stale worktrees exist (branch deleted or merged)
```

with:

```markdown
### What the Hook Enforces

The `Stop` hook (`~/.claude/hooks/cc-repo-hygiene-hook.py`, vendored from catherding `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py`) scopes to the **current worktree's** state. It will **block the turn from ending** if any of these are true:

1. Staged or unstaged changes exist for files this session touched
2. Untracked files exist (not in `.gitignore`) for files this session touched
3. The default branch is behind the remote

Branch cleanup (merged local/remote branches) and stale worktrees from other sessions are **not** this hook's concern. The ExitWorktree hook surfaces those as a non-blocking reminder when you exit a worktree.
```

- [ ] **Step 5.3: Commit the doc change**

```bash
git add claude-optimizing/claude-additions.md
git commit -m "docs(claude-additions): reflect cwd-scoped Stop hook"
```

---

## Task 6: Verify + mark PR ready + merge

- [ ] **Step 6.1: Full non-GitHub test suite green**

```bash
cd /Users/mfullerton/projects/active/catherding/.claude/worktrees/hook-scope-to-current-session/claude-optimizing
python3 -m pytest tests/test_session_aware_hook.py tests/test_exit_worktree_hook.py tests/test_repo_hygiene_hook.py -v
```
Expected: **all PASS**.

- [ ] **Step 6.2: Push the branch**

```bash
git push
```

- [ ] **Step 6.3: Mark PR #76 ready**

```bash
gh pr ready 76
```

- [ ] **Step 6.4: Merge via cc-merge-worktree**

IMPORTANT: run from **main repo**, not from inside the worktree. `cc-merge-worktree` will refuse otherwise (the caller-inside-worktree gate).

```bash
cd /Users/mfullerton/projects/active/catherding
cc-merge-worktree 76 --branch worktree-hook-scope-to-current-session
```

Expected: squash-merged, worktree removed, local+remote branch deleted, `done: <commit msg>` printed.

---

## Self-Review

**Spec coverage:**
- "Strip Checks 4/5/5b/7 from Stop hook" → Task 2 ✓
- "Keep Checks 1-3 + Check 6" → Task 2 Step 2.4 ✓
- "Demote ExitWorktree hook to warn-only" → Task 4 ✓
- "Flip test_exit_worktree_hook.py exit codes" → Task 3 ✓
- "Invert test_repo_hygiene_hook.py" → Task 1 Step 1.2 ✓
- "Add sibling-worktree + sibling-branch tests" → Task 1 Step 1.1 ✓
- "Trim claude-additions.md enforced-checks list" → Task 5 ✓
- "Soften ExitWorktree hook description" → Task 5 ✓

**Placeholder scan:** no TBD / TODO / "handle edge cases" / "similar to Task N" found. All code blocks are complete.

**Type / name consistency:** hook-printed strings, function names, and file paths referenced consistently across tasks. `hook_local_repo` fixture used correctly in both new tests (conftest.py:71 yields `repo` — just the repo path, no remote to manage).

**Bite-size check:** each step is one file edit or one command. No step bundles multiple responsibilities. Commits are frequent (one per task logical unit).
