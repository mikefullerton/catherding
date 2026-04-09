"""Launch Claude Code for non-deterministic commands."""

import subprocess
import sys


def invoke_claude(site_manager_command: str) -> None:
    """Launch claude with a /site-manager command."""
    cmd = ["claude", "-p", f"/site-manager {site_manager_command}"]
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print("error: 'claude' not found on PATH", file=sys.stderr)
        print("Install Claude Code: https://claude.ai/code", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
