"""Shared check result recording and display for all verification suites."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


@dataclass
class CheckResult:
    name: str
    passed: bool
    warning: bool = False
    skipped: bool = False
    detail: str = ""
    suite: str = ""


PROGRESS_SCRIPT = Path.home() / ".claude-status-line" / "progress" / "update-progress.sh"


class CheckRecorder:
    """Records check results with a running global counter and status line updates."""

    def __init__(self, total: int, title: str = "site-manager check"):
        self.total = total
        self.title = title
        self.results: list[CheckResult] = []

    @property
    def count(self) -> int:
        return len(self.results)

    def _update_progress(self, subtitle: str):
        """Update the Claude Code status line progress bar."""
        if PROGRESS_SCRIPT.exists():
            try:
                subprocess.run(
                    [str(PROGRESS_SCRIPT), self.title, subtitle,
                     str(self.count), str(self.total)],
                    capture_output=True, timeout=2,
                )
            except (subprocess.TimeoutExpired, OSError):
                pass

    def _clear_progress(self):
        """Clear the status line progress bar."""
        if PROGRESS_SCRIPT.exists():
            try:
                subprocess.run(
                    [str(PROGRESS_SCRIPT), "--clear"],
                    capture_output=True, timeout=2,
                )
            except (subprocess.TimeoutExpired, OSError):
                pass

    def record(self, name: str, passed: bool, *, warning: bool = False, detail: str = "", suite: str = ""):
        r = CheckResult(name=name, passed=passed, warning=warning, detail=detail, suite=suite)
        self.results.append(r)
        n = self.count
        self._update_progress(name)
        if warning and not passed:
            status, color = "WARN", YELLOW
        elif passed:
            status, color = "PASS", GREEN
        else:
            status, color = "FAIL", RED
        print(f"  {n:>3}/{self.total}  {color}{status}{RESET}  {name}")
        if detail and (not passed or warning):
            for line in detail.splitlines():
                print(f"              {line}")

    def skip(self, name: str, reason: str = "", suite: str = ""):
        r = CheckResult(name=name, passed=True, skipped=True, detail=reason, suite=suite)
        self.results.append(r)
        n = self.count
        self._update_progress(name)
        print(f"  {n:>3}/{self.total}  {YELLOW}SKIP{RESET}  {name}")
        if reason:
            print(f"              {reason}")

    def section(self, title: str):
        print(f"\n{BOLD}{title}{RESET}")

    def summary(self) -> bool:
        """Print summary. Returns True if all blocking checks passed."""
        self._clear_progress()
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed and not r.warning)
        warnings = sum(1 for r in self.results if not r.passed and r.warning)
        skipped = sum(1 for r in self.results if r.skipped)

        print(f"\n{BOLD}Results: {passed}/{len(self.results)} passed{RESET}", end="")
        if failed:
            print(f", {RED}{failed} failed{RESET}", end="")
        if warnings:
            print(f", {YELLOW}{warnings} warnings{RESET}", end="")
        if skipped:
            print(f", {skipped} skipped", end="")
        print()

        return failed == 0

    def to_json(self) -> str:
        return json.dumps({
            "results": [
                {"name": r.name, "passed": r.passed, "warning": r.warning,
                 "skipped": r.skipped, "detail": r.detail, "suite": r.suite}
                for r in self.results
            ],
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed and not r.warning),
            "warnings": sum(1 for r in self.results if not r.passed and r.warning),
        }, indent=2)
