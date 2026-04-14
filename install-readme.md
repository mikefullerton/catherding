# Reproducing the Git + Bash Setup on a Clean Machine

This doc walks through reproducing **everything in this repo that influences how Claude Code issues git and bash commands** on a fresh machine. It does **not** cover graphify, status-line, or YOLO setup — each of those has its own install path (`/custom-status-line install`, `/yolo`, etc.).

Two layers are involved:

1. **This repo** (auto-installed via `./install.sh`): 31 `cc-*` workflow scripts, the pre-commit syntax check, and the `/home/.local/bin` wiring.
2. **Global state** that lives outside this repo (user has to stage manually): `~/.claude/CLAUDE.md` policy, `~/.claude/hooks/*` enforcement, the global `~/.claude/settings.json` hook registration, and a handful of Claude Code plugins.

Follow the sections in order.

---

## 0. Prerequisites

Install these first. All commands assume macOS + zsh/bash.

```bash
# Core tools
brew install git gh python3 ripgrep jq
# Claude Code itself (CLI)
brew install anthropic-ai/claude-code/claude-code   # or whichever install method you use
# uv (for skills that ship as editable-install CLIs)
brew install uv
```

Ensure `$HOME/.local/bin` is on your `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Authenticate `gh` so `cc-merge-worktree`, `cc-pr-status`, etc. work:

```bash
gh auth login
```

---

## 1. Clone and run this repo's installer

```bash
mkdir -p ~/projects/active
git clone <this-repo-url> ~/projects/active/cat-herding
cd ~/projects/active/cat-herding
./install.sh
```

What `install.sh` does:

- Symlinks `skills/*` into `~/.claude/skills/` (distributable skills — `custom-status-line`, `yolo` — excluded from the scope of this doc, but installed alongside).
- Runs `uv tool install -e` for every `skills/*/*/pyproject.toml` (CLI skills).
- Copies every `cc-*.py` from `scripts/` and `skill-scripts/` into `~/.local/bin/cc-*` (extension stripped).
- Activates the repo's pre-commit hook: `git config core.hooksPath .githooks`.

Verify:

```bash
cc-doctor          # → "did: ok 31 | broken 0 | non-symlink 0 | stale 0"
cc-help            # → one-line summary of every cc-* script
```

If `cc-doctor` reports broken entries, re-run `cc-install` — it uses symlinks and is safe to re-invoke.

---

## 2. Global `~/.claude/CLAUDE.md`

This file is the policy layer that tells Claude to prefer `cc-*` scripts, require worktrees, commit early, etc. It is **not checked into this repo** (it's user-global). Back up your current copy before editing.

### 2.1 Sections that drive git/bash behavior

At minimum, make sure the following sections exist in `~/.claude/CLAUDE.md`. Copy them verbatim from your existing setup, or recreate from this template:

```markdown
## Scripting Language — MANDATORY

Always use Python for scripts. Never write bash/shell scripts (.sh). Exceptions:
`install.sh`, `uninstall.sh`, `setup.sh` may be shell.

## Token Efficiency — MANDATORY

- Prefer inline execution over parallel subagents.
- Push work into deterministic Python scripts whenever possible. If Claude will
  repeatedly perform the same logic, encode it in a Python script that produces
  structured output — don't spend tokens re-deriving the answer each time.

## Workflow Scripts — PREFER over multi-step Bash

The `cc-*` scripts (installed to `~/.local/bin/` from
`~/projects/active/cat-herding/scripts/` and `.../skill-scripts/`) collapse
common multi-step Bash rituals into single calls. Use them instead of raw
git/gh sequences whenever the scenario matches:

- `cc-merge-worktree <pr>` — merge PR + full worktree cleanup (9-step ritual)
- `cc-commit-push "msg" [--pr "title"]` — stage + commit + push + optional draft PR
- `cc-repo-state` — session-start audit: branch, status, worktrees, staleness
- `cc-pr-status <num>` — PR summary: state, checks, diff, comments
- `cc-branch-hygiene [--cleanup]` — stale/merged/remote-only/prunable report
- `cc-rebase-main` — rebase onto origin/<default> and force-push with lease
- `cc-bump-submodule <path>...` — bump submodules to tip of origin/<default>
- `cc-since <ref>` — list PRs and commits since a ref
- `cc-doctor` — verify cc-* symlinks
- `cc-help` — catalog with summaries

All scripts support `--help`, exit non-zero on failure, and return tight
parseable output. Source: `~/projects/active/cat-herding/scripts/` (general
workflow) and `~/projects/active/cat-herding/skill-scripts/` (skill-coupled).

## Worktree Workflow — MANDATORY

> Scope: these rules apply only to projects under `~/projects/`. External
> repos (e.g. `~/projects/external/`) are exempt — skip worktree and commit
> rules there.

All changes go through worktree branches. Never commit directly to the default
branch.

1. Start: `EnterWorktree` to create a feature branch and switch into it.
2. Work: commit and push as you go. Create a draft PR on first push.

## Repo Hygiene — MANDATORY, NO EXCEPTIONS

> Scope: `~/projects/` only.

### Only Touch What You Changed
Do NOT commit, push, or otherwise modify code you didn't change in the current
session. If pre-existing uncommitted state exists when you start, ask the user
how to proceed. Never auto-commit, auto-stash, or auto-discard changes you
didn't make.

### Before Starting Work
Run `git status`. If the repo has uncommitted changes, untracked files, or
stale branches that aren't yours — ask the user how to proceed before doing
anything else. If the default branch is behind the remote, pull before
starting.

### During Work
- `EnterWorktree` is the ONLY way to create feature branches. NEVER use
  `git checkout -b`, `git switch -c`, or manually `cd` into a worktree dir.
- Commit early and often — for changes you just made. No local-only commits
  may exist when your turn ends.
- Push every commit immediately after making it.

### Before Ending a Turn
- ALL changes you made MUST be committed and pushed.
- Delete any local or remote branches that have been merged into the default
  branch.
- Verify `main`/`master` matches the remote. If behind, pull.

### What the Hook Enforces
The Stop hook at `~/.claude/hooks/repo-hygiene.py` blocks your turn from
ending if any of these are true:
1. Staged or unstaged changes exist
2. Untracked files exist (not in .gitignore)
3. Local branches exist that are already merged into default
4. Remote branches exist that are already merged into default
5. The default branch is behind the remote
6. Stale worktrees exist (branch deleted or merged)
```

### 2.2 Save + reload

Claude re-reads `CLAUDE.md` at session start, so restart any running `claude` sessions after editing.

---

## 3. Global hooks — `~/.claude/hooks/`

Two hooks in this directory shape git/bash behavior. They live outside this repo; you need to place them manually.

### 3.1 `repo-hygiene.py` (Stop hook — the enforcer)

Reads JSON from stdin (Claude Code hook protocol), runs several `git` queries against the session's `cwd`, and exits non-zero with a diagnostic message if the repo is dirty. Blocks the turn from ending.

Check the sibling `~/.claude/hooks/repo-hygiene.py` on your source machine (236 lines) and copy it to the new machine. If you don't have the source, the behavior is:

- Parse stdin JSON, early-exit if `stop_hook_active` is set (re-entry guard).
- Compute `cwd`; early-exit unless cwd is under `$HOME/projects/`.
- Run `git status --porcelain`, `git branch --merged <default>`, `git rev-list`, `git worktree list` to check each of the 6 conditions listed in section 2.1.
- If any fail, print a human-readable diagnostic to stderr and exit 2 (which the Claude harness interprets as "block the turn").

```bash
mkdir -p ~/.claude/hooks
# Copy from your source machine, or re-author from the rules above
cp /path/to/source/.claude/hooks/repo-hygiene.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/repo-hygiene.py
```

### 3.2 `session-tracker.py`

Writes session metadata used by the status line. Not git/bash-specific, but wired alongside the hygiene hook — copy it too if you have it:

```bash
cp /path/to/source/.claude/hooks/session-tracker.py ~/.claude/hooks/
chmod +x ~/.claude/hooks/session-tracker.py
```

---

## 4. Global hook registration — `~/.claude/settings.json`

The hooks above don't fire unless Claude Code is told to call them. Register the Stop hook (and the session tracker on relevant events) in your global settings.

Open `~/.claude/settings.json` and ensure the `hooks` object contains these event groups — preserve any other groups (observability tools, plugins) already present:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          { "type": "command",
            "command": "/usr/bin/python3 $HOME/.claude/hooks/repo-hygiene.py" }
        ]
      },
      {
        "hooks": [
          { "type": "command",
            "command": "python3 $HOME/.claude/hooks/session-tracker.py Stop" }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          { "type": "command",
            "command": "python3 $HOME/.claude/hooks/session-tracker.py SessionStart" }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          { "type": "command",
            "command": "python3 $HOME/.claude/hooks/session-tracker.py SessionEnd" }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command",
            "command": "python3 $HOME/.claude/hooks/session-tracker.py UserPromptSubmit" }
        ]
      }
    ]
  }
}
```

Restart any running Claude sessions. A new turn's Stop event will now hit the hygiene hook.

---

## 5. Per-repo allow-list — `.claude/settings.local.json`

This file tells Claude Code which bash patterns to auto-approve **without prompting** in this specific repo. It's not checked in to the repo. Create it after cloning:

```bash
cat > ~/projects/active/cat-herding/.claude/settings.local.json <<'EOF'
{
  "permissions": {
    "allow": [
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git push:*)",
      "Bash(git:*)",
      "Bash(cp:*)"
    ]
  }
}
EOF
```

Repeat for every repo under `~/projects/` where you want the same convenience. Anything outside this list will prompt on every invocation.

---

## 6. Claude Code plugins that add git/bash surface

These are optional but recommended — they plug in slash-commands, PR-review agents, and process skills that guide git flows. Install via Claude Code's plugin manager:

```bash
# In a Claude Code session (or via `claude plugin install` if supported headless):
/plugin install commit-commands@claude-plugins-official      # /commit, /commit-push-pr, /clean_gone
/plugin install github@claude-plugins-official               # gh PR/issue helpers
/plugin install pr-review-toolkit@claude-plugins-official    # review-pr + specialist review agents
/plugin install superpowers@claude-plugins-official          # using-git-worktrees, finishing-a-development-branch, executing-plans, writing-plans, etc.
```

Disable plugins you don't want:

```bash
/plugin disable security-guidance@claude-plugins-official
/plugin disable vercel@claude-plugins-official
```

---

## 7. Verify end-to-end

```bash
# Scripts
cc-doctor                         # all symlinks ok
cc-help | head                    # catalog renders

# Repo-local git behaviour
cd ~/projects/active/cat-herding
git status                        # clean
git config core.hooksPath         # → .githooks
echo 'x' > /tmp/bad.py && \
  mv /tmp/bad.py scripts/cc-test-syntax.py && \
  git add scripts/cc-test-syntax.py && \
  git commit -m 'test'            # should be REJECTED by pre-commit
git restore --staged scripts/cc-test-syntax.py && rm scripts/cc-test-syntax.py

# Hook firing
# Start a Claude session, make a dirty change, attempt to end the turn.
# Stop hook should block with a hygiene report.
```

If any step fails, re-read the corresponding section above — each one is isolated.

---

## Uninstall

```bash
cd ~/projects/active/cat-herding
./uninstall.sh                    # removes cc-* symlinks, unsymlinks skills, uninstalls CLIs
rm ~/.claude/hooks/repo-hygiene.py ~/.claude/hooks/session-tracker.py
# Remove the `hooks` entries you added in section 4 from ~/.claude/settings.json
# Remove repo/.claude/settings.local.json if you don't want auto-approvals
git -C ~/projects/active/cat-herding config --unset core.hooksPath
```

Plugins can be removed via `/plugin uninstall <name>@<marketplace>`.
