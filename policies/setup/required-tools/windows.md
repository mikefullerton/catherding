---
title: "Required Tools — Windows"
summary: "Windows machines must have Visual Studio installed."
triggers: [machine-setup, dependency-audit, new-dev-machine, tooling-setup, windows-setup]
tags: [tooling, dependencies, setup, windows]
---

# Required Tools

Machine must have Python 3.12+ and SQLite (all platforms), Xcode (Apple), Visual Studio (Windows).

## All Platforms

| Tool | Notes |
|------|-------|
| Python 3.12+ | See [scripting](scripting.md) |
| SQLite | Usually bundled with the OS |

## Apple [macOS only]

| Tool | Notes |
|------|-------|
| Xcode | Install from the Mac App Store |

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

**Derived from cookbook:** [explicit-over-implicit](../../../../agenticcookbook/principles/explicit-over-implicit.md)
