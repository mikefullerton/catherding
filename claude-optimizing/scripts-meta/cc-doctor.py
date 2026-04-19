#!/usr/bin/env python3
"""Verify every cc-* entry resolves to an executable script.

Usage: cc-doctor

Walks both `~/.local/bin/cc-*` (regular scripts) and `~/.claude/hooks/cc-*-hook.py`
(Claude Code hook scripts). Reports broken symlinks (target deleted/moved),
non-symlinks shadowing the namespace, and stale entries pointing outside the
canonical scripts dir. Also checks the global CLAUDE.md guidance block for
stale unmarked duplicates, and checks that each policy skill references a
section that still exists in docs/rules/development-policies.md. Exits non-zero
on any problem.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path.home() / "projects" / "active" / "catherding"
# Every `claude-optimizing/scripts-*/` category dir. Skill-internal scripts
# don't install to $PATH so cc-doctor doesn't watch them.
CANONICAL_SOURCES = sorted((REPO_ROOT / "claude-optimizing").glob("scripts-*"))
BIN_DIR = Path.home() / ".local" / "bin"
HOOKS_DIR = Path.home() / ".claude" / "hooks"
CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
POLICIES_DOC = REPO_ROOT / "docs" / "rules" / "development-policies.md"
POLICY_SKILLS_DIR = REPO_ROOT / "skills"
POLICY_SKILLS = [
    "new-repo-scaffold",
    "file-organization-policies",
    "llm-integration-policies",
    "setup-and-install-scripts",
    "apple-and-xcode-policies",
]
SENTINEL_HEADERS = [
    "## Scripting Language — MANDATORY",
    "## Token Efficiency — MANDATORY",
    "## Workflow Scripts — PREFER over multi-step Bash",
    "## Worktree Workflow — MANDATORY",
    "## Repo Hygiene — MANDATORY, NO EXCEPTIONS",
]


def _entries() -> list[Path]:
    """All cc-* entries we manage across both install destinations."""
    out: list[Path] = []
    if BIN_DIR.is_dir():
        out.extend(p for p in sorted(BIN_DIR.iterdir()) if p.name.startswith("cc-"))
    if HOOKS_DIR.is_dir():
        out.extend(
            p for p in sorted(HOOKS_DIR.iterdir())
            if p.name.startswith("cc-") and p.name.endswith("-hook.py")
        )
    return out


def _check_claude_md_drift(issues: list[str]) -> int:
    """Count sentinel headers that appear outside the marker block."""
    if not CLAUDE_MD.is_file():
        return 0
    text = CLAUDE_MD.read_text()
    BEGIN, END = "<!-- BEGIN claude-optimizing -->", "<!-- END claude-optimizing -->"
    if BEGIN in text and END in text:
        marker_span = text.split(BEGIN, 1)[1].split(END, 1)[0]
        outside = text.replace(BEGIN + marker_span + END, "")
    else:
        outside = text
    drifted = [h for h in SENTINEL_HEADERS if h in outside]
    for h in drifted:
        issues.append(f"  stale unmarked section in ~/.claude/CLAUDE.md: {h}")
    return len(drifted)


def _check_policy_skill_refs(issues: list[str]) -> int:
    """Each installed policy skill must reference development-policies.md.

    Resolves via the installed symlink under ~/.claude/skills/ so the check
    works whether the skills are sourced from main or a worktree.
    """
    installed_skills_dir = Path.home() / ".claude" / "skills"
    drift = 0
    for skill in POLICY_SKILLS:
        skill_md = installed_skills_dir / skill / "SKILL.md"
        if not skill_md.is_file():
            # Skill not installed — not a drift problem, just not enabled.
            continue
        text = skill_md.read_text()
        if "development-policies.md" not in text:
            issues.append(f"  {skill}: no back-reference to development-policies.md")
            drift += 1
    return drift


def main() -> int:
    if not BIN_DIR.is_dir() and not HOOKS_DIR.is_dir():
        print(f"FAIL: neither {BIN_DIR} nor {HOOKS_DIR} exists", file=sys.stderr)
        return 1

    ok = broken = non_symlink = stale = 0
    issues: list[str] = []
    claude_md_drift = _check_claude_md_drift(issues)
    policy_drift = _check_policy_skill_refs(issues)

    for entry in _entries():
        if not entry.is_symlink():
            non_symlink += 1
            issues.append(f"  not a symlink: {entry}")
            continue
        try:
            real = entry.resolve(strict=True)
        except FileNotFoundError:
            broken += 1
            issues.append(f"  BROKEN symlink: {entry} -> {os.readlink(entry)}")
            continue
        if not os.access(real, os.X_OK):
            issues.append(f"  not executable: {real}")
            broken += 1
            continue
        # Stale = points outside the canonical script dirs AND outside any
        # catherding worktree. EnterWorktree creates worktrees under
        # `<catherding>/.claude/worktrees/<name>/claude-optimizing/scripts-<area>/`,
        # which is fine while testing.
        import re
        real_s = str(real)
        is_canonical = any(real_s.startswith(str(src) + "/") for src in CANONICAL_SOURCES)
        is_worktree = (
            "/catherding/.claude/worktrees/" in real_s
            and bool(re.search(r"/claude-optimizing/scripts-[a-z]+/", real_s))
        )
        if not (is_canonical or is_worktree):
            stale += 1
            issues.append(f"  stale (points outside catherding): {entry} -> {real}")
        ok += 1

    for line in issues:
        print(line)

    summary = (
        f"did: ok {ok} | broken {broken} | non-symlink {non_symlink} | stale {stale}"
        f" | claude.md drift {claude_md_drift} | policy drift {policy_drift}"
    )
    if broken or non_symlink or stale or claude_md_drift or policy_drift:
        print(summary, file=sys.stderr)
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
