# claude-optimizing

A self-contained Claude-Code tooling layer. One installer deploys everything needed to make git-and-bash workflow under Claude Code disciplined, fast, and reproducible across machines.

## What's in this directory

```
claude-optimizing/
├── README.md             ← you are here
├── install.sh            ← idempotent installer (see "How install.sh works")
├── uninstall.sh          ← reverses everything install.sh did
├── claude-additions.md   ← guidance block — merged into ~/.claude/CLAUDE.md
├── scripts-git/    (10)  ← git / PR workflow
├── scripts-bash/    (2)  ← shell helpers
├── scripts-xcode/   (9)  ← macOS / Xcode
├── scripts-claude/  (3)  ← Claude Code meta
├── scripts-meta/    (3)  ← self-management (cc-install, cc-doctor, cc-help)
└── scripts-hooks/   (1)  ← Claude Code hook scripts (cc-*-hook.py)
```

Not in this directory but installed alongside:
- [`../skill-scripts/`](../skill-scripts/) — 2 skill-coupled scripts (`cc-install-statusline`, `cc-verify`) whose lifecycle tracks a skill in `../skills/`. The installer picks them up automatically.

## Design principles

- **Python only** for scripts (no `.sh` except `install.sh` / `uninstall.sh`).
- **Structured output** — concise, parseable, no verbose prose.
- **Non-zero exit on failure** — callers can check `$?` deterministically.
- **Idempotent where possible** — every script is safe to re-run.
- **Atomic where necessary** — all-or-nothing for destructive ops.

## Naming conventions

- Every source file is `cc-<name>.py`. The installer strips `.py` to produce the installed command `cc-<name>` on `$PATH`.
- Files ending in `-hook` (e.g. `cc-repo-hygiene-hook.py`) are Claude Code hooks. They **keep** the `.py` extension and install into `~/.claude/hooks/` instead of `~/.local/bin/`, because Claude Code invokes them as Python files via its hook protocol.
- Categories are named `scripts-<area>/`. Adding a new one is zero-friction: the installers glob `claude-optimizing/scripts-*/`.

## How `install.sh` works

Runs five idempotent steps, each labelled in its output:

| Step | Effect |
|---|---|
| 0. Prereq check | Verifies `git`, `gh`, `python3` are on `PATH`; warns if `~/.local/bin` isn't on `PATH`; exits non-zero if anything is missing. |
| 1. Symlink `cc-*` scripts | `ln -sfn` every `claude-optimizing/scripts-*/cc-*.py` and every `../skill-scripts/cc-*.py` into `~/.local/bin/`. `cc-*-hook.py` files route to `~/.claude/hooks/` instead. |
| 2. Register Stop hook | Patches `~/.claude/settings.json` — appends `/usr/bin/python3 $HOME/.claude/hooks/cc-repo-hygiene-hook.py` under `hooks.Stop`, unless already present. |
| 3. Merge guidance block | Reads `claude-additions.md` and inserts it into `~/.claude/CLAUDE.md` between `<!-- BEGIN claude-optimizing -->` / `<!-- END claude-optimizing -->` markers. On re-run, replaces the block in place. |
| 4. Activate pre-commit | `git config core.hooksPath .githooks` in the containing repo, so committed `cc-*` scripts get `py_compile`-checked before the commit lands. |
| 5. Verify | Runs `cc-doctor` if available; prints a clean-up summary. |

`uninstall.sh` reverses each step and is similarly idempotent. It only removes symlinks that actually point into this tree (plus the repo-root `skill-scripts/`), so other installs on the same machine are untouched.

## The script catalog

Every script supports `--help`. Exit codes are always meaningful.

### Git / PR workflow — `scripts-git/` (10)

| Command | Purpose |
|---|---|
| `cc-merge-worktree <pr>` | Full 9-step PR merge + worktree/branch cleanup (auto-switches to main worktree, marks draft PRs ready, discards upstream-identical dirt, handles drifted submodules). |
| `cc-commit-push "msg" [--pr TITLE] [--tracked-only]` | Stage-all → commit → push → optional draft PR. Prints staged-file count so no follow-up `git status` is needed. |
| `cc-repo-state` | Session-start audit: branch, status, worktrees, staleness, drifted submodules, default-branch lag. |
| `cc-pr-status <num>` / `cc-pr-review <num>` | Compact PR summary (state, checks, diff, comments) / full review state (reviewers, inline comments, CI rollup). |
| `cc-rebase-main` | Fetch + rebase onto `origin/<default>` + force-push-with-lease. |
| `cc-branch-hygiene [--cleanup]` | Stale / merged / remote-only / prunable report. |
| `cc-bump-submodule <path>...` | Bump submodules to tip of `origin/<default>`. |
| `cc-submodule-status` | Per-submodule recorded-vs-checked-out-vs-origin diff. |
| `cc-since <ref>` | List merged PRs + commits since a tag/branch/SHA. |

### Shell helpers — `scripts-bash/` (2)

| Command | Purpose |
|---|---|
| `cc-grep <pattern>` | `rg` with sensible excludes (node_modules, build artifacts, etc.). |
| `cc-rename <pattern> <replacement>` | Dry-run-by-default find-and-replace across repo files (`--apply` to write). |

### Claude Code meta — `scripts-claude/` (3)

| Command | Purpose |
|---|---|
| `cc-usage-stats [--today\|--week\|--last-week\|--compare\|--history N]` | Token / cost stats from `~/.claude/usage.db`. |
| `cc-memory list` / `cc-memory add <type> <name> --description ...` | Manage per-project auto-memory (writes file + updates `MEMORY.md` atomically). |
| `cc-project-index [--filter graphify\|git\|worktrees\|stale]` | Find projects under `~/projects/` by criteria. |

Two cc-* commands in the same namespace — `cc-claude-fields` and `cc-graphify-status` — are installed by the [graphify](~/projects/external/graphify) project, not by this repo. They read state the graphify pipeline populates and are managed by graphify's own installer. `cc-doctor` ignores any cc-* symlink whose target sits outside this repo, so those two entries won't show up as stale here.

### macOS / Xcode — `scripts-xcode/` (9)

| Command | Purpose |
|---|---|
| `cc-xcgen` | `xcodegen generate` in every dir under the repo that has a `project.yml`. |
| `cc-xcbuild` | `xcodebuild build` or `test` with compact output. |
| `cc-xcschemes` | List schemes in an Xcode workspace or project. |
| `cc-xcsetting <scheme> <key>...` | Resolved Xcode build-setting values without grepping pbxproj. |
| `cc-xcrun-app` | Build, launch, and tail logs for a macOS app target. |
| `cc-app-path` | Most recent `.app` or `.framework` path for a scheme in DerivedData. |
| `cc-applogs` | macOS unified log entries for a given process. |
| `cc-plist` | Pretty-print a plist file (XML or binary). |
| `cc-clean-dd [pattern]` | List / delete Xcode DerivedData directories (`--yes` to delete). |

### Self-management — `scripts-meta/` (3)

| Command | Purpose |
|---|---|
| `cc-install [--from DIR] [--dry-run]` | Idempotent re-symlink pass. By default scans every `claude-optimizing/scripts-*/` and `skill-scripts/`. |
| `cc-doctor` | Walk both `~/.local/bin/cc-*` and `~/.claude/hooks/cc-*-hook.py`; report broken, non-symlink, or stale entries. Exit non-zero on any problem. |
| `cc-help [<name>]` | List all `cc-*` scripts with one-line summaries; pass a script name to see its full `--help`. |

### Hook scripts — `scripts-hooks/` (1)

| File | Role |
|---|---|
| `cc-repo-hygiene-hook.py` | `Stop` hook enforcer. Blocks the turn from ending if: uncommitted/untracked changes exist, local/remote branches are already merged, the default branch is behind the remote, or worktrees are stale. Installed to `~/.claude/hooks/cc-repo-hygiene-hook.py` by `install.sh`; registered in `~/.claude/settings.json` under `hooks.Stop`. |

### Skill-coupled — `../skill-scripts/` (2)

| Command | Purpose |
|---|---|
| `cc-install-statusline` | Copy the custom-status-line Python package to `~/.claude-status-line/`, plus `session-tracker.py` to `~/.claude/hooks/`. Clears pycache, runs the skill's pytest suite. |
| `cc-verify` | Status-line-specific test + lint + typecheck runner. Currently ad-hoc (no automation calls it). |

## Adding a new script

1. Pick the right category dir. If none fits, create a new `claude-optimizing/scripts-<area>/` — the installer globs `scripts-*/`, so no loop updates are needed.
2. Create `scripts-<area>/cc-<name>.py` with `#!/usr/bin/env python3` and a short docstring.
3. `chmod +x`.
4. Run `cc-install` to (re-)symlink everything. Files ending in `-hook` automatically route to `~/.claude/hooks/`; everything else lands on `$PATH`.
5. Add a row to the relevant section above and to the catalog block in `claude-additions.md`.

## Related

- [`../install-readme.md`](../install-readme.md) — end-to-end reproduction guide for the full repo setup on a clean machine (this directory's `install.sh` automates sections 0/2/3/4 plus the pre-commit activation).
- [`../skill-scripts/README.md`](../skill-scripts/README.md) — why `skill-scripts/` lives at the repo root instead of under `claude-optimizing/`.
