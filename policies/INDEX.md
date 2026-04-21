---
title: "Policies — Index"
summary: "Index of all policies, grouped into Setup (one-time machine/repo) and Workflow (ongoing development). Each policy is a specific application of a general cookbook principle."
triggers: [find-policy, policy-audit, starting-work]
tags: [index, policies, navigation]
---

# Policies — Index

Each policy is a specific application of [cookbook principles](../../agenticcookbook/principles/INDEX.md) to this author's workflow. The cookbook is the generalized reference; these policies are the concrete rules.

**How to use this index:** Match the situation you're in against the **Triggers** column, then load the linked policy. Every policy is self-contained.

Policies are grouped into two tiers:

- **Setup** — one-time concerns for bootstrapping a machine or a repo.
- **Workflow** — ongoing concerns that govern how day-to-day development work is done.

## Setup

### Required Tools

| Policy | Summary | Triggers |
|--------|---------|----------|
| [all](setup/required-tools/all.md) | Python 3.12+ and SQLite on every machine | `machine-setup`, `dependency-audit`, `new-dev-machine`, `tooling-setup` |
| [apple](setup/required-tools/apple.md) | Xcode + XcodeGen (plus recommended VS Code, Claude Code) | `machine-setup`, `new-dev-machine`, `apple-setup` |
| [windows](setup/required-tools/windows.md) | Visual Studio | `machine-setup`, `new-dev-machine`, `windows-setup` |
| [scripting](setup/required-tools/scripting.md) | Python 3.12+ for scripts; only install/uninstall/setup may be `.sh` | `writing-script`, `tooling-setup`, `automation-task`, `writing-hook` |

### Repo Organization

| Policy | Summary | Triggers |
|--------|---------|----------|
| [repo-baseline](setup/repo-organization/repo-baseline.md) | Every repo must have README, LICENSE, .gitignore, and .claude/CLAUDE.md | `new-repo`, `repo-audit`, `starting-new-project` |
| [documentation](setup/repo-organization/documentation.md) | Markdown goes in /docs; planning and research in /docs/planning and /docs/research | `writing-docs`, `planning-feature`, `adding-research-notes`, `organizing-docs` |
| [file-organization](setup/repo-organization/file-organization.md) | Lowercase dirs, kebab-case files, encapsulated directories | `creating-file`, `creating-directory`, `renaming-file`, `file-audit`, `repo-restructure` |
| [git-naming](setup/repo-organization/git-naming.md) | Repo names are lowercase with no hyphens | `creating-repo`, `renaming-repo` |
| [multi-platform-layout](setup/repo-organization/multi-platform-layout.md) | Top-level /apple, /windows, /android — only those relevant | `starting-multi-platform-project`, `adding-platform`, `repo-restructure` |
| [llm-file-layout](setup/repo-organization/llm-file-layout.md) | /claude/<type>/ for global, .claude/ for repo-local; /policies/ for general policies | `adding-claude-extension`, `adding-skill`, `writing-claude-rule`, `setting-up-graphify`, `adding-mcp-server` |
| [setup-scripts](setup/repo-organization/setup-scripts.md) | Setup steps live in /setup/; every install has a matching uninstall | `writing-install-script`, `adding-setup-step`, `repo-bootstrap`, `adding-install-uninstall` |

## Workflow

### General Principles

| Policy | Summary | Triggers |
|--------|---------|----------|
| [principles-general](workflow/principles-general/principles-general.md) | Map of all 21 cookbook principles, grouped by theme, with links to local policies that apply each one | `starting-work`, `writing-code`, `code-review`, `design-decision` |

### Apple Platform Development

| Policy | Summary | Triggers |
|--------|---------|----------|
| [swift-version](workflow/apple-platform-development/swift-version.md) | Swift 6.2.x with strict concurrency | `starting-swift-project`, `swift-package-setup`, `swift-version-audit`, `xcode-project-conversion` |
| [xcode-projects](workflow/apple-platform-development/xcode-projects.md) | Swift packages for reusable code; Xcode projects (XcodeGen + checked-in .xcodeproj) for shipping products; single .xcworkspace in /apple aggregates both | `creating-xcode-project`, `adding-xcode-target`, `xcodeworkspace-setup`, `creating-swift-package`, `adding-reusable-code` |
| [code-signing](workflow/apple-platform-development/code-signing.md) | Team mikefullerton; entitlements preserved; no certs in repo | `configuring-signing`, `entitlements-change`, `xcode-team-setup`, `creating-xcode-project` |

### Repo Hygiene

| Policy | Summary | Triggers |
|--------|---------|----------|
| [repo-hygiene](workflow/repo-hygiene/repo-hygiene.md) | Feature branches in worktrees; commits push immediately; branches and worktrees cleaned up on merge | `committing-code`, `creating-branch`, `using-worktree`, `opening-pr`, `repo-hygiene-audit` |
