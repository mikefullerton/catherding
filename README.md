# Cat Herding

Opinionated tooling that turns Claude Code into a disciplined, cost-aware development partner. Two independent components, each installable on its own:

| Component | What it does | Source |
|---|---|---|
| **Claude optimizations** | `cc-*` shell commands, five Claude Code hooks, and a guidance block for `~/.claude/CLAUDE.md` | [`claude-optimizing/`](claude-optimizing/) |
| **YOLO** | Per-session auto-approval of all permission prompts, with configurable deny-list | [`skills/yolo/`](skills/yolo/) |

> The `custom-status-line` skill previously lived here. It moved to the [stenographer](https://github.com/agentic-cookbook/stenographer) repo — see `skills/custom-status-line/` there.

---

## Install

```bash
git clone <this-repo-url> ~/projects/active/catherding
cd ~/projects/active/catherding
./install.sh
```

You'll be prompted `[Y/n]` per component. Flags: `--yes` accepts all, `--no` declines all. Non-interactive stdin defaults to `--yes` unless `--no` is given.

`./uninstall.sh` mirrors it.

Full reproduction steps for a clean machine are in [`install-readme.md`](install-readme.md).

---

## 1. Claude optimizations — `claude-optimizing/`

A self-contained Claude-Code tool layer. One installer (`claude-optimizing/install.sh`) deploys all of:

### The `cc-*` scripts (30 commands)

Single-call replacements for multi-step Bash rituals Claude keeps repeating. Every script exits non-zero on failure, returns tight parseable output, and supports `--help`. Categorised into six directories, each of which the installer globs:

| Category | Count | Representative commands |
|---|---|---|
| Git / PR workflow | 8 | `cc-merge-worktree`, `cc-commit-push`, `cc-repo-state`, `cc-pr-status`, `cc-pr-review`, `cc-rebase-main`, `cc-branch-hygiene`, `cc-since` |
| Shell helpers | 2 | `cc-grep`, `cc-rename` |
| macOS / Xcode | 8 | `cc-xcbuild`, `cc-xcschemes`, `cc-xcsetting`, `cc-xcrun-app`, `cc-app-path`, `cc-applogs`, `cc-plist`, `cc-clean-dd` |
| Claude Code meta | 5 | `cc-usage-stats`, `cc-claude-fields`, `cc-memory`, `cc-graphify-status`, `cc-project-index` |
| Self-management | 3 | `cc-install`, `cc-doctor`, `cc-help` |
| Hooks | 5 | `cc-repo-hygiene-hook`, `cc-exit-worktree-hook`, `cc-block-pr-close-hook`, `cc-block-push-delete-hook`, `cc-general-principles-hook` (all route to `~/.claude/hooks/`, not `$PATH`) |

Full catalog with one-liners: [`claude-optimizing/README.md`](claude-optimizing/README.md).

Naming: source is `cc-<name>.py`, installer strips only `.py` → `cc-<name>` on PATH. The `-hook` suffix routes a file into `~/.claude/hooks/cc-*-hook.py` (Claude Code's hook protocol expects hooks there, not on `$PATH`).

### Policy block merged into `~/.claude/CLAUDE.md`

[`claude-additions.md`](claude-optimizing/claude-additions.md) is inserted between `<!-- BEGIN claude-optimizing -->` / `<!-- END claude-optimizing -->` markers on install, and removed on uninstall. It tells Claude to:

- Use Python, never bash (except install/uninstall/setup scripts).
- Prefer deterministic scripts over re-deriving logic in-turn.
- Treat worktree lifecycle (enter, exit, merge, cleanup) as user-initiated; use `cc-merge-worktree <pr>` when asked to merge.
- Follow the Repo Hygiene rules (commit your own work, only touch what you changed).

### Five hook scripts wired into `~/.claude/settings.json`

| Hook | Event | What it does |
|---|---|---|
| `cc-repo-hygiene-hook.py` | `Stop` | **Blocks** the turn from ending if this session produced staged, unstaged, or untracked changes that haven't been committed and pushed. Ignores prior-session dirt. |
| `cc-exit-worktree-hook.py` | `PostToolUse` (matcher: `ExitWorktree`) | **Non-blocking** reminder. After `ExitWorktree`, warns on stderr if a merged-but-still-on-disk worktree or an orphan remote branch exists (PR merged, remote branch not deleted) — suggests `cc-merge-worktree <pr>` to clean up. You decide what to do. |
| `cc-block-pr-close-hook.py` | `PreToolUse` (matcher: `Bash`) | **Blocks** `gh pr close` (usually a typo for `gh pr merge`). Override with `CC_ALLOW_PR_CLOSE=1` prefix. |
| `cc-block-push-delete-hook.py` | `PreToolUse` (matcher: `Bash`) | **Blocks** `git push --delete <branch>` / `git push origin :<branch>` when the branch heads an open PR (deleting it would auto-close the PR). Override with `CC_ALLOW_BRANCH_DELETE=1` prefix. |
| `cc-general-principles-hook.py` | `PreToolUse` (matcher: `Edit\|Write\|MultiEdit\|NotebookEdit`) | **Non-blocking** nudge that fires once per session on the first code-writing tool call, reminding Claude to invoke the `general-principles` skill. |

The two blocking hooks (hygiene + pr-close + push-delete) are narrow: they each answer a single yes/no question and stay out of the way otherwise. Worktree lifecycle and cleanup are user-driven — the hooks surface state but don't force moves.

### Pre-commit syntax check

`install.sh` runs `git config core.hooksPath .githooks`, activating a pre-commit hook that `python3 -m py_compile`s every staged `cc-*.py` before letting the commit through. Catches syntax errors before they propagate to `~/.local/bin/`.

---

## 2. YOLO — `skills/yolo/`

Auto-approves every permission prompt for a whole Claude Code session once enabled. Useful when you've already vetted what Claude will do and don't want to click "Approve" on every shell call. Per-session (not always-on) and tamper-aware.

### Lifecycle

1. `claude plugin install @catherding/yolo` (or `./install.sh` in this repo) deploys three shell hooks into `~/.claude/hooks/`:
   - `yolo-approve-all.sh` — `PermissionRequest` hook. When the session is yolo-enabled, approves the request unless the command matches the configurable deny list.
   - `yolo-session-start.sh` — writes a per-session state marker at `~/.claude-yolo-sessions/<session-id>.json`.
   - `yolo-session-cleanup.sh` — removes the marker on `SessionEnd`.
2. `install.sh` also seeds `~/.claude-yolo-sessions/yolo-deny.json` with sensible defaults (e.g. `rm -rf *`, `git push --force main`) and wires a statusline indicator so the 🔥 YOLO badge shows when the mode is active.
3. The `/yolo` skill (available inside Claude Code) toggles modes: `/yolo on`, `/yolo off`, `/yolo configure` (edit deny list).

### Deny list

A JSON file at `~/.claude-yolo-sessions/yolo-deny.json` containing regex-ish command patterns. Any permission request whose command matches a deny entry falls back to a normal prompt. Edit directly or via `/yolo configure`.

### Uninstall

`skills/yolo/uninstall.sh` removes hook scripts, strips the three `settings.json` entries (`PermissionRequest`, `SessionStart`, `SessionEnd`), deletes the statusline-indicator pipeline entry, and (with `--all`) nukes `~/.claude-yolo-sessions/`.

---

## Repo layout

```
catherding/
├── install.sh                         ← per-component [Y/n] prompts
├── uninstall.sh
├── README.md                          ← this file
├── install-readme.md                  ← clean-machine reproduction guide
├── claude-optimizing/                 ← component 1
│   ├── install.sh / uninstall.sh
│   ├── README.md                      ← full cc-* catalog
│   ├── claude-additions.md            ← merged into ~/.claude/CLAUDE.md
│   └── scripts-{git,bash,xcode,claude,meta,hooks}/   ← 30 cc-* scripts
├── skills/
│   └── yolo/                          ← component 2
│       ├── install.sh / uninstall.sh
│       ├── SKILL.md
│       └── references/                ← hook scripts + deny defaults + indicator
├── .claude/
│   ├── CLAUDE.md                      ← project-level instructions (this repo)
│   ├── skills/                        ← internal helper skills (lint-*, optimize-rules, …)
│   └── settings.json                  ← repo-level hook (graphify reminder on Glob/Grep)
└── .githooks/pre-commit               ← py_compile every staged cc-*.py
```

---

## Design philosophy

Everything here exists to **reduce the number of Bash calls Claude makes per turn**. Each repeated Bash invocation costs tokens (conversation cache + tool-result text); a deterministic script replacing five Bash turns saves real money. The three components cover the three repeating costs:

- **Claude optimizations** — the scripts themselves.
- **YOLO** — so Claude doesn't pause on every permission prompt, which otherwise forces the user back into the loop for trivial operations.
