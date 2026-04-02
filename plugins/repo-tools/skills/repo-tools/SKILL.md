---
name: repo-tools
description: "Repository status overview and interactive cleanup for git repos"
version: "1.0.0"
argument-hint: "<status|clean|--help> [--dry-run] [--version]"
allowed-tools: Read, Glob, Grep, Bash(git *, gh *, ls *, rm *, test *), AskUserQuestion
model: sonnet
---

# Repo Tools v1.0.0

Repository status overview and interactive cleanup for git repos.

## Startup

If `$ARGUMENTS` is `--version`, respond with exactly:
> repo-tools v1.0.0

Then stop.

**CRITICAL**: Print the version line first:

repo-tools v1.0.0

## Route by argument

| Argument | Action |
|----------|--------|
| `status` | Go to **Status** section |
| `clean` | Go to **Clean** section (pass remaining args) |
| `clean --dry-run` | Go to **Clean** section in dry-run mode |
| `--help` | Go to **Help** section |
| *(empty or anything else)* | Print usage and stop: `Usage: /repo-tools <status\|clean\|--help> [--dry-run] [--version]` |

---

## Help

Print the following exactly, then stop:

> ## Repo Tools
>
> Repository status overview and interactive cleanup for git repos.
>
> **Usage:** `/repo-tools <status|clean|--help> [--dry-run] [--version]`
>
> ### Commands
>
> **`/repo-tools status`** — Quick overview of repository state
>
> Shows a snapshot of the current repo including:
> - Project path and current branch
> - Worktree detection (main repo vs git worktree)
> - Dirty files count and uncommitted changes
> - Commits ahead/behind default branch or remote
> - Stale branches (remote tracking branch deleted)
> - Merged branches (safe to delete)
> - Prunable worktrees (directory missing)
> - Finished worktrees (branch merged but worktree still exists)
> - Inactive branches (no commits in 30+ days)
>
> This is read-only — it never modifies anything.
>
> **`/repo-tools clean`** — Interactive repo cleanup
>
> Scans for hygiene issues and offers to fix each one interactively:
> - Prunes dangling worktree refs
> - Removes orphaned and finished worktrees
> - Deletes stale and merged branches
> - Reviews inactive branches
> - Addresses uncommitted changes (show, stash, or skip)
>
> Every destructive action requires confirmation. Uses safe deletes (`git branch -d`, never `-D` unless you approve). Never discards uncommitted work.
>
> **`/repo-tools clean --dry-run`** — Preview issues without fixing
>
> Runs the full scan and reports all issues found, but makes no changes.

---

## Status

### Step 1: Verify Context

Confirm the current directory is a git repository (`git rev-parse --git-dir`). If not, print:
> Not a git repository.

And stop.

### Step 2: Gather Info

Collect all of the following:

**Project info:**
- Repository root path (`git rev-parse --show-toplevel`)
- Current branch (`git rev-parse --abbrev-ref HEAD`)
- Whether this is a git worktree (check if `git rev-parse --git-dir` contains `/worktrees/`)

**Default branch:**
- Detect via `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null`, fall back to `main` or `master`

**Working tree state:**
- Staged files count (`git diff --cached --numstat | wc -l`)
- Unstaged modified files count (`git diff --numstat | wc -l`)
- Untracked files count (`git ls-files --others --exclude-standard | wc -l`)

**Branch position:**
- If on a feature branch: commits ahead of default (`git rev-list --count <default>..HEAD`), commits behind default (`git rev-list --count HEAD..<default>`)
- If on default branch: commits ahead of remote (`git rev-list --count origin/<default>..HEAD`), commits behind remote (`git rev-list --count HEAD..origin/<default>`)

**Repo hygiene:**
- Stale branches: local branches whose upstream is `[gone]` (`git branch -vv | grep ': gone]'`)
- Merged branches: branches fully merged into default, excluding default itself and current branch (`git branch --merged <default>`)
- Prunable worktrees: `git worktree prune --dry-run | wc -l`
- Finished worktrees: worktrees whose branch is merged into default (iterate `git worktree list`, check each with `git merge-base --is-ancestor`)
- Inactive branches: branches not merged into default with last commit older than 30 days (`git for-each-ref --sort=-committerdate --format='%(refname:short) %(committerdate:unix)' refs/heads/`)

### Step 3: Print Report

Print a formatted report. Use this structure:

```
=== REPO STATUS ===

Project:  <path>
Branch:   <branch> [worktree] (if applicable)
Default:  <default branch>

Working Tree:
  Staged:    <n> files
  Unstaged:  <n> files
  Untracked: <n> files

Branch Position:
  <n> commits ahead of <default|origin>
  <n> commits behind <default|origin>
  (or: up to date)

Repo Hygiene:
  Stale branches:      <n>
  Merged branches:     <n>
  Prunable worktrees:  <n>
  Finished worktrees:  <n>
  Inactive branches:   <n>
```

If all hygiene counts are zero, print:
```
Repo Hygiene:
  Clean — no issues found
```

If any hygiene issues exist, print at the bottom:
```
Run `/repo-tools clean` to fix interactively.
```

Omit sections with no data (e.g., if staged/unstaged/untracked are all 0, print `Working Tree: clean`).

---

## Clean

Interactive repo cleanup. Scans for hygiene issues and offers to fix each one.

### Guards

- **Never force-deletes** — uses `git branch -d` (safe delete), never `-D`, unless the user explicitly approves
- **Never discards uncommitted work** — only offers to stash, commit, or show what's dirty
- **Never removes worktrees with uncommitted changes** — flags them but does not touch them
- **Always confirms before destructive actions** — each fix is offered individually
- **`--dry-run` mode is read-only** — reports issues but modifies nothing

### Step 1: Parse Arguments

Parse remaining `$ARGUMENTS` after `clean`:

1. **`--dry-run`** → set dry-run mode (scan and report only, no modifications)

### Step 2: Verify Context

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

### Step 3: Scan

Run all scans and collect findings into categories. For each category, record the items found.

#### 3a: Uncommitted Changes

Run `git status --porcelain`. Categorize:
- **Staged but uncommitted** — files in the index not yet committed
- **Unstaged modifications** — tracked files with local changes
- **Untracked files** — files not in the index (exclude common generated dirs: `node_modules/`, `.build/`, `dist/`, `__pycache__/`, `.venv/`)

#### 3b: Stale Branches (gone remotes)

Run `git branch -vv`. Find local branches whose upstream is marked `[gone]` — the remote branch was deleted but the local tracking branch remains.

#### 3c: Merged Branches

Find local branches fully merged into the default branch:
```
git branch --merged <default-branch>
```
Exclude the default branch itself and the current branch from the list.

#### 3d: Unmerged Branches with No Recent Activity

Find local branches NOT merged into the default branch where the last commit is older than 30 days:
```
git for-each-ref --sort=-committerdate --format='%(refname:short) %(committerdate:iso)' refs/heads/
```
Flag branches with no commits in the last 30 days that are not merged. These are informational only — do not offer to delete without explicit user approval.

#### 3e: Worktrees

Run `git worktree list`. For each worktree (excluding the main working tree):
1. Check if the worktree directory still exists on disk
2. Check if the worktree's branch has been merged into the default branch
3. Check if the worktree has uncommitted changes (`git -C <path> status --porcelain`)

Categorize:
- **Orphaned** — worktree directory no longer exists (prunable)
- **Finished** — worktree branch is merged into default, no uncommitted changes (removable)
- **Dirty** — worktree has uncommitted changes (flag only, do not offer removal)
- **Active** — worktree branch is not merged, has no issues (skip)

#### 3f: Dangling Worktree References

Run `git worktree list --porcelain` and check for worktrees pointing to paths that no longer exist. These can be cleaned with `git worktree prune`.

### Step 4: Report

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
No changes were made. Run `/repo-tools clean` (without --dry-run) to fix issues.
```

And stop.

### Step 5: Fix Loop

Process issues in this order, one category at a time. After each fix, re-scan that category to confirm the fix worked before moving on.

#### Priority order:

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
   - **Stash all** → `git stash push -m "repo-tools stash <date>"`
   - **Skip** → leave them
   - **Stop** → exit the fix loop

#### After each category, re-verify

After processing all items in a category, re-run that specific scan. If new issues appeared (e.g., removing a worktree revealed a branch to delete), process them before moving to the next category.

### Step 6: Final Report

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
