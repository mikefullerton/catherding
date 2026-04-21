---
title: "Required Tools"
summary: "Machine must have Python 3.12+ and SQLite (all platforms), Xcode + XcodeGen (Apple), Visual Studio (Windows)."
triggers: [machine-setup, dependency-audit, new-dev-machine, tooling-setup]
tags: [tooling, dependencies, setup]
---

# Required Tools

Machine must have Python 3.12+ and SQLite (all platforms), Xcode + XcodeGen (Apple), Visual Studio (Windows).

## All Platforms

| Tool | Notes |
|------|-------|
| Python 3.12+ | See [scripting-language](../shell-scripting/scripting-language.md) |
| SQLite | Usually bundled with the OS |

## Apple [macOS only]

| Tool | Notes |
|------|-------|
| Xcode | Install from the Mac App Store |
| XcodeGen | `brew install xcodegen` — used to generate `.xcodeproj` from `project.yml` |

## Windows

| Tool | Notes |
|------|-------|
| Visual Studio | Install from https://visualstudio.microsoft.com |

## Recommended (not required)

### Apple [macOS only]

| Tool | Notes |
|------|-------|
| Visual Studio Code | `brew install --cask visual-studio-code` |
| Claude Code | `npm install -g @anthropic-ai/claude-code` |

**Derived from cookbook:** [explicit-over-implicit](../../../agenticcookbook/principles/explicit-over-implicit.md)
