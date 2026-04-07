#!/usr/bin/env python3
"""Status line pipeline dispatcher.

Entry point for the Claude Code status line hook. Reads Claude JSON from stdin,
runs pipeline stages (built-in modules + external scripts), outputs plain text lines.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def load_pipeline_config(config_path: str) -> dict:
    """Load pipeline.json, creating defaults if missing."""
    path = Path(config_path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        default = {
            "pipeline": [
                {"name": "base-info", "module": "base_info"},
                {"name": "repo-cleanup", "module": "repo_cleanup"},
                {"name": "progress-display", "module": "progress_display"},
            ]
        }
        path.write_text(json.dumps(default, indent=2))
        return default
    return json.loads(path.read_text())


def run_external_script(script_path: str, state: dict) -> Optional[list]:
    """Run an external script with JSON on stdin, return lines or None on failure."""
    script_path = script_path.replace("~", os.path.expanduser("~"))
    if not os.path.isfile(script_path) or not os.access(script_path, os.X_OK):
        return None
    try:
        result = subprocess.run(
            [script_path],
            input=json.dumps(state),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None
        output = json.loads(result.stdout)
        lines = output.get("lines")
        if isinstance(lines, list):
            return lines
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None


def run_pipeline(
    claude_data: dict,
    pipeline: list,
    modules: dict,
) -> list:
    """Run the pipeline stages, return final lines."""
    lines = []
    for stage in pipeline:
        try:
            if "module" in stage:
                mod_name = stage["module"]
                if mod_name in modules:
                    lines = modules[mod_name](claude_data, lines)
            elif "script" in stage:
                state = {"claude": claude_data, "lines": lines}
                result = run_external_script(stage["script"], state)
                if result is not None:
                    lines = result
        except Exception:
            pass  # skip failed stages, preserve lines
    return lines


def main():
    """Entry point: read stdin, run pipeline, print lines."""
    claude_input = json.loads(sys.stdin.read())

    config_dir = os.path.expanduser("~/.claude-status-line")
    config_path = os.path.join(config_dir, "pipeline.json")
    config = load_pipeline_config(config_path)

    # Import built-in modules
    from statusline import base_info, repo_cleanup, progress_display
    modules = {
        "base_info": base_info.run,
        "repo_cleanup": repo_cleanup.run,
        "progress_display": progress_display.run,
    }

    lines = run_pipeline(claude_input, config["pipeline"], modules)
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
