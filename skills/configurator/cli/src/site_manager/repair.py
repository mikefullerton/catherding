"""Repair issues found by verify.

Reads .site/issues.json and delegates fixes to Claude.
In developer mode, walks through each issue interactively to triage
whether it's a tool bug or a deployment issue.
"""

import json
import sys
from pathlib import Path

from site_manager import ISSUES_PATH, DEVELOPER_FLAG
from site_manager.claude import invoke_claude


def _is_tool_developer() -> bool:
    return Path(DEVELOPER_FLAG).expanduser().exists()


def _triage_issues(issues: list[dict]) -> list[dict]:
    """Interactive triage in developer mode. Returns issues to repair."""
    to_repair = []

    print("Developer mode — triaging each issue:\n")
    print("  [r] repair    — fix this in the deployed project")
    print("  [t] tool bug  — skip, fix belongs in site-manager")
    print("  [s] skip      — ignore for now")
    print()

    for i, issue in enumerate(issues, 1):
        severity = issue["severity"].upper()
        print(f"  {i}/{len(issues)} [{severity}] {issue['check']}")
        if issue.get("detail"):
            print(f"         {issue['detail']}")

        while True:
            try:
                choice = input("         [r]epair / [t]ool bug / [s]kip: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                sys.exit(130)

            if choice in ("r", "repair"):
                to_repair.append(issue)
                print("         → will repair")
                break
            elif choice in ("t", "tool", "tool bug"):
                issue["_triaged"] = "tool_bug"
                print("         → tool bug (skipped)")
                break
            elif choice in ("s", "skip"):
                print("         → skipped")
                break
            else:
                print("         invalid choice, try r/t/s")

        print()

    return to_repair


def run_repair(output_json: bool = False) -> None:
    p = Path(ISSUES_PATH)
    if not p.exists():
        print("No issues file found. Run site-manager verify first.")
        sys.exit(0)

    data = json.loads(p.read_text())
    issues = data.get("issues", [])

    if not issues:
        print("No issues to repair. All checks passed.")
        sys.exit(0)

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    print(f"\n{len(issues)} issue(s) from last verify ({data.get('verified_at', '?')[:19]})")
    if errors:
        print(f"  {len(errors)} error(s)")
    if warnings:
        print(f"  {len(warnings)} warning(s)")
    print()

    if _is_tool_developer():
        issues_to_fix = _triage_issues(issues)

        if not issues_to_fix:
            print("No issues selected for repair.")
            sys.exit(0)

        print(f"Repairing {len(issues_to_fix)} issue(s)...\n")
    else:
        # Show the full list for non-developers
        for i, issue in enumerate(issues, 1):
            severity = issue["severity"].upper()
            print(f"  {i}. [{severity}] {issue['check']}")
            if issue.get("detail"):
                print(f"     {issue['detail']}")
        print()
        issues_to_fix = issues

    issue_summary = "\n".join(
        f"- [{i['severity']}] {i['suite']}: {i['check']} — {i['detail']}"
        for i in issues_to_fix if i.get("detail")
    )

    invoke_claude(f"repair\n\nIssues from .site/issues.json:\n{issue_summary}")
