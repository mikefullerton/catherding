---
title: "Repo Baseline"
summary: "Every repo must have README, LICENSE, .gitignore, and .claude/CLAUDE.md."
triggers: [new-repo, repo-audit, starting-new-project]
tags: [repo-structure, baseline, required-files]
---

# Repo Baseline

Every repo must have README, LICENSE, .gitignore, and .claude/CLAUDE.md.

- Repos MUST contain `README.md` in the root. Keep it up to date as the repo evolves.
- Repos MUST contain `LICENSE` in the root. If missing, prompt the user to choose one before proceeding. Default to All Rights Reserved:
  ```
  Copyright (c) <year> <author>. All rights reserved.
  ```
  Alternative: MIT License. You MUST NOT add a license without asking.
- Repos MUST contain `.gitignore`. On macOS, it MUST ignore `.DS_Store`.
- Repos MUST contain `.claude/CLAUDE.md` (NOT a `CLAUDE.md` in the repo root). At minimum it SHOULD cover:
  - what the repo is
  - its directory structure
  - how to run or build it

  A minimal placeholder is fine — the goal is that Claude is oriented from the first session.

**Derived from cookbook:** [principle-of-least-astonishment](../../../agenticcookbook/principles/principle-of-least-astonishment.md), [support-automation](../../../agenticcookbook/principles/support-automation.md)
