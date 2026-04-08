#!/usr/bin/env python3
"""Scaffold a new project with standard files.

Usage:
    python3 setup-project.py <name> <org> <description> [target-dir]

If target-dir is omitted, uses ~/projects/active/<name>.
"""
import argparse
import os
import sys

RESET = "\033[0m"
GREEN = "\033[32m"
BOLD = "\033[1m"


def main():
    parser = argparse.ArgumentParser(description="Scaffold a new project")
    parser.add_argument("name", help="Project name")
    parser.add_argument("org", help="GitHub organization")
    parser.add_argument("description", help="Brief project description")
    parser.add_argument("target", nargs="?", default=None, help="Target directory")
    args = parser.parse_args()

    target = args.target or os.path.expanduser(f"~/projects/active/{args.name}")

    if not os.path.isdir(target):
        print(f"Error: target directory does not exist: {target}", file=sys.stderr)
        sys.exit(1)

    files = {
        "README.md": f"# {args.name}\n\n{args.description}\n",
        ".claude/CLAUDE.md": f"""# {args.name}

{args.description}

## Tech Stack
- (to be determined)

## Build
(to be determined)

## Architecture
(to be determined)
""",
        ".gitignore": """.DS_Store
.claude/worktrees/
.claude/settings.local.json
.env
.superpowers/
""",
        ".claude/settings.json": """{
  "enabledPlugins": {
    "superpowers@claude-plugins-official": true
  }
}
""",
        "docs/planning/planning.md": f"# {args.name} — Planning\n\n(to be determined)\n",
        "docs/project/description.md": f"# {args.name}\n\n{args.description}\n",
    }

    print(f"\n{BOLD}Scaffolding {args.name}{RESET}\n")

    for rel_path, content in files.items():
        full = os.path.join(target, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        print(f"  {GREEN}+{RESET} {rel_path}")

    print(f"\n{GREEN}{len(files)} files created{RESET} in {target}\n")


if __name__ == "__main__":
    main()
