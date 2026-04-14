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
| `commit-push.py "msg" [--pr "title"]` | Stage changed files, commit, push, optionally create PR |
| `repo-state.py` | Session-start audit: branch, status, worktrees, staleness |
| `project-index.py [--filter X]` | Find projects by criteria (graphify, git, etc.) |
| `pr-status.py <num>` | PR summary: state, checks, diff, comments |
| `verify.py` | Tests + lint + type check + version bump validation |
| `branch-hygiene.py` | Stale, merged, remote-only, prunable |
| `usage-stats.py [--week]` | Token/cost stats from `~/.claude/usage.db` |
| `claude-fields.py <version>` | Dump stored version blob, diff fields |
| `graphify-status.py` | Which projects have graphify data |

All scripts support `--help`.
