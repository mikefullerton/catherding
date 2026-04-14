# Deterministic Scripts

Single-call scripts that collapse multi-step operations Claude repeats often. The goal: replace 5-10 Bash turns (and their output accumulation in the conversation cache) with one script call that returns tight, structured output.

Design principles:
- **Python only** — per global CLAUDE.md rule
- **Structured output** — concise, parseable, no verbose prose
- **Non-zero exit on failure** — Claude can check `$?` deterministically
- **Idempotent where possible** — re-running should be safe
- **Atomic where necessary** — all-or-nothing for destructive ops

## Scripts

| Script | Purpose |
|--------|---------|
| `merge-worktree.py <pr>` | Merge PR + clean up worktree/branches (9-step ritual in one call) |
| `install-statusline.py` | Copy status line files, clear pycache, run tests |
| `commit-push.py "msg" [--pr "title"] [--tracked-only]` | Stage all changes (incl. untracked, unless `--tracked-only`), commit, push, optionally PR |
| `repo-state.py` | Session-start audit: branch, status, worktrees, staleness |
| `project-index.py [--filter X]` | Find projects by criteria (graphify, git, etc.) |
| `pr-status.py <num>` | PR summary: state, checks, diff, comments |
| `verify.py` | Tests + lint + type check + version bump validation |
| `branch-hygiene.py` | Stale, merged, remote-only, prunable |
| `usage-stats.py [--week]` | Token/cost stats from `~/.claude/usage.db` |
| `claude-fields.py <version>` | Dump stored version blob, diff fields |
| `graphify-status.py` | Which projects have graphify data |
| `memory.py` | Manage per-project auto-memory: `cc-memory list` / `cc-memory add <type> <name> --description ...` (updates MEMORY.md atomically) |
| `xcsetting.py <scheme> <key>...` | Resolve Xcode build-setting values without grepping pbxproj |
| `rename.py <pattern> <replacement>` | Dry-run-by-default find-and-replace across repo files (`--apply` to write) |
| `clean-dd.py [pattern]` | List / delete Xcode DerivedData directories (`--yes` to delete) |
| `submodule-status.py` | Per-submodule recorded-vs-checked-out-vs-origin SHA diagnostic |
| `pr-review.py <num>` | Comprehensive PR review state: reviewers, inline comments, CI rollup |
| `since.py <ref>` | List merged PRs + commits since a ref (tag, branch, SHA) |

All scripts support `--help`.
