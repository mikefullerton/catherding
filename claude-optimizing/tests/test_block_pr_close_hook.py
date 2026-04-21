"""Tests for the PreToolUse:Bash hook that blocks `gh pr close`.

Pure JSON-in / exit-code-out contract — no git or GitHub needed.
"""
import json
import subprocess
from pathlib import Path

HOOK_PATH = (
    Path(__file__).resolve().parent.parent / "scripts-hooks" / "cc-block-pr-close-hook.py"
)


def _invoke(tool_name="Bash", command=""):
    payload = json.dumps({"tool_name": tool_name, "tool_input": {"command": command}})
    r = subprocess.run(
        [str(HOOK_PATH)], input=payload,
        capture_output=True, text=True, timeout=10,
    )
    return r.stdout, r.stderr, r.returncode


def test_ignores_non_bash_tools():
    _, err, rc = _invoke(tool_name="Read", command="gh pr close 42")
    assert rc == 0
    assert not err.strip()


def test_ignores_unrelated_bash_commands():
    _, err, rc = _invoke(command="gh pr merge 42 --squash")
    assert rc == 0
    assert not err.strip()


def test_ignores_malformed_input():
    r = subprocess.run(
        [str(HOOK_PATH)], input="not json",
        capture_output=True, text=True, timeout=10,
    )
    assert r.returncode == 0


def test_blocks_gh_pr_close():
    _, err, rc = _invoke(command="gh pr close 42")
    assert rc == 2
    assert "gh pr close" in err
    assert "CC_ALLOW_PR_CLOSE=1" in err


def test_blocks_gh_pr_close_with_extra_flags():
    _, err, rc = _invoke(command="gh pr close 42 --comment 'oops'")
    assert rc == 2
    assert "gh pr close" in err


def test_escape_hatch_allows_close():
    _, err, rc = _invoke(command="CC_ALLOW_PR_CLOSE=1 gh pr close 42")
    assert rc == 0
    assert not err.strip()


def test_does_not_match_substring_gh_pr_closed():
    """Word boundary on `close` — commands mentioning `closed` shouldn't trigger."""
    _, err, rc = _invoke(command="echo 'pr was closed yesterday'")
    assert rc == 0
    assert not err.strip()
