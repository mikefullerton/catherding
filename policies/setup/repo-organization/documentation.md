---
title: "Documentation"
summary: "Markdown goes in /docs. Planning and research documents go in /docs/planning and /docs/research."
triggers: [writing-docs, planning-feature, adding-research-notes, organizing-docs]
tags: [documentation, docs, organization]
---

# Documentation

Markdown goes in /docs. Planning and research documents go in /docs/planning and /docs/research.

- Every repo SHOULD have a `/docs` directory.
- Markdown files MUST go in `/docs` unless tightly coupled to something else in the repo (e.g. a `SKILL.md` inside a skill directory, a `README.md` co-located with the code it documents).
- When in doubt, put it in `/docs`.
- Planning documents (specs, proposals, design decisions) MUST go in `/docs/planning/`.
- Research documents (background reading, spike notes, references) MUST go in `/docs/research/`.

**Derived from cookbook:** [separation-of-concerns](../../../../agenticcookbook/principles/separation-of-concerns.md), [principle-of-least-astonishment](../../../../agenticcookbook/principles/principle-of-least-astonishment.md)
