---
title: "Setup Scripts"
summary: "Setup steps live in /setup/. Every install has a matching uninstall."
triggers: [writing-install-script, adding-setup-step, repo-bootstrap, adding-install-uninstall]
tags: [setup, installation, scripts]
---

# Setup Scripts

Setup steps live in `/setup/`. Every install has a matching uninstall.

- If a repo requires steps a developer must take to use it (automated scripts, tools, installers), these MUST go in a `/setup` directory.
- Setup scripts MUST be named `install` (regardless of file type — `install.sh`, `install.py`, etc.).
- Every `install` MUST have a corresponding `uninstall` that reverses what it did.
- The uninstall counterpart is NOT required for prerequisite software that is managed externally (e.g. installing `brew` itself — that's the developer's responsibility to manage).
- Supporting files needed by the scripts (config files, assets, themes, etc.) MUST go in `/setup/files/`.

**Derived from cookbook:** [support-automation](../../../agenticcookbook/principles/support-automation.md), [idempotency](../../../agenticcookbook/principles/idempotency.md)
