# Cat Herding

Opinionated tooling that turns Claude Code into a disciplined, cost-aware development partner. Three independent components, each installable on its own:

| Component | What it does | Source |
|---|---|---|
| **Claude optimizations** | 30 `cc-*` shell commands, a Stop hook, a PostToolUse hook, and a guidance block for `~/.claude/CLAUDE.md` | [`claude-optimizing/`](claude-optimizing/) |
| **Custom status line** | Multi-row terminal status line (path, git, usage/quotas, session count, context %) with a composable pipeline | [`skills/custom-status-line/`](skills/custom-status-line/) |
| **YOLO** | Per-session auto-approval of all permission prompts, with configurable deny-list | [`skills/yolo/`](skills/yolo/) |

---

## Install

```bash
git clone <this-repo-url> ~/projects/active/cat-herding
cd ~/projects/active/cat-herding
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
| Git / PR workflow | 10 | `cc-merge-worktree`, `cc-commit-push`, `cc-repo-state`, `cc-pr-status`, `cc-pr-review`, `cc-rebase-main`, `cc-branch-hygiene`, `cc-bump-submodule`, `cc-submodule-status`, `cc-since` |
| Shell helpers | 2 | `cc-grep`, `cc-rename` |
| macOS / Xcode | 9 | `cc-xcgen`, `cc-xcbuild`, `cc-xcschemes`, `cc-xcsetting`, `cc-xcrun-app`, `cc-app-path`, `cc-applogs`, `cc-plist`, `cc-clean-dd` |
| Claude Code meta | 5 | `cc-usage-stats`, `cc-claude-fields`, `cc-memory`, `cc-graphify-status`, `cc-project-index` |
| Self-management | 3 | `cc-install`, `cc-doctor`, `cc-help` |
| Hooks | 1 | `cc-repo-hygiene-hook` (routes to `~/.claude/hooks/`, not `$PATH`) |

Full catalog with one-liners: [`claude-optimizing/README.md`](claude-optimizing/README.md).

Naming: source is `cc-<name>.py`, installer strips only `.py` → `cc-<name>` on PATH. The `-hook` suffix routes a file into `~/.claude/hooks/cc-*-hook.py` (Claude Code's hook protocol expects hooks there, not on `$PATH`).

### Policy block merged into `~/.claude/CLAUDE.md`

[`claude-additions.md`](claude-optimizing/claude-additions.md) is inserted between `<!-- BEGIN claude-optimizing -->` / `<!-- END claude-optimizing -->` markers on install, and removed on uninstall. It tells Claude to:

- Use Python, never bash (except install/uninstall/setup scripts).
- Prefer deterministic scripts over re-deriving logic in-turn.
- Go through worktree branches for every change, and run `cc-merge-worktree <pr>` after every merge.
- Follow the Repo Hygiene rules (only-touch-what-you-changed, commit-early, push-immediately, delete-merged branches).

### Two hook scripts wired into `~/.claude/settings.json`

| Hook | Event | What it does |
|---|---|---|
| `cc-repo-hygiene-hook.py` | `Stop` | Blocks the turn from ending if: staged/unstaged/untracked changes exist, local or remote branches are already merged into default, default branch is behind origin, or stale worktrees exist. |
| `cc-exit-worktree-hook.py` | `PostToolUse` (matcher: `ExitWorktree`) | Fires right after `ExitWorktree`. If any non-default-branch worktree is still on disk **and** its branch is already merged into `origin/<default>`, exits non-zero with a diagnostic that points at `cc-merge-worktree <pr>` — blocking the next tool call until the cleanup runs. |

Without these hooks, the rules above are advisory only. With them, the rules are mechanically enforced at the two moments that matter (turn-end and post-ExitWorktree).

### Pre-commit syntax check

`install.sh` runs `git config core.hooksPath .githooks`, activating a pre-commit hook that `python3 -m py_compile`s every staged `cc-*.py` before letting the commit through. Catches syntax errors before they propagate to `~/.local/bin/`.

---

## 2. Custom status line — `skills/custom-status-line/`

Replaces the default one-line Claude Code status line with a multi-row terminal panel. Typical contents:

```
~/projects/active/cat-herding on main | ⚠2 remote-only
                  git | files:~0 +0 -0     | remote: in sync       | 0% / 200k ctx           | YOLO 🔥
              Opus 4.6 | 5h:35m             |                       |
         all sessions  | 2 active           | 0 thinking            | 2 waiting
         weekly: 13.3% | 5h: 8.1%           | daily ave: 2.1%       | 5d 11h 02m left | 14.7% projected
          today: 13.1% | 5h: 8.1%           | 19h 55m left          |
      usage last week  | 4489.1M / $9184.04 | this wk: 3894.0M / $7271.72 | -13%
```

Each row is produced by a **pipeline module** — an independent Python script or shell hook the dispatcher calls in order. Modules include base info (path + git + model + YOLO indicator), rate-limit / quota rows (with colour thresholds: red ≥95 %, yellow ≥80 %), active-sessions count, graphify savings summary, progress indicators, and week-over-week usage comparisons.

### Install

- `./install.sh` (top-level) prompts for it.
- Or run `skills/custom-status-line/install.sh` directly. It copies the Python package to `~/.claude-status-line/statusline/`, helper scripts to `~/.claude-status-line/scripts/`, and `session-tracker.py` to `~/.claude/hooks/`. Then runs the skill's pytest suite (`--skip-tests` to skip).
- Uninstall via `skills/custom-status-line/uninstall.sh`.

### Extending the pipeline

The skill documents a plugin convention — drop an executable script into `~/.claude-status-line/scripts/` and add an entry to `pipeline.json`. See [`skills/custom-status-line/how-to-add-status-line-scripts.md`](skills/custom-status-line/how-to-add-status-line-scripts.md).

### Skill-internal developer tools (not on `$PATH`)

- `scripts/verify.py` — runs the skill's pytest + lint + typecheck.
- `scripts/claude-fields.py` — inspects Claude version field blobs in `~/claude-usage.db`.
- `scripts/graphify-status.py` — reads `~/.claude-status-line/graphify-savings-cache.json`.

Invoke with `python3 skills/custom-status-line/scripts/<name>.py`.

---

## 3. YOLO — `skills/yolo/`

Auto-approves every permission prompt for a whole Claude Code session once enabled. Useful when you've already vetted what Claude will do and don't want to click "Approve" on every shell call. Per-session (not always-on) and tamper-aware.

### Lifecycle

1. `claude plugin install @cat-herding/yolo` (or `./install.sh` in this repo) deploys three shell hooks into `~/.claude/hooks/`:
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
cat-herding/
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
│   ├── custom-status-line/            ← component 2
│   │   ├── install.sh / uninstall.sh
│   │   ├── SKILL.md
│   │   ├── references/                ← runtime source files + 3 hook scripts
│   │   ├── scripts/                   ← skill-internal dev tools (not on PATH)
│   │   └── tests/
│   └── yolo/                          ← component 3
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
- **Custom status line** — so Claude can see its own cost + quota state without asking.
- **YOLO** — so Claude doesn't pause on every permission prompt, which otherwise forces the user back into the loop for trivial operations.
