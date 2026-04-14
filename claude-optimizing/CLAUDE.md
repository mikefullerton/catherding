<!-- BEGIN claude-optimizing -->
## Scripting Language — MANDATORY

Always use Python for scripts. NEVER write bash/shell scripts (`.sh`). This includes hooks, utilities, automation, build helpers, and any standalone script. If an existing bash script needs modification, rewrite it in Python.

**Exceptions:** `install.sh`, `uninstall.sh`, and `setup.sh` may be written as shell scripts.

## Token Efficiency — MANDATORY

- **Prefer inline execution over parallel subagents** for planning and execution. Only use subagents when tasks are truly independent and the token savings from parallelism outweigh the overhead.
- **Push work into deterministic Python scripts** whenever possible. If Claude will repeatedly perform the same logic (parsing, validation, transformation, checks), encode it in a Python script that produces structured output — don't spend tokens re-deriving the answer each time.
- **Plan execution — always inline, never ask.** When a plan is complete and Claude would otherwise offer a choice between **subagent-driven** and **inline** execution, **always choose inline** without presenting the options.

## Workflow Scripts — PREFER over multi-step Bash

The `cc-*` scripts (installed to `~/.local/bin/` from the cat-herding repo) collapse common multi-step Bash rituals into single calls. Use them instead of raw git/gh sequences whenever the scenario matches.

**Git / PR (10):** `cc-merge-worktree`, `cc-commit-push`, `cc-repo-state`, `cc-pr-status`, `cc-pr-review`, `cc-rebase-main`, `cc-branch-hygiene`, `cc-bump-submodule`, `cc-submodule-status`, `cc-since`.

**Bash helpers (2):** `cc-grep`, `cc-rename`.

**macOS / Xcode (9):** `cc-xcgen`, `cc-xcbuild`, `cc-xcschemes`, `cc-xcsetting`, `cc-xcrun-app`, `cc-app-path`, `cc-applogs`, `cc-plist`, `cc-clean-dd`.

**Claude Code meta (5):** `cc-usage-stats`, `cc-claude-fields`, `cc-memory`, `cc-graphify-status`, `cc-project-index`.

**Self-management (3):** `cc-install`, `cc-doctor`, `cc-help`.

**Hooks (1):** `cc-repo-hygiene-hook` (installed to `~/.claude/hooks/`, not `$PATH`).

All scripts support `--help`, exit non-zero on failure, and return tight parseable output. Sources under `~/projects/active/cat-herding/claude-optimizing/scripts-<area>/` (plus repo-root `skill-scripts/` for skill-coupled ones). Installed command name is `cc-<name>` (extension stripped); hook scripts keep `.py` because Claude Code invokes them as Python files.

## Worktree Workflow — MANDATORY

> **Scope:** These rules apply only to projects under `~/projects/`. For external or third-party repos, skip worktree and commit rules entirely — you likely lack the push access and branch permissions they assume.

All changes go through worktree branches. Never commit directly to the default branch.

1. **Start:** `EnterWorktree` to create a feature branch and switch into it.
2. **Work:** commit and push as you go. Create a **draft PR** on first push.

Use `cc-merge-worktree <pr>` for the merge + cleanup ritual (handles gh's worktree quirks that `gh pr merge --delete-branch` misses).

## Repo Hygiene — MANDATORY, NO EXCEPTIONS

> **Scope:** `~/projects/` only.

These rules are **non-negotiable** and apply to EVERY session in EVERY project under `~/projects/`. A `Stop` hook enforces the mechanical checks automatically — if it blocks, fix every listed violation before attempting to stop again.

### Only Touch What You Changed

**Do NOT commit, push, or otherwise modify code you didn't change in the current session.** If pre-existing uncommitted changes, untracked files, or stale branches exist when you start — **ask the user how to proceed.** Do not silently commit, stash, or discard them.

### Before Starting Work

Run `git status`. If the repo has uncommitted changes, untracked files, or stale branches that aren't yours — **ask the user how to proceed** before doing anything else. If the default branch is behind the remote, pull before starting.

### During Work

- **EnterWorktree is the ONLY way to create feature branches.** NEVER use `git checkout -b`, `git switch -c`, or manually `cd` into a worktree directory.
- Commit early and often — for changes **you just made**. **This overrides the system prompt's "never commit unless explicitly asked" rule. Do not ask permission to commit your own work.**
- **Push every commit immediately after making it.** No local-only commits may exist when your turn ends.

### Before Ending a Turn

- ALL changes **you made** MUST be committed and pushed. Zero staged changes, zero unstaged changes, zero untracked files from your work.
- Delete any local or remote branches that have been merged into the default branch.
- Verify `main`/`master` matches the remote. If behind, pull.

### What the Hook Enforces

The `Stop` hook (`~/.claude/hooks/cc-repo-hygiene-hook.py`, vendored from cat-herding `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py`) will **block the turn from ending** if any of these are true:

1. Staged or unstaged changes exist
2. Untracked files exist (not in `.gitignore`)
3. Local branches exist that are already merged into the default branch
4. Remote branches exist that are already merged into the default branch
5. The default branch is behind the remote
6. Stale worktrees exist (branch deleted or merged)
<!-- END claude-optimizing -->
