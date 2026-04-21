---
name: new-repo-scaffold
description: Use when creating a new repo (git init, gh repo create, scaffolding a new project) or when a repo is missing README/LICENSE/.gitignore/.claude/CLAUDE.md. Enforces the "every repo must have" checklist and documentation layout.
---

# New Repo Scaffold — MANDATORY

Every repo under `~/projects/` must have these files in the root before work proceeds. When creating a new repo or noticing any are missing, create them — but follow the rules below, don't just drop templates.

## Required files

- **`README.md`** — describes what the repo is. Keep it current as the repo evolves.
- **`LICENSE`** — **ask before choosing.** Default is All Rights Reserved:
  ```
  Copyright (c) <year> <author>. All rights reserved.
  ```
  Alternative: MIT. **Do not add a license without asking the user.**
- **`.gitignore`** — on macOS, always ignore `.DS_Store`.
- **`.claude/CLAUDE.md`** — project-specific Claude instructions. **Never** `CLAUDE.md` in the repo root. At minimum covers: what the repo is, its directory structure, how to build/run it. A placeholder is fine — the goal is Claude is oriented on first session.

## Documentation layout

If the repo has documentation, it goes in `/docs`:

```
/docs              ← general docs
/docs/planning     ← specs, proposals, design decisions
/docs/research     ← background reading, spike notes, references
```

Exceptions: `SKILL.md` stays inside its skill dir; `README.md` stays co-located with the code it documents. When in doubt, `/docs`.

## Git naming

- Repo names: lowercase, no hyphens (e.g. `mysetup`, not `my-setup`).

## Reference

Full rationale and the rest of the standard: `~/projects/active/catherding/docs/policies/development-policies.md` (sections: "Every Repo Must Have", "Documentation", "Git").
