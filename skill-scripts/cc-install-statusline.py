#!/usr/bin/env python3
"""Install status line changes to ~/.claude-status-line/ and run tests.

Usage: install-statusline.py [--skip-tests]

Copies:
  skills/custom-status-line/references/statusline/*.py
    → ~/.claude-status-line/statusline/
  skills/custom-status-line/references/scripts/*.py
    → ~/.claude-status-line/scripts/
  skills/custom-status-line/references/hooks/*.py
    → ~/.claude/hooks/   (status-line hook scripts, e.g. session-tracker.py)

Clears pycache and runs the test suite (skip with --skip-tests).
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

def _find_repo_root() -> Path:
    """Locate the cat-herding repo.

    Works both when invoked in-tree (via `python3 scripts/install-statusline.py`)
    and when invoked as a copy under `~/.local/bin/cc-install-statusline`, where
    `__file__` points into `~/.local/` and the old `parent.parent` trick breaks.

    Search order:
      1. Walk up from cwd looking for `scripts/cc-install.py`
         (unique to cat-herding).
      2. Fall back to the canonical path documented in global CLAUDE.md.
    """
    marker = Path("scripts/cc-install.py")
    p = Path.cwd().resolve()
    for candidate in (p, *p.parents):
        if (candidate / marker).is_file():
            return candidate
    return Path.home() / "projects/active/cat-herding"


HERE = _find_repo_root()
SRC_STATUSLINE = HERE / "skills/custom-status-line/references/statusline"
SRC_SCRIPTS = HERE / "skills/custom-status-line/references/scripts"
SRC_HOOKS = HERE / "skills/custom-status-line/references/hooks"
INSTALLED = Path.home() / ".claude-status-line"
INSTALLED_STATUSLINE = INSTALLED / "statusline"
INSTALLED_SCRIPTS = INSTALLED / "scripts"
INSTALLED_HOOKS = Path.home() / ".claude" / "hooks"


def copy_tree(src: Path, dst: Path) -> int:
    """Copy all files from src/ to dst/, overwriting. Return count copied."""
    if not src.is_dir():
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for f in src.glob("*.py"):
        shutil.copy2(f, dst / f.name)
        count += 1
    return count


def clear_pycache(root: Path):
    """Recursively remove __pycache__ directories."""
    for p in root.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Install status line and run tests.")
    ap.add_argument("--skip-tests", action="store_true", help="Skip pytest run")
    args = ap.parse_args()

    if not SRC_STATUSLINE.is_dir():
        print(f"FAIL: {SRC_STATUSLINE} not found", file=sys.stderr)
        print(f"  resolved repo root: {HERE}", file=sys.stderr)
        print(f"  cwd: {Path.cwd()}", file=sys.stderr)
        print("  fix: cd into the cat-herding repo, or correct the fallback path "
              "in _find_repo_root()", file=sys.stderr)
        sys.exit(2)

    n_sl = copy_tree(SRC_STATUSLINE, INSTALLED_STATUSLINE)
    n_sc = copy_tree(SRC_SCRIPTS, INSTALLED_SCRIPTS)
    n_hk = copy_tree(SRC_HOOKS, INSTALLED_HOOKS)
    clear_pycache(INSTALLED)
    # Hook scripts must be executable — Claude Code invokes them as commands.
    for f in INSTALLED_HOOKS.glob("*.py"):
        os.chmod(f, 0o755)

    print(f"installed: {n_sl} statusline + {n_sc} scripts + {n_hk} hooks files")

    if args.skip_tests:
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = str(INSTALLED)
    tests_dir = HERE / "skills/custom-status-line/tests"
    result = subprocess.run(
        ["python3", "-m", "pytest", str(tests_dir), "-q"],
        env=env,
        capture_output=True,
        text=True,
    )
    # Print last line of pytest output for a tight summary
    last_lines = result.stdout.strip().splitlines()
    summary = last_lines[-1] if last_lines else "(no pytest output)"
    print(summary)
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
