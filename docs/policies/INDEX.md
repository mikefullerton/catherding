---
title: "Development Policies — Index"
summary: "Index of all development policies. Each policy is a specific application of a general cookbook principle to this author's workflow."
triggers: [find-policy, policy-audit, starting-work]
tags: [index, policies, navigation]
---

# Development Policies — Index

Each policy is a specific application of [cookbook principles](../../../agenticcookbook/principles/INDEX.md) to this author's workflow. The cookbook is the generalized reference; these policies are the concrete rules.

**How to use this index:** Match the situation you're in against the **Triggers** column, then load the linked policy. Every policy is self-contained.

## Every Repo

| Policy | Summary | Triggers |
|--------|---------|----------|
| [repo-baseline](repo-baseline.md) | Every repo must have README, LICENSE, .gitignore, and .claude/CLAUDE.md | `new-repo`, `repo-audit`, `starting-new-project` |
| [documentation](documentation.md) | Markdown goes in /docs; planning and research in /docs/planning and /docs/research | `writing-docs`, `planning-feature`, `adding-research-notes`, `organizing-docs` |
| [file-organization](file-organization.md) | Lowercase dirs, kebab-case files, encapsulated directories | `creating-file`, `creating-directory`, `renaming-file`, `file-audit`, `repo-restructure` |
| [git-naming](git-naming.md) | Repo names are lowercase with no hyphens | `creating-repo`, `renaming-repo` |

## Tooling

| Policy | Summary | Triggers |
|--------|---------|----------|
| [scripting-language](scripting-language.md) | Python 3.12+ for scripts; only install/uninstall/setup may be .sh | `writing-script`, `tooling-setup`, `automation-task`, `writing-hook` |
| [setup-scripts](setup-scripts.md) | Setup steps live in /setup/; every install has a matching uninstall | `writing-install-script`, `adding-setup-step`, `repo-bootstrap`, `adding-install-uninstall` |
| [required-tools](required-tools.md) | Python 3.12+, SQLite; Xcode + XcodeGen (Apple); Visual Studio (Windows) | `machine-setup`, `dependency-audit`, `new-dev-machine`, `tooling-setup` |

## LLMs

| Policy | Summary | Triggers |
|--------|---------|----------|
| [llm-file-layout](llm-file-layout.md) | /claude/<type>/ for global, .claude/ for repo-local; /docs/policies/ for general policies | `adding-claude-extension`, `adding-skill`, `writing-claude-rule`, `setting-up-graphify`, `adding-mcp-server` |

## Multi-Platform

| Policy | Summary | Triggers |
|--------|---------|----------|
| [multi-platform-layout](multi-platform-layout.md) | Top-level /apple, /windows, /android — only those relevant | `starting-multi-platform-project`, `adding-platform`, `repo-restructure` |

## Apple [macOS only]

| Policy | Summary | Triggers |
|--------|---------|----------|
| [apple-swift](apple-swift.md) | Swift 6.2.x with strict concurrency | `starting-swift-project`, `swift-package-setup`, `swift-version-audit`, `xcode-project-conversion` |
| [apple-xcode-projects](apple-xcode-projects.md) | XcodeGen + project.yml + checked-in .xcodeproj; single .xcworkspace in /apple | `creating-xcode-project`, `xcode-project-conversion`, `adding-xcode-target`, `xcodeworkspace-setup`, `converting-swift-package` |
| [apple-code-signing](apple-code-signing.md) | Team mikefullerton; entitlements preserved; no certs in repo | `configuring-signing`, `entitlements-change`, `xcode-team-setup`, `creating-xcode-project` |
