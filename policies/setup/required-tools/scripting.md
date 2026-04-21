---
title: "Scripting Language"
summary: "Use Python 3.12+ for scripts. Only install.sh, uninstall.sh, and setup.sh may be shell."
triggers: [writing-script, tooling-setup, automation-task, writing-hook]
tags: [python, scripting, language-version]
---

# Scripting Language

Use Python 3.12+ for scripts. Only `install.sh`, `uninstall.sh`, and `setup.sh` may be shell.

- You MUST use Python for scripts (hooks, utilities, automation, build helpers, standalone scripts).
- You MUST NOT write bash or shell scripts (`.sh`), with the exceptions below.
- If an existing bash script needs modification, you SHOULD rewrite it in Python.
- **Exceptions:** `install.sh`, `uninstall.sh`, and `setup.sh` MAY be written as shell scripts.
- Target Python 3.12 as the minimum version. Install via `brew install python@3.12`.

**Derived from cookbook:** [principle-of-least-astonishment](../../../../agenticcookbook/principles/principle-of-least-astonishment.md), [simplicity](../../../../agenticcookbook/principles/simplicity.md)
