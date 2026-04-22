#!/usr/bin/env python3
"""Verify every cc-* entry is a copy of its canonical source and is executable.

Usage: cc-doctor

Walks both `~/.local/bin/cc-*` (regular scripts) and `~/.claude/hooks/cc-*-hook.py`
(Claude Code hook scripts). Reports missing installs (canonical source has no
installed copy), stale copies (content differs from source — re-run
cc-install), orphans (installed file has no matching canonical source),
non-executable entries, and legacy symlinks (old install model). Also checks
the global CLAUDE.md guidance block for stale unmarked duplicates, and
checks that each policy skill references at least one policy file in
policies/. Exits non-zero on any problem.
"""
from __future__ import annotations

import filecmp
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

# Hook source files listed here are expected to be installed; others in
# scripts-hooks/ stay as source-only. Mirrors ACTIVE_HOOKS in install.sh
# and cc-install.py.
ACTIVE_HOOKS = {"cc-general-principles-hook"}
POLICIES_DIR = REPO_ROOT / "policies"
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


def _canonical_sources() -> dict[Path, Path]:
    """Map install-target path -> canonical source path for every cc-*.py.

    Hook sources not in ACTIVE_HOOKS are treated as source-only (skipped —
    they're not expected to appear in ~/.claude/hooks/).
    """
    by_target: dict[Path, Path] = {}
    for src_dir in CANONICAL_SOURCES:
        if not src_dir.is_dir():
            continue
        for script in sorted(src_dir.glob("cc-*.py")):
            if not script.is_file():
                continue
            if script.stem.endswith("-hook"):
                if script.stem not in ACTIVE_HOOKS:
                    continue
                target = HOOKS_DIR / script.name
            else:
                target = BIN_DIR / script.stem
            by_target[target] = script
    return by_target


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
    """Each installed policy skill must reference at least one policies/ file.

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
        if "policies/" not in text:
            issues.append(f"  {skill}: no back-reference to policies/")
            drift += 1
    return drift


def main() -> int:
    if not BIN_DIR.is_dir() and not HOOKS_DIR.is_dir():
        print(f"FAIL: neither {BIN_DIR} nor {HOOKS_DIR} exists", file=sys.stderr)
        return 1

    ok = missing = stale = orphan = legacy_symlink = not_exec = 0
    issues: list[str] = []
    claude_md_drift = _check_claude_md_drift(issues)
    policy_drift = _check_policy_skill_refs(issues)

    by_target = _canonical_sources()
    installed = {e: e for e in _entries()}

    for target, script in by_target.items():
        entry = installed.pop(target, None)
        if entry is None:
            missing += 1
            issues.append(f"  missing install: {target} (source: {script})")
            continue
        if entry.is_symlink():
            legacy_symlink += 1
            issues.append(f"  legacy symlink (re-run cc-install): {entry} -> {os.readlink(entry)}")
            continue
        if not entry.is_file():
            issues.append(f"  not a regular file: {entry}")
            stale += 1
            continue
        if not os.access(entry, os.X_OK):
            not_exec += 1
            issues.append(f"  not executable: {entry}")
            continue
        if not filecmp.cmp(script, entry, shallow=False):
            stale += 1
            issues.append(f"  stale copy (re-run cc-install): {entry} ≠ {script}")
            continue
        ok += 1

    for entry in installed.values():
        orphan += 1
        issues.append(f"  orphan (no canonical source): {entry}")

    for line in issues:
        print(line)

    summary = (
        f"did: ok {ok} | missing {missing} | stale {stale} | orphan {orphan}"
        f" | legacy-symlink {legacy_symlink} | not-executable {not_exec}"
        f" | claude.md drift {claude_md_drift} | policy drift {policy_drift}"
    )
    if missing or stale or orphan or legacy_symlink or not_exec or claude_md_drift or policy_drift:
        print(summary, file=sys.stderr)
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
