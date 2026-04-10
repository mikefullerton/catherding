# Cat Herding

A personal collection of Claude Code plugins, skills, CLI tools, and configuration rules that augment development workflows.

## Purpose

Cat Herding functions as a local plugin marketplace for Claude Code. It provides installable plugins, reusable skills, and two Python CLIs (site-manager and webinator) for managing web infrastructure. Everything is designed for zero or minimal external dependencies.

## Key Features

- 6 installable Claude Code plugins (yolo, custom-status-line, repo-cleaner, show-project-setup, site-manager, webinator)
- 11 local skills (lint-skill, lint-rule, lint-agent, optimize-rules, install-worktree-rule, and more)
- site-manager CLI v0.3.0 — multi-site web deployment manager (8 commands)
- webinator CLI v0.1.0 — web infrastructure manager (11+ commands)
- Configuration rules for CLI versioning and plugin development workflows
- Research documents on Claude Code capabilities

## Tech Stack

- **Language:** Python 3.11+ (CLIs — zero external dependencies, stdlib only)
- **Testing:** pytest, Vitest (JavaScript test harness)
- **Plugins:** Bash shell scripts, YAML manifests
- **Build:** `uv` (Python tool installer)

## Status

Active development.

## Related Projects

- [Roadmaps](../../roadmaps/docs/project/description.md) — feature planning system (also a Claude Code extension)
- [Tools](../../tools/docs/project/description.md) — agentic-cookbook skills and rules
