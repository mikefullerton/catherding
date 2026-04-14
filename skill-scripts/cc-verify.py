#!/usr/bin/env python3
"""Run the repo's verification suite.

Usage: verify.py [--tests] [--lint] [--typecheck]

Without flags, runs everything that's available for this repo. Detects tools
by looking at config files: pytest.ini/pyproject.toml (pytest), ruff (ruff),
mypy (mypy). Exits non-zero on any failure.

Output is tight: one line per check ('pass' / 'fail: <details>').
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

def _find_repo_root() -> Path:
    """Locate the cat-herding repo — see install-statusline.py for rationale."""
    marker = Path(".claude-plugin/marketplace.json")
    p = Path.cwd().resolve()
    for candidate in (p, *p.parents):
        if (candidate / marker).is_file():
            return candidate
    return Path.home() / "projects/active/cat-herding"


HERE = _find_repo_root()
TESTS_DIR = HERE / "skills/custom-status-line/tests"
STATUSLINE_PKG = Path.home() / ".claude-status-line"


def run_pytest():
    if not TESTS_DIR.is_dir():
        return None, "no tests dir"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(STATUSLINE_PKG)
    result = subprocess.run(
        ["python3", "-m", "pytest", str(TESTS_DIR), "-q", "--tb=no"],
        env=env, capture_output=True, text=True,
    )
    last = (result.stdout.strip().splitlines() or [""])[-1]
    return result.returncode == 0, last


def run_ruff():
    # Check for ruff in pyproject or as an installed tool
    if not (HERE / "pyproject.toml").exists():
        return None, "no pyproject.toml"
    result = subprocess.run(
        ["ruff", "check", "."],
        cwd=HERE, capture_output=True, text=True,
    )
    if result.returncode == 127 or "command not found" in (result.stderr or ""):
        return None, "ruff not installed"
    msg = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "clean"
    return result.returncode == 0, msg


def run_mypy():
    if not (HERE / "mypy.ini").exists() and "mypy" not in (HERE / "pyproject.toml").read_text() if (HERE / "pyproject.toml").exists() else "":
        return None, "mypy not configured"
    result = subprocess.run(
        ["mypy", "."],
        cwd=HERE, capture_output=True, text=True,
    )
    if result.returncode == 127:
        return None, "mypy not installed"
    msg = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "clean"
    return result.returncode == 0, msg


def main():
    ap = argparse.ArgumentParser(description="Run verification checks.")
    ap.add_argument("--tests", action="store_true", help="Only tests")
    ap.add_argument("--lint", action="store_true", help="Only lint")
    ap.add_argument("--typecheck", action="store_true", help="Only typecheck")
    args = ap.parse_args()

    run_all = not (args.tests or args.lint or args.typecheck)

    checks = []
    if args.tests or run_all:
        checks.append(("tests", run_pytest))
    if args.lint or run_all:
        checks.append(("lint", run_ruff))
    if args.typecheck or run_all:
        checks.append(("typecheck", run_mypy))

    overall_ok = True
    for name, fn in checks:
        ok, msg = fn()
        if ok is None:
            print(f"{name:<10} skip ({msg})")
        elif ok:
            print(f"{name:<10} pass ({msg})")
        else:
            print(f"{name:<10} FAIL ({msg})")
            overall_ok = False

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
