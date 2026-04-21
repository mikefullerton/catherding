---
title: "File Organization"
summary: "Encapsulate coupled files in directories; lowercase dirs with no hyphens; kebab-case filenames unless the language says otherwise."
triggers: [creating-file, creating-directory, renaming-file, file-audit, repo-restructure]
tags: [naming, files, directories, organization]
---

# File Organization

Encapsulate coupled files in directories; lowercase dirs with no hyphens; kebab-case filenames unless the language says otherwise.

- You MUST encapsulate coupled files together in directories named for their purpose.
- You MUST NOT leave loose files in the repo root, or in directories that contain other encapsulated subdirectories.
- Directory names MUST be lowercase.
- Directory names MUST NOT contain hyphens.
- File names with a delimiter MUST use kebab-case (`my-file.md`, not `my_file.md` or `myFile.md`).
- Per-language or per-file-type conventions take precedence over kebab-case (e.g. Swift files use `PascalCase.swift`, Python modules use `snake_case.py`).

**Allowed loose files in the repo root:**

- Any dot-prefixed file or directory (`.gitignore`, `.gitattributes`, `.claude/`, `.vscode/`, …)
- `.code-workspace` (Visual Studio Code workspace file)
- `README.md`

**Derived from cookbook:** [principle-of-least-astonishment](../../../agenticcookbook/principles/principle-of-least-astonishment.md), [manage-complexity-through-boundaries](../../../agenticcookbook/principles/manage-complexity-through-boundaries.md)
