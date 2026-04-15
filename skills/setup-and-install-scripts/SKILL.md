---
name: setup-and-install-scripts
description: Use when authoring or modifying install/uninstall scripts, or when creating a /setup directory for a repo that requires developer setup steps. Enforces the /setup layout, install/uninstall naming, and supporting-files location.
---

# Setup & Install Scripts — MANDATORY

## When a /setup directory is required

If a repo requires steps a developer must take to use it — automated scripts, tools, or installers — those go in a `/setup` directory.

## Naming

- Setup scripts are named `install` (regardless of file extension): `install.sh`, `install.py`, etc.
- **Every `install` must have a corresponding `uninstall`** that reverses what it did.
- The uninstall counterpart is *not* required for prerequisite software managed externally (e.g. installing `brew` itself — that's the developer's responsibility).

## Supporting files

- Config files, assets, themes, and anything else the scripts need → `/setup/files/`.

## Shell exception reminder

`install.sh`, `uninstall.sh`, and `setup.sh` are the *only* `.sh` exceptions to the "Python for scripts" rule. See `~/.claude/CLAUDE.md` → "Scripting Language — MANDATORY".

## Reference

Full rationale: `~/projects/active/cat-herding/docs/rules/development-policies.md` (section: "Setup").
