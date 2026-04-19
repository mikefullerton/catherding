# Cat Herding

Personal collection of Claude Code skills, hooks, and workflow scripts.

## Repository Structure

```
skills/           # Distributable skills (yolo)
.claude/skills/   # Internal skills (lint-skill, lint-rule, lint-agent, optimize-rules, install-worktree-rule, port-swiftui-to-appkit)
claude-optimizing/         # Self-contained Claude-Code tooling layer (guidance + scripts + hooks)
  scripts-git/             # Git / PR workflow (cc-merge-worktree, cc-commit-push, …)
  scripts-bash/            # Shell helpers (cc-grep, cc-rename)
  scripts-xcode/           # macOS / Xcode (cc-xcbuild, cc-xcgen, cc-applogs, …)
  scripts-claude/          # Claude Code meta (cc-usage-stats, cc-claude-fields, cc-memory, cc-graphify-status, cc-project-index)
  scripts-meta/            # Self-management (cc-install, cc-doctor, cc-help)
  scripts-hooks/           # Claude Code hook scripts (cc-repo-hygiene-hook.py for Stop + cc-exit-worktree-hook.py for PostToolUse:ExitWorktree → ~/.claude/hooks/)
  tests/                   # pytest harness for the cc-* scripts (uses agentic-cookbook/catherdingtests as a real-GitHub sandbox)
  claude-additions.md      # Guidance block appended to ~/.claude/CLAUDE.md by install.sh
  install.sh / uninstall.sh  # Deploy/remove guidance + scripts + hooks
```

## Tests

The `cc-*` scripts have a real-GitHub test harness at `claude-optimizing/tests/`. It uses [`agentic-cookbook/catherdingtests`](https://github.com/agentic-cookbook/catherdingtests) as a sandbox repo (creates real branches, PRs, and merges). Run `pytest tests/ -v` from `claude-optimizing/`. See `claude-optimizing/tests/README.md` for coverage and the sandbox-repo setup that matches production conditions like `delete_branch_on_merge: true`.

## Skills

| Skill | Purpose |
|-------|---------|
| `/yolo` | Toggle per-session YOLO mode |

> `custom-status-line` moved to the [stenographer](https://github.com/agentic-cookbook/stenographer) repo.

## Git Workflow

All work must be done in worktree branches and merged back into main via PR. Use `EnterWorktree` to create feature branches. Never commit directly to main. `cc-merge-worktree <pr>` handles the full merge + cleanup ritual (including remote-branch deletion, which `gh pr merge --delete-branch` silently skips from inside a worktree).

## graphify

This project has a graphify knowledge graph at `graphify-out/`.

Rules:
- Before answering architecture or codebase questions, read `graphify-out/GRAPH_REPORT.md` for god nodes and community structure
- If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
