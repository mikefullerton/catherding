---
name: repo-tools
description: "Recursive repository cleanup — auto-fixes obvious issues, interactively resolves the rest"
version: "3.0.0"
argument-hint: "<clean|--help> [--depth N] [--dry-run] [--version]"
allowed-tools: Read, Glob, Grep, Bash(python3 *, git *, gh *, ls *, rm *, test *, find *), AskUserQuestion
model: sonnet
---

# Repo Tools v3.0.0

Recursive repository cleanup — auto-fixes obvious issues, interactively resolves the rest.

## Startup

If `$ARGUMENTS` is `--version`, respond with exactly:
> repo-tools v3.0.0

Then stop.

**CRITICAL**: Print the version line first:

repo-tools v3.0.0

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
> - Pushes unpushed commits on the current branch
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

### Phase 1: Run the deterministic cleanup script

Build the command from `$ARGUMENTS`:

```bash
python3 $SKILL_DIR/references/clean.py <ROOT> [--depth N] [--dry-run]
```

Where `<ROOT>` is the current working directory (`.`), and `--depth` / `--dry-run` are forwarded from the user's arguments.

The script:
1. Discovers all git repos (respecting `--depth`)
2. For each repo: fetches, prunes worktree refs, deletes gone and merged branches, removes finished worktrees, pushes unpushed commits
3. Prints human-readable progress to stderr (you will see it)
4. Prints a JSON manifest to stdout with the structure:

```json
{
  "repos_scanned": 5,
  "auto_fixed": {
    "worktree_refs_pruned": 2,
    "worktrees_removed": 1,
    "stale_branches_deleted": 3,
    "merged_branches_deleted": 1,
    "pushes": 2
  },
  "interactive": [
    {
      "repo": "my-project",
      "path": "/Users/me/projects/my-project",
      "default_branch": "main",
      "branch": "feature/foo",
      "items": [
        {"type": "uncommitted", "files": [{"status": " M", "path": "src/app.py"}, ...]},
        {"type": "inactive_branch", "branch": "old-feature", "last_commit_age": "45 days ago", ...},
        {"type": "dirty_worktree", "path": "/path/to/wt", "branch": "wip", "merged": false, "status": "..."}
      ]
    }
  ]
}
```

**Parse the JSON output.** If `interactive` is empty, skip to **Phase 3** (dashboard). Otherwise proceed to **Phase 2**.

If `--dry-run` was set, the script already reported everything as `[dry-run]`. Print the dashboard from the JSON counts (using the dry-run format) and stop — do not enter Phase 2.

### Phase 2: Interactive decisions

Walk the `interactive` array repo by repo. For each repo, print:

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

### Phase 3: Final Dashboard

After all repos have been processed, print a summary. Use the counts from the script's JSON `auto_fixed` plus your own tracking of interactive resolutions:

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
