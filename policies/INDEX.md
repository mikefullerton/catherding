---
title: "Policies — Index"
summary: "Index of all policies, grouped by area. Each policy is a specific application of a general cookbook principle."
triggers: [find-policy, policy-audit, starting-work]
tags: [index, policies, navigation]
---

# Policies — Index

Each policy is a specific application of [cookbook principles](../../agenticcookbook/principles/INDEX.md) to this author's workflow. The cookbook is the generalized reference; these policies are the concrete rules.

**How to use this index:** Match the situation you're in against the **Triggers** column, then load the linked policy. Every policy is self-contained.

## General Software Development

| Policy | Summary | Triggers |
|--------|---------|----------|
| [required-tools](general-software-development/required-tools.md) | Python 3.12+, SQLite; Xcode + XcodeGen (Apple); Visual Studio (Windows) | `machine-setup`, `dependency-audit`, `new-dev-machine`, `tooling-setup` |
| [setup-scripts](general-software-development/setup-scripts.md) | Setup steps live in /setup/; every install has a matching uninstall | `writing-install-script`, `adding-setup-step`, `repo-bootstrap`, `adding-install-uninstall` |

## Apple Software Development

| Policy | Summary | Triggers |
|--------|---------|----------|
| [swift](apple-software-development/swift.md) | Swift 6.2.x with strict concurrency | `starting-swift-project`, `swift-package-setup`, `swift-version-audit`, `xcode-project-conversion` |
| [xcode-projects](apple-software-development/xcode-projects.md) | XcodeGen + project.yml + checked-in .xcodeproj; single .xcworkspace in /apple | `creating-xcode-project`, `xcode-project-conversion`, `adding-xcode-target`, `xcodeworkspace-setup`, `converting-swift-package` |
| [code-signing](apple-software-development/code-signing.md) | Team mikefullerton; entitlements preserved; no certs in repo | `configuring-signing`, `entitlements-change`, `xcode-team-setup`, `creating-xcode-project` |

## Shell Scripting

| Policy | Summary | Triggers |
|--------|---------|----------|
| [scripting-language](shell-scripting/scripting-language.md) | Python 3.12+ for scripts; only install/uninstall/setup may be .sh | `writing-script`, `tooling-setup`, `automation-task`, `writing-hook` |

## Repo Organization

| Policy | Summary | Triggers |
|--------|---------|----------|
| [repo-baseline](repo-organization/repo-baseline.md) | Every repo must have README, LICENSE, .gitignore, and .claude/CLAUDE.md | `new-repo`, `repo-audit`, `starting-new-project` |
| [documentation](repo-organization/documentation.md) | Markdown goes in /docs; planning and research in /docs/planning and /docs/research | `writing-docs`, `planning-feature`, `adding-research-notes`, `organizing-docs` |
| [file-organization](repo-organization/file-organization.md) | Lowercase dirs, kebab-case files, encapsulated directories | `creating-file`, `creating-directory`, `renaming-file`, `file-audit`, `repo-restructure` |
| [git-naming](repo-organization/git-naming.md) | Repo names are lowercase with no hyphens | `creating-repo`, `renaming-repo` |
| [multi-platform-layout](repo-organization/multi-platform-layout.md) | Top-level /apple, /windows, /android — only those relevant | `starting-multi-platform-project`, `adding-platform`, `repo-restructure` |
| [llm-file-layout](repo-organization/llm-file-layout.md) | /claude/<type>/ for global, .claude/ for repo-local; /policies/ for general policies | `adding-claude-extension`, `adding-skill`, `writing-claude-rule`, `setting-up-graphify`, `adding-mcp-server` |

## Repo Hygiene

No policy files yet — commit/branch/worktree rules currently live in `~/.claude/CLAUDE.md` ("Worktree Workflow" and "Repo Hygiene" sections). See [repo-hygiene/README.md](repo-hygiene/README.md).
