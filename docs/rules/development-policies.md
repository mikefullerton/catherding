---
name: development-policies
description: Global development environment policies — language versions, tooling, project layout. Rules with no platform label apply to all platforms.
type: rules
---

# Development Policies — MANDATORY

> Rules with no platform label apply to all platforms.

## Every Repo Must Have

- **`README.md`** in the root — keep it up to date as the repo evolves.
- **`LICENSE`** in the root — if missing, prompt the user to choose one before proceeding. Default to All Rights Reserved:
  ```
  Copyright (c) <year> <author>. All rights reserved.
  ```
  Alternative: MIT License. Do not add a license without asking.
- **`.gitignore`** — on macOS, always ignore `.DS_Store` files.
- **`.claude/CLAUDE.md`** — project-specific Claude instructions go here, not as a `CLAUDE.md` in the repo root. At minimum it should cover: what the repo is, its directory structure, and how to run or build it. A minimal placeholder is fine — the goal is that Claude is oriented from the first session.

## Documentation

Each repo should have a `/docs` directory. Markdown files go here unless tightly coupled to something else in the repo (e.g. a `SKILL.md` inside a skill directory, or a `README.md` co-located with code it documents). When in doubt, put it in `/docs`.

If the repo contains planning or research documents, they go in the corresponding subdirectory:

```
/docs/planning    ← specs, proposals, design decisions
/docs/research    ← background reading, spike notes, references
```

## File Organization

- Encapsulate coupled files together in directories named for their purpose.
- Avoid loose files in the root of the repo, or in directories that contain other encapsulated subdirectories.
- Use lowercase for directory names.
- Do not use hyphens in directory names.
- Use kebab-case for file names that contain a delimiter (e.g. `my-file.md`, not `my_file.md` or `myFile.md`). This is the default — per-language or per-file-type conventions take precedence (e.g. Swift files use `PascalCase.swift`, Python modules use `snake_case.py`).

**Allowed loose files in the repo root:**
- Any dot-prefixed file or directory (e.g. `.gitignore`, `.gitattributes`, `.claude/`, `.vscode/`)
- `.code-workspace` (Visual Studio Code workspace file)
- `README.md`

## Git

- Use lowercase for repo names.
- Do not use hyphens in repo names.

## LLMs

- Do not assume Claude is the LLM being used in a repo unless the repo is explicitly Claude-specific.
- For repos that are not Claude-specific: any Claude-related files go in a `/claude` directory.
- Every repo should be opted into Graphify for any LLM that supports it. Opting in requires:
  1. Graphify installed on the machine (`pip install graphifyy && graphify install`)
  2. `graphify-out/` added to `.gitignore` (generated output, not committed)
  3. A `.graphifyignore` if any directories should be excluded (same syntax as `.gitignore`)
  4. Run `/graphify` in a session to generate the initial graph

### Rules vs Behavioral Instructions

Not all rules are the same:

- **General policies** (like this document) — apply regardless of which LLM or tool is being used. These live in `/docs/rules/` and are written in plain language for anyone (human or AI) to follow.
- **Claude-specific behavioral instructions** — tell Claude how to behave in specific situations ("when X happens, do Y"). These belong in `.claude/CLAUDE.md` (project scope) or `/claude/rules/` (global scope), and are written as directives to Claude specifically.

If a rule would make sense for a human developer to follow, it's a general policy. If it's "Claude, remember to..." it's a behavioral instruction.

### Claude Extensions

Extensions to Claude's functionality (skills, rules, agents, MCP integrations, commands, plugins, hooks, etc.) are scoped by who they affect:

- **Global extensions** — affect Claude across all projects. These live in `/claude/<type>/`, named for the extension type:
  ```
  /claude/skills/
  /claude/plugins/
  /claude/rules/
  /claude/agents/
  /claude/commands/
  /claude/hooks/
  ```
  Global extensions must be installed and uninstalled by scripts in the `/setup` directory.

- **Repo-local extensions** — only affect Claude when working in this repo. These live in `.claude/`, following Claude Code's own conventions:
  ```
  .claude/skills/
  .claude/CLAUDE.md
  ```
  Repo-local extensions do not need install/uninstall scripts — Claude Code picks them up automatically.

## Setup

If a repo requires steps a developer must take to use it — automated scripts, tools, or installers — these go in a `/setup` directory.

- Setup scripts are named `install` (regardless of file type — `install.sh`, `install.py`, etc.).
- Every `install` must have a corresponding `uninstall` that reverses what it did.
- The uninstall counterpart is not required for prerequisite software that is managed externally (e.g. installing `brew` itself — that's the developer's responsibility to manage).
- Supporting files needed by the scripts (config files, assets, themes, etc.) go in `/setup/files/`.

## Scripting Language

**Always use Python for scripts.** NEVER write bash/shell scripts (.sh). This includes hooks, utilities, automation, build helpers, and any standalone script. If an existing bash script needs modification, rewrite it in Python.

**Exceptions:** `install.sh`, `uninstall.sh`, and `setup.sh` may be written as shell scripts.

**Python version:** Target Python 3.12 as the minimum. Install via `brew install python@3.12`.

## Required Tools

### All Platforms

| Tool | Notes |
|------|-------|
| Python 3.12+ | See Scripting Language rule |
| SQLite | Usually bundled with the OS |

### Apple [macOS only]

| Tool | Notes |
|------|-------|
| Xcode | Install from the Mac App Store |
| XcodeGen | `brew install xcodegen` — used to generate `.xcodeproj` from `project.yml` |

### Windows

| Tool | Notes |
|------|-------|
| Visual Studio | Install from https://visualstudio.microsoft.com |

## Recommended Tools

### Apple [macOS only]

| Tool | Notes |
|------|-------|
| Visual Studio Code | `brew install --cask visual-studio-code` |
| Claude Code | `npm install -g @anthropic-ai/claude-code` |

## Repo Layout

Multi-platform repos use top-level platform directories:

```
/apple
/windows
/android
```

Only create the directories relevant to the repo. Platform-specific code, projects, and tooling live exclusively under their platform directory.

## Apple [macOS only]

### Swift

**All Swift code must target the latest patch release of Swift 6.2 (i.e. 6.2.x).** Use `// swift-tools-version: 6.2` in Package.swift files and write code that compiles cleanly under Swift 6 concurrency rules (`@Sendable`, `@MainActor`, strict data-race safety). Do not downgrade to Swift 5 language mode. Do not upgrade to Swift 6.3 or later without an explicit decision to do so.

### Project Structure

Each Apple project lives in its own subdirectory under `/apple`:

```
/apple/ProjectName1/
/apple/ProjectName2/
```

### Xcode Projects over Swift Packages

**Always use Xcode projects, never Swift Package Manager as the primary project format.**

- Every project must have a `project.yml` (XcodeGen spec) at the root of its project directory, e.g. `/apple/MyProject/project.yml`.
- The generated `.xcodeproj` is checked into the repo alongside `project.yml`.

#### Converting from a Swift Package

When converting a `Package.swift`-based project to an Xcode project:

1. Create `project.yml` with equivalent targets and settings.
2. **Include a test target** — migrate all existing tests into it.
3. Set the signing team to `mikefullerton` (Temporal Apple Developer account) and preserve all entitlements.
4. **Always build and run tests after converting** before considering the migration complete.

### Xcode Workspace

The `/apple` directory must contain a single `.xcworkspace` that includes all Xcode projects in the repo:

- Include every `.xcodeproj` directly under `/apple/<ProjectName>/`.
- For submodules (their directories sit at the repo root): include their Xcode projects **one level deep only** — if a submodule itself contains submodules, do not include those nested projects.

### Code Signing

- **Team:** `mikefullerton` (Temporal Apple Developer account)
- Preserve all entitlements when modifying project settings or converting projects.
- Provisioning profiles and certificates are managed on the local machine only — never check them into the repo. Use Xcode's automatic signing where possible.
