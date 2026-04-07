---
name: repo-tools
description: "Recursive repository cleanup — auto-fixes obvious issues, interactively resolves the rest"
version: "2.0.0"
argument-hint: "<clean|--help> [--depth N] [--dry-run] [--version]"
allowed-tools: Read, Glob, Grep, Bash(git *, gh *, ls *, rm *, test *, find *), AskUserQuestion
model: sonnet
---

# Repo Tools v2.0.0

Recursive repository cleanup — auto-fixes obvious issues, interactively resolves the rest.

## Startup

If `$ARGUMENTS` is `--version`, respond with exactly:
> repo-tools v2.0.0

Then stop.

**CRITICAL**: Print the version line first:

repo-tools v2.0.0

## Route by argument

| Argument | Action |
|----------|--------|
| `clean` | Go to **Clean** section (pass remaining args) |
| `clean --dry-run` | Go to **Clean** section in dry-run mode |
| `clean --depth N` | Go to **Clean** section with custom depth |
| `--help` | Go to **Help** section |
| *(empty or anything else)* | Print usage and stop: `Usage: /repo-tools <clean\|--help> [--depth N] [--dry-run] [--version]` |

---

## Help

Print the following exactly, then stop:

> ## Repo Tools
>
> Recursive repository cleanup — auto-fixes obvious issues, interactively resolves the rest.
>
> **Usage:** `/repo-tools <clean|--help> [--depth N] [--dry-run] [--version]`
>
> ### Commands
>
> **`/repo-tools clean`** — Discover and clean git repos
>
> Recursively discovers git repositories from the current directory (default depth 3), then walks each one:
>
> **Auto-fixed (no confirmation needed):**
> - Prunes dangling worktree references
> - Deletes branches whose remote tracking branch is gone
> - Deletes branches fully merged into the default branch
> - Removes finished worktrees (branch merged, no uncommitted changes)
>
> **Interactive (stops for input):**
> - Uncommitted changes — grouped into smart batches with descriptions, offers: commit or chat
> - Inactive unmerged branches — shows change summary and last commit, offers: delete, skip, or chat
> - Dirty worktrees — summarizes contents, offers: stash, skip, or chat
>
> After processing all repos, prints a final dashboard summarizing everything done.
>
> **`/repo-tools clean --dry-run`** — Preview without changing anything
>
> Walks the full tree and reports what would be auto-fixed and what would need input, but makes no changes.
>
> **`/repo-tools clean --depth N`** — Set discovery depth (default: 3)
>
> Controls how many directory levels deep to search for git repositories.

---

## Clean

### Guards

- **Never force-deletes** — uses `git branch -d` (safe delete), never `-D`, unless the user explicitly approves
- **Never discards uncommitted work** — only offers to commit, stash, or discuss
- **Never removes worktrees with uncommitted changes** — flags them but does not touch them
- **Always confirms before ambiguous actions** — deterministic fixes are silent, judgment calls stop for input
- **`--dry-run` mode is read-only** — reports everything but modifies nothing

### Step 1: Parse Arguments

Parse `$ARGUMENTS` after `clean`:

- **`--dry-run`** → set dry-run mode (scan and report only, no modifications)
- **`--depth N`** → set discovery depth (default: 3)

### Step 2: Discover Repositories

Find all git repositories starting from the current working directory.

```bash
find . -maxdepth <depth> -name .git -type d 2>/dev/null
```

For each `.git` found:
1. Resolve the parent directory as the repo root
2. Skip if the `.git` path contains `/worktrees/` (these are worktree checkouts, not standalone repos)
3. Skip if the repo root is inside another already-discovered repo's `.git` directory (submodules handled by parent)

Sort results by path for predictable ordering.

If no repositories are found, print:
> No git repositories found within depth <N> of `<cwd>`.

And stop.

If exactly one repo is found (e.g., cwd is inside a repo), proceed directly — no "discovered N repos" header needed.

If multiple repos are found, print:
```
Found <N> repositories:
  <path1>
  <path2>
  ...
```

### Step 3: Walk Each Repository

Process repositories one at a time. For each repo:

1. Print a header:
   ```
   --- <repo-path> (<branch>) ---
   ```

2. Determine the default branch (`git -C <path> symbolic-ref refs/remotes/origin/HEAD 2>/dev/null`, fall back to `main` or `master`).

3. Run `git -C <path> fetch --prune 2>/dev/null` to sync remote tracking state (skip silently if no remote).

4. Run all scans (Steps 3a-3f below).

5. Auto-fix deterministic items (Step 4).

6. Stop on each ambiguous item for input (Step 5).

7. Move to the next repo.

#### 3a: Dangling Worktree References

Run `git -C <path> worktree prune --dry-run 2>&1`. Count lines of output.

Category: **auto-fix**

#### 3b: Stale Branches (remote gone)

Run `git -C <path> branch -vv`. Find branches whose upstream is marked `[gone]`.

Category: **auto-fix**

#### 3c: Merged Branches

```bash
git -C <path> branch --merged <default>
```

Exclude the default branch and the current branch.

Category: **auto-fix**

#### 3d: Finished Worktrees

Run `git -C <path> worktree list`. For each worktree (excluding main):
- Check if the directory exists
- Check if the branch is merged into default (`git merge-base --is-ancestor`)
- Check for uncommitted changes (`git -C <worktree-path> status --porcelain`)

A worktree is "finished" if the branch is merged and there are no uncommitted changes.

**Orphaned worktrees** (directory missing) are also auto-fixable via `git worktree prune`.

Category: **auto-fix** (orphaned and finished with clean state)

#### 3e: Uncommitted Changes

Run `git -C <path> status --porcelain`. Categorize:
- **Staged** — files in the index not yet committed (prefix `A`, `M`, `R`, `D` in first column)
- **Unstaged** — tracked files with local changes (prefix `M`, `D` in second column)
- **Untracked** — new files not in the index (prefix `??`)

Exclude common generated dirs: `node_modules/`, `.build/`, `dist/`, `__pycache__/`, `.venv/`, `.egg-info/`

If any exist, group them into **smart batches** (see Step 5a).

Category: **interactive**

#### 3f: Inactive Unmerged Branches

Find branches NOT merged into default with last commit older than 30 days:

```bash
git -C <path> for-each-ref --sort=-committerdate \
  --format='%(refname:short) %(committerdate:unix) %(committerdate:relative) %(subject)' refs/heads/
```

Cross-reference with `git branch --merged <default>` to exclude merged branches. Exclude the default branch and current branch.

For each inactive branch, also gather:
- Last commit message (from the `%(subject)` above)
- Number of commits ahead of default (`git rev-list --count <default>..<branch>`)
- Diff stat summary (`git diff --stat <default>...<branch> | tail -1`)

Category: **interactive**

#### 3g: Dirty Worktrees

From the worktree scan in 3d, any worktree with uncommitted changes.

For each, gather:
- `git -C <worktree-path> status --porcelain` output
- Branch name and whether it's merged

Category: **interactive**

### Step 4: Auto-Fix (Deterministic)

Process in this order. In `--dry-run` mode, report what *would* be done but change nothing.

#### 4a: Prune dangling worktree refs

```bash
git -C <path> worktree prune
```

Print: `  Pruned <N> dangling worktree ref(s)`

#### 4b: Remove finished worktrees

For each finished worktree (merged branch, no changes):

```bash
git -C <path> worktree remove <worktree-path>
git -C <path> branch -d <branch>
```

Print: `  Removed worktree <path> (branch <name>, merged)`

#### 4c: Delete stale branches

For each branch whose remote is gone:

```bash
git -C <path> branch -d <branch>
```

Print: `  Deleted stale branch <name> (remote gone)`

#### 4d: Delete merged branches

For each branch fully merged into default:

```bash
git -C <path> branch -d <branch>
```

Print: `  Deleted merged branch <name>`

If nothing was auto-fixed, print: `  No auto-fixable issues`

#### Dry-run output

In `--dry-run` mode, prefix each line with `[dry-run]` and do not execute commands:
```
  [dry-run] Would prune 2 dangling worktree ref(s)
  [dry-run] Would delete stale branch feature/old (remote gone)
  [dry-run] Would delete merged branch fix/typo
```

### Step 5: Interactive (Judgment Calls)

Stop on each ambiguous item, present a summary, and ask the user. In `--dry-run` mode, print the summary but skip asking — just report what would need input.

#### 5a: Uncommitted Changes — Smart Batching

Group uncommitted files into logical batches using these heuristics:

1. **Directory affinity** — files in the same directory or subtree
2. **Change type** — new files together, modifications together
3. **Naming patterns** — test files batch together, config files batch together, source files in the same module batch together

For each batch:
1. Generate a short description of what the batch represents (e.g., "New test files for auth module", "Modified API handler and schema in src/api/")
2. List the files in the batch with their status (new/modified/deleted)
3. For modified files, include a one-line summary of what changed (`git diff --stat` for each file)

Present each batch to the user:

```
Batch 1: <description>
  M  src/api/handler.py   (+12 -3)
  M  src/api/schema.py    (+5 -1)
  A  src/api/validator.py  (new, 45 lines)
```

Use AskUserQuestion for each batch:
> **<description>** — <N> file(s). Commit or chat?
>
> - **Commit** — commit with a suggested message (editable)
> - **Chat** — tell me more about these changes so I can help
> - **Skip** — leave as-is
> - **Stop** — stop cleaning this repo

If **Commit**: suggest a commit message based on the file changes, ask if the user wants to adjust it, then:
```bash
git -C <path> add <files...>
git -C <path> commit -m "<message>"
```

If **Chat**: show `git diff` for the batch files and discuss. After discussion, re-offer the commit/skip/stop options.

#### 5b: Inactive Unmerged Branches

For each inactive branch, present:

```
Branch: <name>
  Last commit: <date> (<N> days ago)
  Message: "<last commit subject>"
  Changes: <N> commits ahead of <default> — <diff-stat summary>
```

Use AskUserQuestion:
> Branch `<name>` — <N> days inactive, <N> commits not merged. "<last commit subject>". Delete, skip, or chat?
>
> - **Delete** — `git branch -d` (safe delete; will warn if not fully merged)
> - **Skip** — leave it
> - **Chat** — show me more detail about this branch
> - **Stop** — stop cleaning this repo

If **Delete** and `-d` fails (not merged), report the error and ask:
> Safe delete failed — branch is not fully merged. Force-delete with `git branch -D`?

If **Chat**: show `git log --oneline <default>..<branch>` and `git diff --stat <default>...<branch>`, then re-offer options.

#### 5c: Dirty Worktrees

For each dirty worktree:

```
Worktree: <path>
  Branch: <name> (<merged|not merged> into <default>)
  Uncommitted: <N> file(s)
    <status summary>
```

Use AskUserQuestion:
> Worktree at `<path>` has uncommitted changes. Stash, skip, or chat?
>
> - **Stash** — `git -C <path> stash push -m "repo-tools stash <date>"`
> - **Skip** — leave it
> - **Chat** — show me the changes
> - **Stop** — stop cleaning this repo

#### Dry-run output for interactive items

In `--dry-run` mode, print the summaries but instead of asking, print:
```
  [needs input] <description of what would be asked>
```

### Step 6: Final Dashboard

After all repos have been processed, print a summary:

```
=== REPO TOOLS COMPLETE ===

Repos scanned: <N>

Auto-fixed:
  <N> dangling worktree ref(s) pruned
  <N> finished worktree(s) removed
  <N> stale branch(es) deleted
  <N> merged branch(es) deleted

Resolved interactively:
  <N> batch(es) committed
  <N> branch(es) deleted
  <N> worktree(s) stashed

Skipped:
  <N> batch(es) of uncommitted changes
  <N> inactive branch(es)
  <N> dirty worktree(s)

Status: <ALL CLEAN | <N> items skipped>
```

Omit sections where all counts are zero. If everything is clean across all repos:

```
=== REPO TOOLS COMPLETE ===

Repos scanned: <N>
Status: ALL CLEAN
```

For `--dry-run`, replace the header:

```
=== REPO TOOLS DRY RUN ===

Repos scanned: <N>

Would auto-fix:
  <counts...>

Needs input:
  <counts...>
```
