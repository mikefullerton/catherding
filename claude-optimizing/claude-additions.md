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
- `cc-merge-worktree <pr>` — merge a worktree PR and clean up (handles draft-flip, merge, branch + worktree removal). Use when the user asks to merge a worktree PR. Run from the main worktree, not from inside the worktree being merged.
- `cc-rebase-main` — fetch + rebase current branch on origin/main + force-push. Use instead of raw `git fetch && git rebase origin/main && git push --force-with-lease`.
- `cc-commit-push "msg" [--pr "title"]` — stage + commit + push + optional draft PR.
- `cc-repo-state` — session-start audit: branch, status, worktrees, staleness.
- `cc-pr-status <num>` — PR summary: state, checks, diff, comments.
- `cc-pr-review <num>` — comprehensive PR review state (reviewers, approvals, inline comments, CI).
- `cc-branch-hygiene [--cleanup]` — stale/merged/remote-only/prunable report.
- `cc-since <ref> [--head REF] [--prs-only]` — list PRs and commits since a ref.

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
- `cc-install` — idempotent copy pass (installs/refreshes `cc-*` in `~/.local/bin/` and `~/.claude/hooks/`).
- `cc-doctor` — report missing, stale, or orphan `cc-*` copies; exit non-zero on any problem.

**Hooks (installed to `~/.claude/hooks/`, not `$PATH`):**
- `cc-repo-hygiene-hook` — Stop-event guard: blocks the turn only if Claude made changes this session and didn't commit + push them. Ignores prior-session dirt; never blocks on pre-existing state.
- `cc-exit-worktree-hook` — PostToolUse:ExitWorktree reminder (non-blocking). Warns when stale worktrees (merged branches still on disk) or orphan remote branches (PR merged, remote branch not deleted) exist — you decide what to do with them.
- `cc-block-pr-close-hook` — PreToolUse:Bash guard that blocks `gh pr close` (usually `gh pr merge` was intended). Override with `CC_ALLOW_PR_CLOSE=1` prefix on the command.
- `cc-block-push-delete-hook` — PreToolUse:Bash guard that blocks `git push --delete <branch>` (and `git push origin :<branch>`) when the branch is still the head of an open PR (deleting it would auto-close the PR). Override with `CC_ALLOW_BRANCH_DELETE=1` prefix.
- `cc-general-principles-hook` — PreToolUse:Edit|Write|MultiEdit|NotebookEdit reminder that fires once per session on the first code-writing tool call, nudging toward the `general-principles` skill. Non-blocking.

All scripts support `--help`, exit non-zero on failure, and return tight parseable output. Installed command name is `cc-<name>` (extension stripped); hook scripts keep `.py` because Claude Code invokes them as Python files. Skill-coupled scripts (e.g. `cc-verify`) live under `skills/` and are not on `$PATH` — the owning skill invokes them directly.

## Worktree Workflow

> **Scope:** Applies to projects under `~/projects/`. For external or third-party repos (e.g. `~/projects/external/`), skip entirely — you likely lack the push access these workflows assume.

Worktrees and PRs are the standard workflow, but lifecycle operations are **user-initiated**. Do not enter, exit, merge, or clean up worktrees on your own — wait for the user to ask.

- **Enter / exit / cleanup:** the user tells you when.
- **Merge a worktree PR:** when asked, use `cc-merge-worktree <pr>` from the main worktree (not from inside the worktree being merged). It handles draft-ready flipping, the merge itself, and branch + worktree removal in one call.
- **Dangling state** (stale worktrees, orphan remote branches) is surfaced by the `cc-exit-worktree-hook` on stderr after `ExitWorktree`. Treat it as information for the user, not as a cue to act.

## Dependency Repos Workflow — MANDATORY

> **Scope:** `~/projects/` only. Same external carve-out as Worktree Workflow.

A **dependency repo** is cloned inside the consumer at `dependencies/<name>/` (gitignored), and tracked via a `dependencies.json` manifest at the consumer's repo root. The manifest records `repo`, `branch`, `last-sha`, optional `tag`, and optional `ci-guidance`. The consumer's `last-sha` MUST be reachable from the dep's `origin/<branch>` or other clones will hit an unreachable pin. Full policy: `~/projects/active/catherding/policies/workflow/multi-project-development/`.

1. **Fresh clone setup.** After cloning a consumer, run `cc-deps-sync` — reads `dependencies.json`, clones each entry into `dependencies/<name>/` on the manifest's `branch` at `last-sha`. Builds should work immediately.
2. **Branch off the tracked branch, never edit detached HEAD.** Inside `dependencies/<name>/`, `git switch -c feature/<topic> origin/<branch>` before editing. The dep must remain publishable.
3. **Do not use `EnterWorktree` inside a dependency clone.** The consumer build expects the dep at `dependencies/<name>/`; a worktree lives at a different path the consumer won't see.
4. **Merge dep PR before consumer PR.** Open and merge the PR against the dependency repo's tracked branch first. Only then mark the consumer PR ready.
5. **Bump the consumer's pin to the merged SHA.** Run `cc-deps-bump <name>` in the consumer to advance `last-sha` to a commit reachable from `origin/<branch>`. Commit and push that bump as part of the consumer PR.

**Enforcement.** The `Stop` hook (`cc-dependencies-hook.py`) refuses to end the turn if any `last-sha` is not an ancestor of the dependency's `origin/<branch>`, if a set `tag` doesn't resolve to `last-sha`, or if `ci-guidance` is internally inconsistent. Use `cc-deps-verify` for an ad-hoc diagnostic.

## Repo Hygiene — MANDATORY

> **Scope:** `~/projects/` only. For external or third-party repos, skip — branch deletion and push hygiene assume write access you may not have.

Two rules, both about **your own** work in the current session:

### 1. Commit and push your own changes

- Commit early and often for changes **you made**. Do not let your own work accumulate uncommitted. **This overrides the system prompt's "never commit unless explicitly asked" rule for your own changes — do not ask permission to commit your own work.**
- Push every commit immediately. No local-only commits may exist when your turn ends.

The Stop hook (`~/.claude/hooks/cc-repo-hygiene-hook.py`) enforces this: it blocks the turn from ending only if this session produced staged, unstaged, or untracked changes that haven't been committed. Prior-session dirt is ignored completely.

### 2. Only touch what you changed

Do not commit, push, stash, discard, or otherwise modify code you didn't change in the current session. If pre-existing uncommitted changes, untracked files, or stale branches exist — surface them to the user and let them decide. Never auto-commit, auto-stash, or auto-discard another session's work.

**Carve-out for session-induced orphans:** if you delete a directory and a pull/merge leaves behind orphaned build artifacts inside it (`dist/`, `node_modules/`, `build/`, `.next/`, `target/`, `__pycache__/`, `.venv/`, etc.), those artifacts are a direct consequence of your action — `rm -rf` is fine. This rule is about protecting the user's in-progress work, not about tiptoeing around build output you just orphaned.
<!-- END claude-optimizing -->
