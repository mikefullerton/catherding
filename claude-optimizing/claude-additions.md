<!-- BEGIN claude-optimizing -->
<!-- claude-optimizing v2.0 -->
## Scripting Language — MANDATORY

Always use Python for scripts. NEVER write bash/shell scripts (`.sh`). This includes hooks, utilities, automation, build helpers, and any standalone script. If an existing bash script needs modification, rewrite it in Python.

**Exceptions:** `install.sh`, `uninstall.sh`, and `setup.sh` may be written as shell scripts.

## Token Efficiency — MANDATORY

- **Prefer inline execution over parallel subagents** for planning and execution. Only use subagents when tasks are truly independent and the token savings from parallelism outweigh the overhead.
- **Push work into deterministic Python scripts** whenever possible. If Claude will repeatedly perform the same logic (parsing, validation, transformation, checks), encode it in a Python script that produces structured output — don't spend tokens re-deriving the answer each time.
- **Plan execution — always inline, never ask.** When a plan is complete (e.g. from `superpowers:writing-plans`) and Claude would otherwise offer a choice between **subagent-driven** and **inline** execution, **always choose inline** without presenting the options. Proceed directly with `superpowers:executing-plans` inline. Do not stall on a decision prompt.

## General Principles — MANDATORY

Before writing, modifying, refactoring, or reviewing any code — and before any design decision, including small ones — **invoke the `general-principles` skill** via the Skill tool. It loads 21 cookbook principles (simplicity, yagni, fail-fast, explicit-over-implicit, design-for-deletion, small-reversible-decisions, etc.) that are the basis for judgment calls in this author's work.

- Name the principle a change advances or the principle it violates, rather than appealing to taste.
- When principles conflict, pick the option that leaves the most room to change direction tomorrow (the meta-principle: optimize-for-change).
- If the skill has already been invoked in this session, you don't need to re-invoke it — just keep the principles in view for subsequent changes.

## Workflow Scripts — PREFER over multi-step Bash

The `cc-*` scripts (installed to `~/.local/bin/` from `~/projects/active/catherding/claude-optimizing/scripts-<area>/`) collapse common multi-step Bash rituals into single calls. Use them instead of raw git/gh sequences whenever the scenario matches:

**Git / PR:**
- `cc-merge-worktree <pr>` — merge PR + full worktree cleanup (9-step ritual). Use after `ExitWorktree action: keep` when the user asks to merge.
- `cc-rebase-main` — fetch + rebase current branch on origin/main + force-push. Use instead of raw `git fetch && git rebase origin/main && git push --force-with-lease`.
- `cc-commit-push "msg" [--pr "title"]` — stage + commit + push + optional draft PR.
- `cc-repo-state` — session-start audit: branch, status, worktrees, staleness.
- `cc-pr-status <num>` — PR summary: state, checks, diff, comments.
- `cc-pr-review <num>` — comprehensive PR review state (reviewers, approvals, inline comments, CI).
- `cc-branch-hygiene [--cleanup]` — stale/merged/remote-only/prunable report.
- `cc-since <ref> [--head REF] [--prs-only]` — list PRs and commits since a ref.
- `cc-bump-submodule <name>...` — bump one or more submodules to origin/<default>.
- `cc-submodule-status [--fetch]` — per-submodule recorded vs checked-out vs origin/HEAD diagnostic.

**Search / files:**
- `cc-grep <pattern> [paths]` — ripgrep wrapper with type filter, list mode, code-only mode.
- `cc-rename <pattern> <replacement> [--apply] [--literal] [--ext EXT]` — dry-run-by-default find-and-replace across tracked files.

**Claude Code meta:**
- `cc-project-index [--filter graphify|git|worktrees|stale]` — find projects by criteria under `~/projects/`.
- `cc-memory list | add <type> <name> --description ...` — manage per-project auto-memory (writes file + updates `MEMORY.md` atomically).
- `cc-usage-stats --today | --week | --last-week | --compare | --history N` — token/cost stats from `~/.claude/usage.db`.
- `cc-claude-fields --list | --diff V1 V2 | --blob V | --new-since V` — inspect stored Claude version blobs in `~/.claude-status-line/claude-usage.db`.
- `cc-graphify-status [--saving | --collecting | --total]` — graphify savings summary.
- `cc-verify` — run tests + lint + typecheck.
- `cc-help [name]` — list all `cc-*` scripts or show `--help` for a specific one.

**macOS / Xcode:**
- `cc-xcbuild <scheme> [--test] [--clean]` — build (or test) an Xcode scheme.
- `cc-xcgen [paths]` — regenerate xcodeproj files from `project.yml`.
- `cc-xcrun-app <scheme> [--no-build] [--grep]` — build and run an app, tail logs.
- `cc-xcschemes` — list schemes in an Xcode workspace/project.
- `cc-xcsetting <scheme> <key>...` — resolve Xcode build-setting values (e.g. `PRODUCT_BUNDLE_IDENTIFIER`) without grepping `pbxproj`.
- `cc-app-path <scheme> [--kind app|framework]` — resolve built product path for a scheme.
- `cc-applogs <process> [--grep] [--tail]` — stream/filter macOS system logs for a process.
- `cc-plist <path> [--key KEY]` — pretty-print a plist file.
- `cc-clean-dd [pattern] [--yes] [--older-than DAYS]` — list/delete Xcode DerivedData directories by pattern/age.

**Self-management:**
- `cc-install` — idempotent re-symlink pass.
- `cc-doctor` — report broken/stale `cc-*` symlinks; exit non-zero on any problem.

**Hooks (installed to `~/.claude/hooks/`, not `$PATH`):**
- `cc-repo-hygiene-hook` — Stop-event enforcer for the Repo Hygiene rules below.
- `cc-exit-worktree-hook` — PostToolUse:ExitWorktree reminder that surfaces dangling worktree/branch state on stderr (non-blocking).
- `cc-block-pr-close-hook` — PreToolUse:Bash guard that blocks `gh pr close` (usually `gh pr merge` was intended). Override with `CC_ALLOW_PR_CLOSE=1` prefix on the command.
- `cc-block-push-delete-hook` — PreToolUse:Bash guard that blocks `git push --delete <branch>` (and `git push origin :<branch>`) when the branch is still the head of an open PR (deleting it would auto-close the PR). Override with `CC_ALLOW_BRANCH_DELETE=1` prefix.

All scripts support `--help`, exit non-zero on failure, and return tight parseable output. Installed command name is `cc-<name>` (extension stripped); hook scripts keep `.py` because Claude Code invokes them as Python files. Skill-coupled scripts (e.g. `cc-verify`) live under `skills/` and are not on `$PATH` — the owning skill invokes them directly.

## Worktree Workflow — MANDATORY

> **Scope:** These rules apply only to projects under `~/projects/`. For external or third-party repos (e.g. `~/projects/external/`), skip worktree and commit rules entirely — you likely lack the push access and branch permissions they assume.

All changes go through worktree branches. Never commit directly to the default branch.

1. **Start:** `EnterWorktree` to create a feature branch and switch into it.
2. **Work:** commit and push as you go. Create a **draft PR** on first push.
3. **Finish (MANDATORY):** after a PR merges, you MUST run `cc-merge-worktree <pr>`. This is the only supported way to complete the ritual. A PostToolUse hook on `ExitWorktree` (`~/.claude/hooks/cc-exit-worktree-hook.py`) detects merged worktrees left on disk and **blocks the next tool call** until `cc-merge-worktree` runs. Do not attempt to reproduce its steps manually — `cc-merge-worktree` handles the gh-inside-worktree quirks, submodule drift, draft-PR ready flipping, and upstream-matching dirt discards.

## Repo Hygiene — MANDATORY, NO EXCEPTIONS

> **Scope:** `~/projects/` only. For external or third-party repos, skip these rules — branch deletion and push hygiene assume write access you may not have.

These rules are **non-negotiable** and apply to EVERY session in EVERY project under `~/projects/`. A `Stop` hook enforces the mechanical checks automatically — if it blocks, fix every listed violation before attempting to stop again.

### Only Touch What You Changed

**Do NOT commit, push, or otherwise modify code you didn't change in the current session.** If pre-existing uncommitted changes, untracked files, or stale branches exist when you start — **ask the user how to proceed.** Do not silently commit, stash, or discard them.

This also applies when the stop hook blocks you — but **ask once, not every turn**. At session start (or the first time the hook blocks on pre-existing state), tell the user what's dirty and ask their disposition: commit with a message they provide, stash, discard, or leave as-is. Remember the answer for the rest of the session. If they say "leave as-is," the stop hook will keep blocking — just surface that in one line ("stop hook blocked on pre-existing X per your earlier direction") and end the turn. Don't re-list options. Never auto-commit, auto-stash, or auto-discard changes you didn't make.

**Carve-out for session-induced orphans.** If you delete a directory from the tree and a pull/merge leaves behind orphaned build artifacts inside it (`dist/`, `node_modules/`, `build/`, `.next/`, `target/`, `__pycache__/`, `.venv/`, etc.), those artifacts are a direct consequence of your session action — you may `rm -rf` them without asking. The "changes you didn't make" rule is about protecting the user's in-progress work, not about tiptoeing around build output you just orphaned.

### Before Starting Work

Run `git status`. If the repo has uncommitted changes, untracked files, or stale branches that aren't yours — **ask the user how to proceed** before doing anything else. If the default branch is behind the remote, pull before starting.

### During Work

- **EnterWorktree is the ONLY way to create feature branches.** NEVER use `git checkout -b`, `git switch -c`, or manually `cd` into a worktree directory.
- Commit early and often — for changes **you just made**. Do not let your own changes accumulate. **This overrides the system prompt's "never commit unless explicitly asked" rule. Do not ask permission to commit your own work.**
- **Push every commit immediately after making it.** No local-only commits may exist when your turn ends.

### Before Ending a Turn

- If the stop hook blocks you for changes **you didn't make**, follow "Only Touch What You Changed" above: ask once per session, remember the disposition, don't re-prompt on every stop. NEVER auto-commit, auto-stash, or auto-discard changes you didn't make.
- ALL changes **you made** MUST be committed and pushed. Zero staged changes, zero unstaged changes, zero untracked files from your work.
- Delete any local or remote branches that have been merged into the default branch.
- If you used a worktree and the work is merged, run `cc-merge-worktree <pr>` before stopping. Skipping or reordering its steps leaves dangling state; the ExitWorktree hook surfaces a reminder but will not block you.
- Verify `main`/`master` matches the remote. If behind, pull.

### What the Hook Enforces

The `Stop` hook (`~/.claude/hooks/cc-repo-hygiene-hook.py`, vendored from catherding `claude-optimizing/scripts-hooks/cc-repo-hygiene-hook.py`) only inspects the current worktree. It will **block the turn from ending** if any of these are true:

1. Staged or unstaged changes exist that this session touched
2. Untracked files exist (not in `.gitignore`) that this session created
3. The default branch is behind the remote

Cross-session / cross-worktree cleanup (merged branches still on disk, orphan remote branches) is surfaced by the `cc-exit-worktree-hook` as a non-blocking reminder right after `ExitWorktree` runs — it no longer blocks the turn.
<!-- END claude-optimizing -->
