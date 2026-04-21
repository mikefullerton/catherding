---
name: file-organization-policies
description: Use when creating a new file or directory in an unfamiliar location, or when reviewing whether a file is in the right place. Enforces directory/file naming and encapsulation rules.
---

# File Organization — MANDATORY

## Directories

- **Encapsulate coupled files together** in directories named for their purpose.
- **Avoid loose files** in the repo root, or in directories that already contain encapsulated subdirectories.
- **Lowercase** directory names only.
- **No hyphens** in directory names.

## Files

- **Kebab-case** for file names that contain a delimiter: `my-file.md`, not `my_file.md` or `myFile.md`.
- **Language conventions win** where they conflict with kebab-case:
  - Swift: `PascalCase.swift`
  - Python modules: `snake_case.py`
- **When in doubt**, kebab-case.

## Allowed loose files in the repo root

Only these belong at the top level:

- Any dot-prefixed file or directory (`.gitignore`, `.gitattributes`, `.claude/`, `.vscode/`, etc.)
- `*.code-workspace` (VS Code workspace files)
- `README.md`

Anything else goes in a subdirectory.

## Reference

Full rationale in [`~/projects/active/catherding/policies/repo-organization/file-organization.md`](../../policies/repo-organization/file-organization.md). See [INDEX.md](../../policies/INDEX.md) for related policies.
