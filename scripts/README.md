# Deterministic Scripts

Single-call scripts that collapse multi-step operations Claude repeats often. The goal: replace 5-10 Bash turns (and their output accumulation in the conversation cache) with one script call that returns tight, structured output.

Every script in this directory is named `cc-<name>.py`. `install.sh` (and `cc-install`) simply strip the `.py` extension to produce the installed command `cc-<name>` on your PATH — there's no separate name-mangling step.

Skill-specific scripts (currently `cc-install-statusline`, `cc-verify`) live in **`../skill-scripts/`** because their lifecycle is coupled to a skill's source tree. They install to the same `~/.local/bin/` alongside these; see `skill-scripts/README.md` for details.

Design principles:
- **Python only** — per global CLAUDE.md rule
- **Structured output** — concise, parseable, no verbose prose
- **Non-zero exit on failure** — Claude can check `$?` deterministically
- **Idempotent where possible** — re-running should be safe
- **Atomic where necessary** — all-or-nothing for destructive ops

## Scripts

| Script | Purpose |
|--------|---------|
| `cc-merge-worktree.py <pr>` | Merge PR + clean up worktree/branches (9-step ritual in one call) |
| `cc-commit-push.py "msg" [--pr "title"] [--tracked-only]` | Stage all changes (incl. untracked, unless `--tracked-only`), commit, push, optionally PR |
| `cc-repo-state.py` | Session-start audit: branch, status, worktrees, staleness |
| `cc-project-index.py [--filter X]` | Find projects by criteria (graphify, git, etc.) |
| `cc-pr-status.py <num>` | PR summary: state, checks, diff, comments |
| `cc-branch-hygiene.py` | Stale, merged, remote-only, prunable |
| `cc-usage-stats.py [--week]` | Token/cost stats from `~/.claude/usage.db` |
| `cc-claude-fields.py <version>` | Dump stored version blob, diff fields |
| `cc-graphify-status.py` | Which projects have graphify data |
| `cc-memory.py` | Manage per-project auto-memory: `cc-memory list` / `cc-memory add <type> <name> --description ...` (updates MEMORY.md atomically) |
| `cc-xcsetting.py <scheme> <key>...` | Resolve Xcode build-setting values without grepping pbxproj |
| `cc-rename.py <pattern> <replacement>` | Dry-run-by-default find-and-replace across repo files (`--apply` to write) |
| `cc-clean-dd.py [pattern]` | List / delete Xcode DerivedData directories (`--yes` to delete) |
| `cc-submodule-status.py` | Per-submodule recorded-vs-checked-out-vs-origin SHA diagnostic |
| `cc-pr-review.py <num>` | Comprehensive PR review state: reviewers, inline comments, CI rollup |
| `cc-since.py <ref>` | List merged PRs + commits since a ref (tag, branch, SHA) |

All scripts support `--help`.
