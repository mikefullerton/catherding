#!/usr/bin/env python3
"""Manage Claude Code per-project auto-memory: add entries and list the index.

Usage:
  cc-memory list [--project PATH]
  cc-memory add <type> <name> --description DESC [--slug SLUG]
                [--body TEXT | --body-file PATH | --body-stdin]
                [--hook TEXT] [--project PATH] [--force]

`<type>` is one of: user, feedback, project, reference.
`<name>` is the human-readable title (also used as the MEMORY.md link text).
Filename becomes `<type>_<slug>.md` where slug defaults to a slugified name.

Writes the memory file with proper frontmatter and appends a one-line entry
to MEMORY.md atomically. Memory dir is inferred from the current working
directory: ~/.claude/projects/<encoded-cwd>/memory/ (cwd with '/' -> '-').

Exit 0 on success; 1 on validation errors or if the slug already exists
(override with --force).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VALID_TYPES = ("user", "feedback", "project", "reference")


def memory_dir_for(project_path: Path) -> Path:
    encoded = str(project_path.resolve()).replace("/", "-")
    return Path.home() / ".claude" / "projects" / encoded / "memory"


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def cmd_list(project: Path) -> int:
    mdir = memory_dir_for(project)
    index = mdir / "MEMORY.md"
    if not index.is_file():
        print(f"cc-memory: no MEMORY.md at {index}", file=sys.stderr)
        return 1
    text = index.read_text()
    print(text, end="" if text.endswith("\n") else "\n")
    # Surface broken links (entries pointing to missing files).
    broken = []
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", text):
        target = mdir / m.group(2)
        if not target.is_file():
            broken.append(m.group(2))
    if broken:
        print(f"did: listed {index} | broken links: {len(broken)}", file=sys.stderr)
        for b in broken:
            print(f"  missing: {b}", file=sys.stderr)
        return 1
    print(f"did: listed {index}")
    return 0


def read_body(args: argparse.Namespace) -> str:
    sources = [args.body, args.body_file, args.body_stdin]
    if sum(x is not None and x is not False for x in sources) > 1:
        raise SystemExit("cc-memory: specify at most one of --body / --body-file / --body-stdin")
    if args.body is not None:
        return args.body
    if args.body_file is not None:
        return Path(args.body_file).read_text()
    if args.body_stdin:
        return sys.stdin.read()
    return ""


def cmd_add(args: argparse.Namespace) -> int:
    if args.type not in VALID_TYPES:
        print(f"cc-memory: invalid type '{args.type}' (expected {'|'.join(VALID_TYPES)})", file=sys.stderr)
        return 1

    name = args.name.strip()
    if not name:
        print("cc-memory: name is required", file=sys.stderr)
        return 1

    description = args.description.strip()
    if not description:
        print("cc-memory: --description is required", file=sys.stderr)
        return 1

    slug = args.slug.strip() if args.slug else slugify(name)
    if not slug:
        print("cc-memory: could not derive slug from name; pass --slug", file=sys.stderr)
        return 1

    mdir = memory_dir_for(Path(args.project))
    if not mdir.is_dir():
        print(f"cc-memory: memory dir does not exist: {mdir}", file=sys.stderr)
        return 1

    filename = f"{args.type}_{slug}.md"
    target = mdir / filename
    if target.exists() and not args.force:
        print(f"cc-memory: {target} already exists (use --force to overwrite)", file=sys.stderr)
        return 1

    raw_body = read_body(args)
    body = raw_body.rstrip() + "\n" if raw_body.strip() else ""
    content = _compose(args.type, name, description, body)

    hook = (args.hook or description).strip().splitlines()[0]
    index = mdir / "MEMORY.md"
    new_line = f"- [{name}]({filename}) — {hook}\n"

    # Atomic-ish: write file, then update index. Roll back file on index failure.
    target.write_text(content)
    try:
        _append_or_replace_index(index, filename, new_line)
    except OSError as exc:
        if not args.force:
            target.unlink(missing_ok=True)
        print(f"cc-memory: failed to update index: {exc}", file=sys.stderr)
        return 1

    print(f"did: wrote {target} | updated {index}")
    return 0


def _compose(mtype: str, name: str, description: str, body: str) -> str:
    header = (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        f"type: {mtype}\n"
        "---\n"
    )
    if body:
        return header + "\n" + body
    return header


def _append_or_replace_index(index: Path, filename: str, new_line: str) -> None:
    if not index.exists():
        index.write_text("# Memory Index\n\n" + new_line)
        return
    text = index.read_text()
    pattern = re.compile(rf"^- \[[^\]]+\]\({re.escape(filename)}\) —.*$", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(new_line.rstrip(), text)
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += new_line
    index.write_text(text)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="cc-memory",
        description="Manage Claude Code per-project auto-memory entries.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="Print MEMORY.md for the current project")
    p_list.add_argument("--project", default=".", help="Project path (default: cwd)")

    p_add = sub.add_parser("add", help="Create a memory file + update MEMORY.md index")
    p_add.add_argument("type", help=f"Memory type ({'|'.join(VALID_TYPES)})")
    p_add.add_argument("name", help="Human-readable memory name (also the index link text)")
    p_add.add_argument("--description", required=True, help="One-line description for frontmatter")
    p_add.add_argument("--slug", help="Override filename slug (default: slugified name)")
    p_add.add_argument("--body", help="Memory body as a literal string")
    p_add.add_argument("--body-file", help="Read memory body from file path")
    p_add.add_argument("--body-stdin", action="store_true", help="Read memory body from stdin")
    p_add.add_argument("--hook", help="Index hook after the em-dash (default: description)")
    p_add.add_argument("--project", default=".", help="Project path (default: cwd)")
    p_add.add_argument("--force", action="store_true", help="Overwrite existing memory file")

    args = parser.parse_args()
    if args.cmd == "list":
        return cmd_list(Path(args.project))
    if args.cmd == "add":
        return cmd_add(args)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
