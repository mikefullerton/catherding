---
name: cleanup-repo
version: "1.0.0"
description: "Find and fix stale branches, deleteable branches, finished worktrees, uncommitted files, and other repo hygiene issues. Triggers on 'cleanup repo', 'clean up repo', or /cleanup-repo."
argument-hint: "[--dry-run] [--version]"
allowed-tools: Read, Glob, Grep, Bash(git *, gh *, ls *, rm *, test *), AskUserQuestion
model: sonnet
---

## Version Check

If `$ARGUMENTS` is `--version`, respond with exactly:

> cleanup-repo v1.0.0

Then stop. Do not continue with the rest of the skill.

Otherwise, print `cleanup-repo v1.0.0` as the first line of output, then proceed.

**Version check**: Read `${CLAUDE_SKILL_DIR}/SKILL.md` from disk and extract the `version:` field from frontmatter. If it differs from this skill's version (1.0.0), print:

> ⚠ This skill is running v1.0.0 but vA.B.C is installed. Restart the session to use the latest version.

Continue running — do not stop.

---

# Cleanup Repo

Iteratively scan a git repository for hygiene issues — stale branches, merged branches, orphaned worktrees, uncommitted changes, untracked files — and offer to fix each one until the repo is clean.

## Guards

- **Never force-deletes** — uses `git branch -d` (safe delete), never `-D`, unless the user explicitly approves
- **Never discards uncommitted work** — only offers to stash, commit, or show what's dirty
- **Never removes worktrees with uncommitted changes** — flags them but does not touch them
- **Always confirms before destructive actions** — each fix is offered individually
- **`--dry-run` mode is read-only** — reports issues but modifies nothing

---

## Step 1: Parse Arguments

Parse `$ARGUMENTS`:

1. **`--dry-run`** → set dry-run mode (scan and report only, no modifications)
2. **`--version`** → handled above

---

## Step 2: Verify Context

1. Confirm the current directory is a git repository (`git rev-parse --git-dir`). If not, print:
   > ERROR: Not a git repository.

   And stop.

2. Identify the default branch (`git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null` or fall back to `main`/`master`).

3. Run `git fetch --prune` to sync remote tracking state.

4. Print:
   ```
   === REPO CLEANUP ===
   Repository: <repo name>
   Default branch: <branch>
   Current branch: <branch>
   ```

---

## Step 3: Scan

Run all scans and collect findings into categories. For each category, record the items found.

### 3a: Uncommitted Changes

Run `git status --porcelain`. Categorize:
- **Staged but uncommitted** — files in the index not yet committed
- **Unstaged modifications** — tracked files with local changes
- **Untracked files** — files not in the index (exclude common generated dirs: `node_modules/`, `.build/`, `dist/`, `__pycache__/`, `.venv/`)

### 3b: Stale Branches (gone remotes)

Run `git branch -vv`. Find local branches whose upstream is marked `[gone]` — the remote branch was deleted but the local tracking branch remains.

### 3c: Merged Branches

Find local branches fully merged into the default branch:
```
git branch --merged <default-branch>
```
Exclude the default branch itself and the current branch from the list.

### 3d: Unmerged Branches with No Recent Activity

Find local branches NOT merged into the default branch where the last commit is older than 30 days:
```
git for-each-ref --sort=-committerdate --format='%(refname:short) %(committerdate:iso)' refs/heads/
```
Flag branches with no commits in the last 30 days that are not merged. These are informational only — do not offer to delete without explicit user approval.

### 3e: Worktrees

Run `git worktree list`. For each worktree (excluding the main working tree):
1. Check if the worktree directory still exists on disk
2. Check if the worktree's branch has been merged into the default branch
3. Check if the worktree has uncommitted changes (`git -C <path> status --porcelain`)

Categorize:
- **Orphaned** — worktree directory no longer exists (prunable)
- **Finished** — worktree branch is merged into default, no uncommitted changes (removable)
- **Dirty** — worktree has uncommitted changes (flag only, do not offer removal)
- **Active** — worktree branch is not merged, has no issues (skip)

### 3f: Dangling Worktree References

Run `git worktree list --porcelain` and check for worktrees pointing to paths that no longer exist. These can be cleaned with `git worktree prune`.

---

## Step 4: Report

Print the full scan results:

```
=== SCAN RESULTS ===

Uncommitted Changes:
  Staged: <n> files
  Unstaged: <n> files
  Untracked: <n> files
  <list each file with its status>

Stale Branches (remote gone): <n>
  <branch-name> (tracking: origin/<name>, gone)
  ...

Merged Branches (safe to delete): <n>
  <branch-name> (merged into <default>)
  ...

Inactive Branches (>30 days, not merged): <n>
  <branch-name> (last commit: <date>, <n> days ago)
  ...

Worktrees: <n> total, <n> issues
  <path> [orphaned] — directory missing
  <path> [finished] — branch merged, clean
  <path> [dirty] — has uncommitted changes (will not touch)
  <path> [active] — ok
  ...

Dangling worktree refs: <n>
```

Then print the summary:

```
=== SUMMARY ===
Issues found: <total count>
  <n> stale branches to delete
  <n> merged branches to delete
  <n> inactive branches to review
  <n> worktrees to clean up
  <n> dangling worktree refs to prune
  <n> uncommitted file groups to address
```

If no issues found, print:

```
=== CLEAN ===
No issues found. Repository is clean.
```

And stop.

**If `--dry-run` is set**, print:

```
=== DRY RUN COMPLETE ===
No changes were made. Run `/cleanup-repo` (without --dry-run) to fix issues.
```

And stop.

---

## Step 5: Fix Loop

Process issues in this order, one category at a time. After each fix, re-scan that category to confirm the fix worked before moving on.

### Priority order:

1. **Dangling worktree refs** — `git worktree prune` (safe, no data loss)
2. **Orphaned worktrees** — `git worktree prune` (same command covers these)
3. **Finished worktrees** — for each, use AskUserQuestion:
   > Worktree at `<path>` — branch `<name>` is merged into `<default>`. Remove it?
   - **Yes** → `git worktree remove <path>`, then `git branch -d <branch>` if local
   - **No** → skip
   - **Stop** → exit the fix loop entirely

4. **Stale branches** — for each, use AskUserQuestion:
   > Branch `<name>` — remote is gone. Delete local branch?
   - **Yes** → `git branch -d <name>`
   - **No** → skip
   - **Stop** → exit the fix loop

5. **Merged branches** — for each, use AskUserQuestion:
   > Branch `<name>` — fully merged into `<default>`. Delete it?
   - **Yes** → `git branch -d <name>`
   - **No** → skip
   - **Stop** → exit the fix loop

6. **Inactive branches** — for each, use AskUserQuestion:
   > Branch `<name>` — last commit <n> days ago, not merged. What to do?
   - **Skip** → leave it
   - **Delete** → `git branch -d <name>` (will fail if not merged; if it fails, report and ask if they want to force-delete with `-D`)
   - **Stop** → exit the fix loop

7. **Uncommitted changes** — use AskUserQuestion:
   > There are uncommitted changes. What would you like to do?
   - **Show details** → print `git status` and `git diff --stat`
   - **Stash all** → `git stash push -m "cleanup-repo stash <date>"`
   - **Skip** → leave them
   - **Stop** → exit the fix loop

### After each category, re-verify

After processing all items in a category, re-run that specific scan. If new issues appeared (e.g., removing a worktree revealed a branch to delete), process them before moving to the next category.

---

## Step 6: Final Report

After the fix loop completes (all categories processed or user stopped), run the full scan one more time and print:

```
=== CLEANUP COMPLETE ===
Fixed: <n> issues
  <n> branches deleted
  <n> worktrees removed
  <n> dangling refs pruned
  <n> stashes created
Remaining: <n> issues (skipped or stopped)

Repository status: <CLEAN | <n> remaining issues>
```

---

## Examples

**Full interactive cleanup:**
```
/cleanup-repo
```

**Preview issues without fixing:**
```
/cleanup-repo --dry-run
```

---

## Done

The cleanup is complete. Any skipped issues can be addressed by running `/cleanup-repo` again.
