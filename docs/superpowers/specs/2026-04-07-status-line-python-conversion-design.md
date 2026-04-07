# Status Line Python Conversion

Convert all 6 custom-status-line bash scripts to a single Python package with shared utilities.

## Motivation

The bash scripts use x10/x100 fixed-point integer arithmetic for decimal display, build SQL strings with sed escaping, and duplicate color/alignment helpers across files. Python gives real floats, parameterized SQL, and natural code sharing.

## Architecture

One Python package replaces all bash scripts:

```
references/
  statusline/
    __init__.py           # package marker
    dispatcher.py         # entry point, replaces dispatcher.sh
    base_info.py          # git info, model stats, usage projection, SQLite logging
    repo_cleanup.py       # stale branch/worktree warnings
    progress_display.py   # boxed progress bar
    update_progress.py    # standalone CLI: write progress file + trigger refresh
    ensure_permissions.py # standalone CLI: merge Bash() patterns into settings.json
    formatting.py         # shared: ANSI colors, visible_len, pad_right/left, column alignment
    db.py                 # shared: SQLite schema migration + parameterized insert helpers
```

### Built-in vs external pipeline scripts

The dispatcher imports `base_info`, `repo_cleanup`, and `progress_display` as Python functions — no subprocess overhead for built-ins. Third-party drop-in scripts in `pipeline.json` are still called via `subprocess.run()` and can be any language (sh, python, etc.).

### pipeline.json format

Built-in entries use `"module"` key, external scripts use `"script"` key:

```json
{
  "pipeline": [
    {"name": "base-info", "module": "base_info"},
    {"name": "repo-cleanup", "module": "repo_cleanup"},
    {"name": "my-custom-thing", "script": "~/.claude-status-line/scripts/my-thing.sh"}
  ]
}
```

The dispatcher resolves `"module"` entries by importing from the `statusline` package. `"script"` entries are executed as subprocesses with JSON on stdin, same as today.

## Shared modules

### formatting.py

- ANSI color constants: BLUE, YELLOW, GREEN, ORANGE, RED, DIM, RST
- `visible_len(s)` — strip ANSI codes, return character count
- `pad_right(s, width)` / `pad_left(s, width)` — pad to visible width
- `format_columns(rows, sep)` — auto-width column alignment across multiple lines

### db.py

- `get_db(path)` — open SQLite connection, run schema migrations via `PRAGMA user_version`
- `upsert_session(db, **kwargs)` — parameterized session upsert
- `append_weekly_usage(db, **kwargs)` — append-only insert with dedup check
- Schema stays identical to current v3; migration logic preserved

## Module details

### dispatcher.py

Entry point called by the status line hook. Reads Claude JSON from stdin, seeds pipeline state, runs each pipeline stage:

1. For `"module"` entries: import and call the module's `run(claude_data, lines)` function directly
2. For `"script"` entries: `subprocess.run()` with JSON on stdin, parse JSON output
3. On any exception or invalid output: skip that stage, pass lines through unchanged
4. Final output: print each line to stdout

Auto-creates default `pipeline.json` if missing, same as today.

### base_info.py

`run(claude_data: dict, lines: list[str]) -> list[str]`

Generates 3 status lines:
- **Line 1**: project path, session name, git branch, dirty files, commits ahead/behind
- **Line 2**: model name, effort level, YOLO indicator, duration, lines changed, context usage
- **Line 3**: weekly usage, elapsed day, daily average, 5h rate, projected 7-day, overage warning

Usage projection uses real float arithmetic:
```python
rate_7d = claude_data["rate_limits"]["seven_day"]["used_percentage"]
elapsed_hours = max(1, int((now - last_wed_10am).total_seconds() / 3600))
daily_avg = rate_7d * 24 / elapsed_hours
projected = rate_7d * 168 / elapsed_hours
```

SQLite logging via `db.py` with parameterized queries (no string interpolation).

Git commands via `subprocess.run(["git", ...], capture_output=True)`.

### repo_cleanup.py

`run(claude_data: dict, lines: list[str]) -> list[str]`

Detects and appends warnings to line 1:
- Stale branches (remote tracking deleted)
- Merged branches (safe to delete)
- Prunable worktrees
- Remote-only branches
- Finished worktrees (branch merged, worktree still exists)

### progress_display.py

`run(claude_data: dict, lines: list[str]) -> list[str]`

Reads `~/.claude-status-line/progress/<session_id>.json`, renders a centered box with title, progress bar, and subtitle. Appends 6 lines after existing lines. Passes through unchanged if no progress file exists.

### update_progress.py

Standalone CLI, called from CLAUDE.md and other scripts:

```
python3 -m statusline.update_progress "Title" "Step" 3 10
python3 -m statusline.update_progress --clear
```

Session discovery: walks process tree via `os.getppid()` / `psutil`-free approach using `ps -o ppid=`.

A thin shell wrapper at `~/.claude-status-line/progress/update-progress.sh` preserves backward compatibility:
```bash
#!/bin/bash
exec python3 -m statusline.update_progress "$@"
```

### ensure_permissions.py

Standalone CLI for install time:

```
python3 -m statusline.ensure_permissions /path/to/SKILL.md
```

Reads `allowed-tools` from SKILL.md frontmatter, merges `Bash()` patterns into `~/.claude/settings.json`.

## Installation

The SKILL.md install flow:

1. Copy `references/statusline/` to `~/.claude-status-line/statusline/`
2. Symlink dispatcher: `~/.claude-status-line/scripts/dispatcher.py` -> package
3. Update hook in `settings.json`: `python3 ~/.claude-status-line/scripts/dispatcher.py`
4. Migrate `pipeline.json`: rewrite built-in `"script"` entries to `"module"` format, preserve user-added external entries
5. Write shell wrapper for `update-progress.sh`
6. Remove old `.sh` files from `~/.claude-status-line/scripts/`

## Testing & validation

### Unit tests

Each module gets tested by calling its `run()` function with mock JSON input:

- **base_info**: mock Claude JSON with known values, verify 3 output lines contain expected text (model name, duration format, usage percentages). Test float math edge cases: day 7 at 100% must project to 100.0%, not 98%. Test overage calculation above 100%.
- **repo_cleanup**: mock git subprocess output, verify warning text appended to line 1. Test with zero issues (passthrough).
- **progress_display**: mock progress JSON file, verify 6-line box output with correct bar fill. Test missing/empty progress file (passthrough).
- **formatting**: test `visible_len` with ANSI-colored strings, verify `pad_right`/`pad_left` produce correct visible widths.
- **db**: test schema migration with in-memory SQLite (`":memory:"`). Test upsert idempotency, append-only dedup.

### Integration test

A single end-to-end test that pipes realistic Claude JSON through `dispatcher.py` (with built-in modules only, no external scripts) and verifies:
- Output is 3+ lines of plain text
- Lines contain expected column structure
- No JSON leaks through to stdout
- Exit code 0

### Validation during development

After each module is converted:
1. Run its unit tests
2. Run the integration test
3. Manually test in a live Claude session by installing the Python version and comparing output to the bash version

### Test location

Tests live at `plugins/custom-status-line/tests/` using pytest:

```
tests/
  conftest.py             # shared fixtures (mock Claude JSON, temp dirs)
  test_base_info.py
  test_repo_cleanup.py
  test_progress_display.py
  test_formatting.py
  test_db.py
  test_dispatcher.py      # integration test
```

## Dependencies

- Python 3.9+ (macOS default)
- stdlib only: json, sqlite3, subprocess, re, os, datetime, pathlib, shutil, sys
- No external packages required
- jq no longer needed for built-in scripts (still needed only if user has external drop-in scripts that use it)

## Performance

Python startup is ~30-50ms. With built-ins running as function calls in a single process (no subprocess per stage), total should be well under the 200ms target. Optimize later if needed.
