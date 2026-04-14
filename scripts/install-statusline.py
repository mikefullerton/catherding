#!/usr/bin/env python3
"""Install status line changes to ~/.claude-status-line/ and run tests.

Usage: install-statusline.py [--skip-tests]

Copies all .py files from skills/custom-status-line/references/statusline/
to ~/.claude-status-line/statusline/, plus any changed scripts, clears pycache,
and runs the test suite.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SRC_STATUSLINE = HERE / "skills/custom-status-line/references/statusline"
SRC_SCRIPTS = HERE / "skills/custom-status-line/references/scripts"
INSTALLED = Path.home() / ".claude-status-line"
INSTALLED_STATUSLINE = INSTALLED / "statusline"
INSTALLED_SCRIPTS = INSTALLED / "scripts"


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
        print(f"FAIL: {SRC_STATUSLINE} not found (run from repo root)", file=sys.stderr)
        sys.exit(2)

    n_sl = copy_tree(SRC_STATUSLINE, INSTALLED_STATUSLINE)
    n_sc = copy_tree(SRC_SCRIPTS, INSTALLED_SCRIPTS)
    clear_pycache(INSTALLED)

    print(f"installed: {n_sl} statusline + {n_sc} scripts files")

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
