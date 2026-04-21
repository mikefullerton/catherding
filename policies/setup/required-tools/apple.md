---
title: "Required Tools"
summary: "Machine must have Python 3.12+ and SQLite (all platforms), Xcode + XcodeGen (Apple), Visual Studio (Windows)."
triggers: [machine-setup, dependency-audit, new-dev-machine, tooling-setup]
tags: [tooling, dependencies, setup]
---

# Required Tools

## Apple [macOS only]

| Tool | Notes |
|------|-------|
| Xcode | Install from the Mac App Store |
| XcodeGen | `brew install xcodegen` — used to generate `.xcodeproj` from `project.yml` |

## Recommended (not required)

### Apple [macOS only]

| Tool | Notes |
|------|-------|
| Visual Studio Code | `brew install --cask visual-studio-code` |
| Claude Code | `npm install -g @anthropic-ai/claude-code` |

