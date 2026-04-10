# Cat Herding

Personal collection of Claude Code skills, plugins, hooks, and workflow extensions.

## Repository Structure

```
skills/                # 2 distributable skills (yolo, custom-status-line)
.claude/skills/        # Internal skills (lint-skill, lint-rule, lint-agent, optimize-rules, install-worktree-rule, etc.)
.claude/rules/         # Rules (cli-versioning, plugin-development, worktree-branch-cleanup)
```

## Skills

| Skill | Purpose |
|-------|---------|
| `/custom-status-line install` | Install composable status line pipeline |
| `/custom-status-line uninstall` | Remove status line pipeline |
| `/yolo` | Toggle per-session YOLO mode |

## Git Workflow

All work must be done in worktree branches and merged back into main via PR. Use EnterWorktree to create feature branches. Never commit directly to main.
