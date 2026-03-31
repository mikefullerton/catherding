# Cat Herding

Personal collection of tools, scripts, Claude Code rules, skills, and extensions that augment my development workflow.

## Repository Structure

```
.claude/skills/        # 12 Claude Code skills
.claude/rules/         # 6 rules (active in this repo)
rules/                 # 6 distributable rules + 1 script
```

## Skills

| Skill | Purpose |
|-------|---------|
| `/yolo` | Toggle per-session YOLO mode (auto-approve permissions) |
| `/install-status-enhancements` | Install enhanced Claude Code status line |
| `/uninstall-status-enhancements` | Remove enhanced status line |
| `/cleanup-repo` | Find and fix stale branches, worktree issues, repo hygiene |
| `/install-worktree-rule` | Install the worktree/PR git workflow rule |
| `/optimize-rules` | Consolidate multiple rule files into a single optimized file |
| `/lint-rule` | Lint a rule file against best practices |
| `/lint-skill` | Lint a skill against best practices |
| `/lint-agent` | Lint an agent against best practices |
| `/show-project-setup` | Show project setup dashboard |
| `/install-recommended-tools` | Install recommended developer tools |
| `/port-swiftui-to-appkit` | Plan conversion of a SwiftUI app to AppKit |

## Distributable Rules

| Rule | Purpose |
|------|---------|
| `always-use-worktrees-and-prs.md` | Enforce worktree + PR git workflow |
| `authoring-ground-rules.md` | Foundation rule for all authoring |
| `skill-authoring.md` | Best practices for writing skills |
| `skill-versioning.md` | Semver versioning protocol for skills/rules |
| `extension-authoring.md` | Best practices for writing extensions |
| `permissions.md` | Permission management guidelines |

## Git Workflow

**Owner edits** go direct to main. **Claude Code sessions** go through a branch + PR via worktree.
