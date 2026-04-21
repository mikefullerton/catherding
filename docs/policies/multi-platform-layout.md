---
title: "Multi-Platform Layout"
summary: "Multi-platform repos use top-level /apple, /windows, /android directories — only those relevant to the repo."
triggers: [starting-multi-platform-project, adding-platform, repo-restructure]
tags: [multi-platform, repo-structure]
---

# Multi-Platform Layout

Multi-platform repos use top-level `/apple`, `/windows`, `/android` directories — only those relevant to the repo.

- Multi-platform repos MUST use top-level platform directories:
  ```
  /apple
  /windows
  /android
  ```
- You MUST create only the directories relevant to the repo.
- Platform-specific code, projects, and tooling MUST live exclusively under their platform directory.

**Derived from cookbook:** [separation-of-concerns](../../../agenticcookbook/principles/separation-of-concerns.md)
