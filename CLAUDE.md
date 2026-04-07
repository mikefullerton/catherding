# Cat Herding

Personal collection of tools, scripts, Claude Code rules, skills, and extensions that augment my development workflow.

## Repository Structure

```
.claude/skills/        # 11 Claude Code skills
.claude/rules/         # 6 rules (active in this repo)
rules/                 # 6 distributable rules + 1 script
```

## Skills

| Skill | Purpose |
|-------|---------|
| `/custom-status-line install` | Install composable status line pipeline |
| `/custom-status-line uninstall` | Remove status line pipeline |
| `/repo-tools clean` | Recursive repo cleanup — auto-fixes obvious issues, interactively resolves the rest |
| `/install-worktree-rule` | Install the worktree/PR git workflow rule |
| `/optimize-rules` | Consolidate multiple rule files into a single optimized file |
| `/lint-rule` | Lint a rule file against best practices |
| `/lint-skill` | Lint a skill against best practices |
| `/lint-agent` | Lint an agent against best practices |
| `/show-project-setup` | Show project setup dashboard |
| `/install-recommended-tools` | Install recommended developer tools |
| `/site-manager add [description]` | Add services, auth, features, storage to existing project |
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

**Owner edits** go direct to main. **Claude Code sessions** go through a branch + PR via worktree. Worktree directory: `.claude/worktrees/`.
