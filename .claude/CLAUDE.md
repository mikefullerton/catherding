# Cat Herding

Personal collection of tools, scripts, Claude Code rules, skills, and extensions that augment my development workflow.

## Repository Structure

```
.claude/skills/        # 11 Claude Code skills
skills/                # 4 distributable skills (configurator, webinitor, new-project, quick-ref)
.claude/rules/         # 6 rules (active in this repo)
rules/                 # 6 distributable rules + 1 script
```

## Skills

| Skill | Purpose |
|-------|---------|
| `/custom-status-line install` | Install composable status line pipeline |
| `/custom-status-line uninstall` | Remove status line pipeline |
| `/repo-cleaner clean` | Recursive repo cleanup — auto-fixes obvious issues, interactively resolves the rest |
| `/install-worktree-rule` | Install the worktree/PR git workflow rule |
| `/optimize-rules` | Consolidate multiple rule files into a single optimized file |
| `/lint-rule` | Lint a rule file against best practices |
| `/lint-skill` | Lint a skill against best practices |
| `/lint-agent` | Lint an agent against best practices |
| `/show-project-setup` | Show project setup dashboard |
| `/install-recommended-tools` | Install recommended developer tools |
| `/webinitor` | Website infrastructure management — Cloudflare, Railway, GoDaddy, GitHub |
| `/configurator add [description]` | Add services, auth, features, storage to existing project |
| `/new-project <name> [in <org>]` | Create a new GitHub repo with project scaffolding |
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

All work must be done in worktree branches and merged back into main via PR. Use EnterWorktree to create feature branches. Never commit directly to main.
