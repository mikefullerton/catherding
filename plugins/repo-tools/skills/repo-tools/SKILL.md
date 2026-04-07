---
name: repo-tools
description: "Recursive repository cleanup — auto-fixes obvious issues, interactively resolves the rest"
version: "4.0.0"
argument-hint: "<clean|--help> [--depth N] [--dry-run] [--version]"
allowed-tools: Read, Glob, Grep, Bash(python3 *, git *, gh *, ls *, rm *, test *, find *), AskUserQuestion
model: sonnet
---

# Repo Tools v4.0.0

Recursive repository cleanup — auto-fixes obvious issues, interactively resolves the rest.

## Startup

If `$ARGUMENTS` is `--version`, respond with exactly:
> repo-tools v4.0.0

Then stop.

**CRITICAL**: Print the version line first:

repo-tools v4.0.0

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
> - Fetches remote and prunes stale tracking refs
> - Pulls if behind remote (fast-forward only, skipped if uncommitted changes)
> - Pushes if ahead of remote
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

### Phase 1: Discover repos

```bash
python3 $SKILL_DIR/references/discover.py <ROOT> [--depth N]
```

Where `<ROOT>` is the current working directory (`.`), and `--depth` is forwarded from the user's arguments.

Parse the JSON output — an array of `{repo, path}` objects. Print:

```
Found <total> repos to process:
  active/cat-herding
  active/my-app
  archive/old-thing
```

Use paths relative to `~/projects` (strip the `~/projects/` prefix from the absolute path).

If no repos found, print "No git repositories found." and stop.

### Phase 2: Deterministic pass

Print:

```
Starting deterministic pass:
```

For each repo (index `i`, starting at 1):

1. Update the status line progress:
```bash
~/.claude-status-line/progress/update-progress.sh "repo-tools clean" "<relative-path>" <i> <total>
```

2. Print a header:
```
Processing <relative-path> (<i> of <total>)
```

3. Run the script:
```bash
python3 $SKILL_DIR/references/process-repo.py <repo-path> [--dry-run]
```

Forward `--dry-run` from the user's arguments.

4. The script prints step-by-step progress to stderr. **You must read this output and print it verbatim** so the user sees exactly what happened. The output looks like:

```
  Fetching remote...
  Fetched
  Checking for uncommitted changes: 3 found
  Pull: up to date
  Push: up to date
  Branches: 2 non-default (feature/old, hotfix/done)
  Evaluating branch feature/old: stale (remote gone)
    Deleted stale branch feature/old
  Evaluating branch hotfix/done: merged into main
    Deleted merged branch hotfix/done
```

5. Parse the JSON from stdout. Collect all results into an array.

6. Print a footer:
```
Finished processing <relative-path> (<i> of <total>)
```

The JSON output has this structure:

```json
{
  "repo": "my-project",
  "path": "/Users/me/projects/my-project",
  "default_branch": "main",
  "branch": "feature/foo",
  "needs_push": false,
  "needs_pull": false,
  "branches": ["feature/foo"],
  "auto_fixed": {
    "worktree_refs_pruned": 0,
    "worktrees_removed": 1,
    "stale_branches_deleted": 2,
    "merged_branches_deleted": 1
  },
  "items": [
    {"type": "uncommitted", "files": [...]},
    {"type": "inactive_branch", "branch": "old-feature", ...},
    {"type": "dirty_worktree", "path": "/path/to/wt", ...}
  ]
}
```

After all repos are processed, clear the progress:
```bash
~/.claude-status-line/progress/update-progress.sh --clear
```

### Phase 3: Status chart

After all repos are processed, print a chart showing every repo's status:

```
=== REPO STATUS ===

active/cat-herding            5 uncommitted files, 2 inactive branches, needs pull
active/my-app                 1 dirty worktree (wip-branch), needs push
active/other-project          clean
archive/old-thing             3 inactive branches, 2 branches (feature/x, hotfix/y)
```

Format rules:
- Path column: left-aligned, relative to `~/projects`
- Status column: left-aligned, comma-separated list of issues
- For uncommitted: `<N> uncommitted file(s)`
- For inactive branches: `<N> inactive branch(es)`
- For dirty worktrees: `<N> dirty worktree(s) (<branch names>)`
- For needs_push: `needs push`
- For needs_pull: `needs pull`
- For branches (non-default): `<N> branch(es) (<names>)`
- For clean repos (no issues, no branches, no push/pull needed): `clean`
- Sort: repos with issues first, then clean repos

If `--dry-run`, print the chart and stop — do not enter Phase 4.

If all repos are clean, print the chart (all showing "clean") and skip to **Phase 5** (dashboard).

Otherwise, count repos with non-empty `items` and use AskUserQuestion:
> **<N> item(s) across <M> repo(s) need decisions.** Continue?
>
> - **Continue** — walk through each repo interactively
> - **Stop** — skip interactive fixes and go to the dashboard

If **Stop**, skip to **Phase 5** (dashboard).

### Phase 4: Interactive decisions

Walk the collected results array, skipping repos with empty `items`. For each repo with items, print:

```
--- <path> (<branch>) ---
```

Then process each item in the repo's `items` array:

#### Uncommitted changes (`type: "uncommitted"`)

The `files` array contains `{status, path}` objects. Group them into **smart batches** using:

1. **Directory affinity** — files in the same directory or subtree
2. **Change type** — new files together, modifications together
3. **Naming patterns** — test files batch together, config files batch together, source files in the same module batch together

For each batch:
1. Generate a short description (e.g., "New test files for auth module")
2. List the files with their status
3. For modified files, run `git -C <repo-path> diff --stat <file>` to get line counts

Present each batch:

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
git -C <path> push
```

If the push fails (e.g., no upstream), set upstream and retry:
```bash
git -C <path> push -u origin <current-branch>
```

If **Chat**: show `git diff` for the batch files and discuss. After discussion, re-offer the commit/skip/stop options.

#### Inactive branches (`type: "inactive_branch"`)

Present using the item's fields:

```
Branch: <branch>
  Last commit: <last_commit_age>
  Message: "<last_commit_subject>"
  Changes: <commits_ahead> commits ahead of <default_branch> — <diff_stat>
```

Use AskUserQuestion:
> Branch `<branch>` — <last_commit_age>, <commits_ahead> commits not merged. "<last_commit_subject>". Delete, skip, or chat?
>
> - **Delete** — `git branch -d` (safe delete; will warn if not fully merged)
> - **Skip** — leave it
> - **Chat** — show me more detail about this branch
> - **Stop** — stop cleaning this repo

If **Delete** and `-d` fails (not merged), report the error and ask:
> Safe delete failed — branch is not fully merged. Force-delete with `git branch -D`?

If **Chat**: show `git log --oneline <default>..<branch>` and `git diff --stat <default>...<branch>`, then re-offer options.

#### Dirty worktrees (`type: "dirty_worktree"`)

Present:

```
Worktree: <path>
  Branch: <branch> (<merged|not merged> into <default_branch>)
  Uncommitted: <file count from status>
    <status>
```

Use AskUserQuestion:
> Worktree at `<path>` has uncommitted changes. Stash, skip, or chat?
>
> - **Stash** — `git -C <path> stash push -m "repo-tools stash <date>"`
> - **Skip** — leave it
> - **Chat** — show me the changes
> - **Stop** — stop cleaning this repo

#### Handling "Stop"

If the user says **Stop** on any item, skip all remaining items for that repo and move to the next repo.

### Phase 5: Final Dashboard

After all repos have been processed, print a summary. Aggregate `auto_fixed` counts across all repo results, plus your own tracking of interactive resolutions:

```
=== REPO TOOLS COMPLETE ===

Repos scanned: <N>

Auto-fixed:
  <N> dangling worktree ref(s) pruned
  <N> finished worktree(s) removed
  <N> stale branch(es) deleted
  <N> merged branch(es) deleted
  <N> push(es)

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
