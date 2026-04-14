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
    """Run the pipeline stages, return final lines.

    Maintains a shared `rows` list of Row objects that columnar modules
    append to. After all stages run, rows are formatted in one pass and
    inserted into the output.
    """
    lines = []
    rows = []  # shared Row list — columnar modules append here

    for stage in pipeline:
        try:
            if "module" in stage:
                mod_name = stage["module"]
                if mod_name in modules:
                    func = modules[mod_name]
                    import inspect
                    params = inspect.signature(func).parameters
                    if "rows" in params:
                        lines = func(claude_data, lines, rows)
                    else:
                        lines = func(claude_data, lines)
            elif "script" in stage:
                state = {"claude": claude_data, "lines": lines}
                result = run_external_script(stage["script"], state)
                if result is not None:
                    lines = result
        except Exception as e:
            import traceback
            log_path = os.path.expanduser("~/.claude-status-line/dispatcher.log")
            with open(log_path, "a") as f:
                f.write(f"[{__import__('datetime').datetime.now().isoformat()}] Stage '{stage.get('name', '?')}' failed: {e}\n")
                f.write(f"  {traceback.format_exc()}\n")

    # Single formatting pass for all columnar rows
    if rows:
        from statusline.formatting import compute_column_widths, format_rows
        widths = compute_column_widths(rows)
        format_rows(rows, widths)
        for row in rows:
            lines.append(row.render())

    return lines


def main():
    """Entry point: read stdin, run pipeline, print lines."""
    log_path = os.path.expanduser("~/.claude-status-line/dispatcher.log")

    try:
        raw = sys.stdin.read()
        claude_input = json.loads(raw)
    except Exception as e:
        with open(log_path, "a") as f:
            f.write(f"[{__import__('datetime').datetime.now().isoformat()}] JSON parse error: {e}\n")
            f.write(f"  stdin length: {len(raw) if 'raw' in dir() else 'unread'}\n")
            f.write(f"  stdin preview: {repr(raw[:200]) if 'raw' in dir() else 'N/A'}\n")
        return

    try:
        config_dir = os.path.expanduser("~/.claude-status-line")
        config_path = os.path.join(config_dir, "pipeline.json")
        config = load_pipeline_config(config_path)

        # Import built-in modules
        from statusline import base_info, repo_cleanup, progress_display, version_tracker, usage_costs, graphify_savings, version_check
        modules = {
            "base_info": base_info.run,
            "repo_cleanup": repo_cleanup.run,
            "progress_display": progress_display.run,
            "version_tracker": version_tracker.run,
            "usage_costs": usage_costs.run,
            "graphify_savings": graphify_savings.run,
            "version_check": version_check.run,
        }

        lines = run_pipeline(claude_input, config["pipeline"], modules)
        for line in lines:
            print(line)
    except Exception as e:
        import traceback
        with open(log_path, "a") as f:
            f.write(f"[{__import__('datetime').datetime.now().isoformat()}] Pipeline error: {e}\n")
            f.write(f"  traceback: {traceback.format_exc()}\n")
            f.write(f"  input keys: {list(claude_input.keys()) if isinstance(claude_input, dict) else type(claude_input)}\n")


if __name__ == "__main__":
    main()
