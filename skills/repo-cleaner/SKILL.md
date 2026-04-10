---
name: repo-cleaner
description: "Recursive repository cleanup — auto-fixes obvious issues, interactively resolves the rest"
version: "5.0.0"
argument-hint: "<clean|--help> [--depth N] [--dry-run] [--version]"
allowed-tools: Read, Glob, Grep, Bash(python3 *, git *, gh *, ls *, rm *, test *, find *), AskUserQuestion
model: sonnet
---

# Repo Cleaner v5.0.0

Recursive repository cleanup — auto-fixes obvious issues, interactively resolves the rest.

## Startup

If `$ARGUMENTS` is `--version`, respond with exactly:
> repo-cleaner v5.0.0

Then stop.

**CRITICAL**: Print the version line first:

repo-cleaner v5.0.0

## Route by argument

| Argument | Action |
|----------|--------|
| `clean` | Go to **Clean** section (pass remaining args) |
| `clean --dry-run` | Go to **Clean** section in dry-run mode |
| `clean --depth N` | Go to **Clean** section with custom depth |
| `--help` | Go to **Help** section |
| *(empty or anything else)* | Print usage and stop: `Usage: /repo-cleaner <clean\|--help> [--depth N] [--dry-run] [--version]` |

---

## Help

Print the following exactly, then stop:

> ## Repo Tools
>
> Recursive repository cleanup — auto-fixes obvious issues, interactively resolves the rest.
>
> **Usage:** `/repo-cleaner <clean|--help> [--depth N] [--dry-run] [--version]`
>
> ### Commands
>
> **`/repo-cleaner clean`** — Discover and clean git repos
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
> - Unresolved pull/push — offers to pull or push when deterministic pass couldn't
> - Non-default branches — shows change summary and last commit, offers: delete, skip, or chat
> - Dirty worktrees — summarizes contents, offers: stash, skip, or chat
>
> After processing all repos, prints a final dashboard summarizing everything done.
>
> **`/repo-cleaner clean --dry-run`** — Preview without changing anything
>
> Walks the full tree and reports what would be auto-fixed and what would need input, but makes no changes.
>
> **`/repo-cleaner clean --depth N`** — Set discovery depth (default: 3)
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

### Phase 1: Discover and process

Run the single clean script:

```bash
python3 $SKILL_DIR/references/clean.py <ROOT> [--depth N] [--dry-run]
```

Where `<ROOT>` is the current working directory (`.`), and `--depth` / `--dry-run` are forwarded from the user's arguments.

The script:
1. Discovers all git repos (respecting `--depth`, skipping `-test`/`-tests` dirs)
2. Runs a fast local pre-check on each, skipping repos that are already clean
3. Processes repos needing work **in parallel** (6 workers): fetch, pull/push, worktrees, branches
4. Streams per-repo progress to stderr as each repo completes
5. Outputs a JSON manifest to stdout

**You must read the stderr output and print it verbatim** — it contains the per-repo transcripts the user needs to see. The output looks like:

```
  cat-herding: 2 uncommitted, 3 remote branch(es)
  temporal: 1 local branch(es), 7 remote branch(es)

32 repos found, 13 need processing, 19 clean

Processing cat-herding (1/13)
  Fetching remote...
  Fetched
  Checking for uncommitted changes: 2 found
  Branches: only default branch
Finished cat-herding (1/13) — 1 need attention

Processing temporal (2/13)
  Fetching remote...
  Fetched
  Evaluating branch old-feature: squash-merged into main
    Deleted squash-merged branch old-feature
Finished temporal (2/13) — 1 auto-fixed
```

Parse the JSON from stdout:

```json
{
  "all": [{"repo": "cat-herding", "path": "/Users/me/projects/active/cat-herding"}, ...],
  "total": 32,
  "clean": 19,
  "processed": 13,
  "results": [
    {
      "repo": "cat-herding",
      "path": "/Users/me/projects/active/cat-herding",
      "default_branch": "main",
      "branch": "main",
      "needs_push": false,
      "needs_pull": false,
      "branches": [],
      "auto_fixed": {"worktree_refs_pruned": 0, "worktrees_removed": 0, "stale_branches_deleted": 0, "merged_branches_deleted": 0},
      "items": [{"type": "uncommitted", "files": [...]}, ...]
    }
  ]
}
```

If no repos found, print "No git repositories found." and stop.

If `results` is empty (all repos were clean at pre-check), print "All <total> repos clean — nothing to do." and stop.

### Phase 2: Status chart

After the script completes, print a chart showing every repo's status. Use `results` for processed repos and `all` for the full list (repos not in results are clean):

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
- For branches needing decision: `<N> branch(es) to review`
- For dirty worktrees: `<N> dirty worktree(s) (<branch names>)`
- For needs_push: `needs push`
- For needs_pull: `needs pull`
- For clean repos (no issues at all): `clean`
- Sort: repos with issues first, then clean repos

If `--dry-run`, print the chart and stop — do not enter Phase 3.

If all repos are clean, print the chart (all showing "clean") and skip to **Phase 4** (dashboard).

Otherwise, count repos with non-empty `items` and use AskUserQuestion:
> **<N> item(s) across <M> repo(s) need decisions.** Continue?
>
> - **Continue** — walk through each repo interactively
> - **Stop** — skip interactive fixes and go to the dashboard

If **Stop**, skip to **Phase 4** (dashboard).

### Phase 3: Interactive decisions

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
> **[<repo-name>]** <description> — <N> file(s). Commit or chat?
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

#### Needs pull (`type: "needs_pull"`)

The current branch is behind its remote upstream. This was skipped during the deterministic pass (likely because of uncommitted changes or a non-fast-forward situation).

Use AskUserQuestion:
> **[<repo-name>]** Current branch is behind remote. Pull, skip, or chat?
>
> - **Pull** — `git -C <path> pull --ff-only`
> - **Skip** — leave it
> - **Stop** — stop cleaning this repo

If pull fails (not fast-forward), report the error and suggest `git pull --rebase` or manual resolution.

#### Needs push (`type: "needs_push"`)

The current branch has unpushed commits.

Use AskUserQuestion:
> **[<repo-name>]** Current branch has unpushed commits. Push, skip, or chat?
>
> - **Push** — `git -C <path> push` (set upstream with `-u origin <branch>` if needed)
> - **Skip** — leave it
> - **Stop** — stop cleaning this repo

#### Branches (`type: "branch"`)

Every non-default, non-special branch is flagged — both local and remote-only. Special branches (`gh-pages`, `github-pages`) are always kept. Merged remote-only branches are auto-deleted during the deterministic pass.

Check the `remote_only` field to determine the branch location.

**Local branches** (`remote_only` is absent or false):

```
Branch: <branch> (local)
  Last commit: <last_commit_age>
  Message: "<last_commit_subject>"
  Changes: <commits_ahead> commits ahead of <default_branch> — <diff_stat>
```

Use AskUserQuestion:
> **[<repo-name>]** Branch `<branch>` — <last_commit_age>, <commits_ahead> commits not merged. "<last_commit_subject>". Delete, skip, or chat?
>
> - **Delete** — `git branch -d` (safe delete; will warn if not fully merged)
> - **Skip** — leave it (e.g., WIP branch you're still using)
> - **Chat** — show me more detail about this branch
> - **Stop** — stop cleaning this repo

If **Delete** and `-d` fails (not merged), report the error and ask:
> Safe delete failed — branch is not fully merged. Force-delete with `git branch -D`?

If **Chat**: show `git log --oneline <default>..<branch>` and `git diff --stat <default>...<branch>`, then re-offer options.

**Remote-only branches** (`remote_only` is true):

```
Branch: <branch> (remote only)
  Last commit: <last_commit_age>
  Message: "<last_commit_subject>"
  Changes: <commits_ahead> commits ahead of <default_branch> — <diff_stat>
```

Use AskUserQuestion:
> **[<repo-name>]** Remote branch `<branch>` — <last_commit_age>, <commits_ahead> commits not merged. "<last_commit_subject>". Delete, skip, or chat?
>
> - **Delete** — `git push origin --delete <branch>`
> - **Skip** — leave it
> - **Chat** — show me more detail about this branch
> - **Stop** — stop cleaning this repo

If **Chat**: show `git log --oneline <default>..origin/<branch>` and `git diff --stat <default>...origin/<branch>`, then re-offer options.

#### Dirty worktrees (`type: "dirty_worktree"`)

Present:

```
Worktree: <path>
  Branch: <branch> (<merged|not merged> into <default_branch>)
  Uncommitted: <file count from status>
    <status>
```

Use AskUserQuestion:
> **[<repo-name>]** Worktree at `<path>` has uncommitted changes. Stash, skip, or chat?
>
> - **Stash** — `git -C <path> stash push -m "repo-cleaner stash <date>"`
> - **Skip** — leave it
> - **Chat** — show me the changes
> - **Stop** — stop cleaning this repo

#### Handling "Stop"

If the user says **Stop** on any item, skip all remaining items for that repo and move to the next repo.

### Phase 4: Final Dashboard

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
  <N> branch(es)
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
