# Status Line Python Conversion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert all 6 custom-status-line bash scripts to a Python package with shared utilities, real float math, and parameterized SQL.

**Architecture:** One Python package (`statusline/`) under `references/` replaces all bash scripts. The dispatcher imports built-in modules as functions (no subprocess overhead) and shells out for third-party drop-in scripts. Shared `formatting.py` and `db.py` modules eliminate duplication.

**Tech Stack:** Python 3.9+ stdlib only (json, sqlite3, subprocess, re, os, datetime, pathlib, shutil, sys). pytest for testing.

**Spec:** `docs/superpowers/specs/2026-04-07-status-line-python-conversion-design.md`

---

## File Structure

```
plugins/custom-status-line/
  skills/custom-status-line/references/
    statusline/
      __init__.py           # package marker
      formatting.py         # ANSI colors, visible_len, pad_right/left, column alignment
      db.py                 # SQLite schema migration + parameterized helpers
      dispatcher.py         # entry point, pipeline orchestration
      base_info.py          # git info, model stats, usage projection, SQLite logging
      repo_cleanup.py       # stale branch/worktree warnings
      progress_display.py   # boxed progress bar
      update_progress.py    # standalone CLI: write progress file
      ensure_permissions.py # standalone CLI: merge permissions into settings.json
  tests/
    conftest.py             # shared fixtures
    test_formatting.py
    test_db.py
    test_dispatcher.py
    test_base_info.py
    test_repo_cleanup.py
    test_progress_display.py
    test_update_progress.py
    test_ensure_permissions.py
```

**Existing files to update after conversion:**
- `plugins/custom-status-line/skills/custom-status-line/SKILL.md` — update install/uninstall flow for Python
- `plugins/custom-status-line/how-to-add-status-line-scripts.md` — update examples to mention Python dispatcher
- `plugins/custom-status-line/README.md` — update references

**Existing files removed after conversion:**
- `plugins/custom-status-line/skills/custom-status-line/references/dispatcher.sh`
- `plugins/custom-status-line/skills/custom-status-line/references/base-info.sh`
- `plugins/custom-status-line/skills/custom-status-line/references/repo-cleanup.sh`
- `plugins/custom-status-line/skills/custom-status-line/references/progress-display.sh`
- `plugins/custom-status-line/skills/custom-status-line/references/update-progress.sh`
- `plugins/custom-status-line/skills/custom-status-line/references/ensure-permissions.sh`

---

### Task 1: Create package scaffold and formatting.py

**Files:**
- Create: `plugins/custom-status-line/skills/custom-status-line/references/statusline/__init__.py`
- Create: `plugins/custom-status-line/skills/custom-status-line/references/statusline/formatting.py`
- Create: `plugins/custom-status-line/tests/conftest.py`
- Create: `plugins/custom-status-line/tests/test_formatting.py`

- [ ] **Step 1: Write the failing tests for formatting**

```python
# tests/test_formatting.py
import pytest
from statusline.formatting import (
    BLUE, YELLOW, GREEN, ORANGE, RED, DIM, RST,
    visible_len, pad_right, pad_left,
)


class TestVisibleLen:
    def test_plain_text(self):
        assert visible_len("hello") == 5

    def test_ansi_colored(self):
        assert visible_len(f"{BLUE}hello{RST}") == 5

    def test_multiple_colors(self):
        s = f"{RED}err{RST} {GREEN}ok{RST}"
        assert visible_len(s) == 6  # "err ok"

    def test_empty(self):
        assert visible_len("") == 0

    def test_only_ansi(self):
        assert visible_len(f"{BLUE}{RST}") == 0


class TestPadRight:
    def test_pads_plain(self):
        result = pad_right("hi", 5)
        assert result == "hi   "
        assert visible_len(result) == 5

    def test_pads_ansi(self):
        result = pad_right(f"{RED}hi{RST}", 5)
        assert visible_len(result) == 5
        assert result.startswith("\033[")  # still has color

    def test_no_pad_when_exact(self):
        result = pad_right("hello", 5)
        assert result == "hello"

    def test_no_pad_when_over(self):
        result = pad_right("hello!", 5)
        assert result == "hello!"


class TestPadLeft:
    def test_pads_plain(self):
        result = pad_left("hi", 5)
        assert result == "   hi"
        assert visible_len(result) == 5

    def test_pads_ansi(self):
        result = pad_left(f"{RED}hi{RST}", 5)
        assert visible_len(result) == 5

    def test_no_pad_when_exact(self):
        result = pad_left("hello", 5)
        assert result == "hello"
```

- [ ] **Step 2: Create conftest.py with sys.path setup**

```python
# tests/conftest.py
import sys
from pathlib import Path

# Add the references directory to sys.path so `import statusline` works
REFERENCES_DIR = Path(__file__).resolve().parent.parent / "skills" / "custom-status-line" / "references"
sys.path.insert(0, str(REFERENCES_DIR))
```

- [ ] **Step 3: Create __init__.py**

```python
# statusline/__init__.py
"""Custom status line pipeline for Claude Code."""
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_formatting.py -v`
Expected: ImportError — `statusline.formatting` does not exist yet.

- [ ] **Step 5: Implement formatting.py**

```python
# statusline/formatting.py
"""ANSI colors and column alignment helpers."""
import re

# ANSI color constants
BLUE = "\033[38;5;117m"
YELLOW = "\033[38;5;229m"
GREEN = "\033[38;5;151m"
ORANGE = "\033[38;5;214m"
RED = "\033[38;5;210m"
DIM = "\033[38;5;245m"
RST = "\033[0m"

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def visible_len(s: str) -> int:
    """Return the visible length of a string, ignoring ANSI escape codes."""
    return len(_ANSI_RE.sub("", s))


def pad_right(s: str, width: int) -> str:
    """Pad string to visible width with trailing spaces."""
    pad = width - visible_len(s)
    return s + " " * pad if pad > 0 else s


def pad_left(s: str, width: int) -> str:
    """Pad string to visible width with leading spaces."""
    pad = width - visible_len(s)
    return " " * pad + s if pad > 0 else s
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_formatting.py -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add plugins/custom-status-line/skills/custom-status-line/references/statusline/__init__.py \
       plugins/custom-status-line/skills/custom-status-line/references/statusline/formatting.py \
       plugins/custom-status-line/tests/conftest.py \
       plugins/custom-status-line/tests/test_formatting.py
git commit -m "feat(status-line): add Python package scaffold and formatting module"
git push
```

---

### Task 2: Create db.py (SQLite schema + helpers)

**Files:**
- Create: `plugins/custom-status-line/skills/custom-status-line/references/statusline/db.py`
- Create: `plugins/custom-status-line/tests/test_db.py`

- [ ] **Step 1: Write failing tests for db module**

```python
# tests/test_db.py
import sqlite3
import pytest
from statusline.db import get_db, upsert_session, append_weekly_usage

DB_VERSION = 3


class TestGetDb:
    def test_creates_tables(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = get_db(str(db_path))
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor]
        assert "sessions" in tables
        assert "weekly_usage" in tables
        db.close()

    def test_sets_user_version(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = get_db(str(db_path))
        version = db.execute("PRAGMA user_version").fetchone()[0]
        assert version == DB_VERSION
        db.close()

    def test_migration_is_idempotent(self, tmp_path):
        db_path = tmp_path / "test.db"
        db1 = get_db(str(db_path))
        db1.close()
        db2 = get_db(str(db_path))
        version = db2.execute("PRAGMA user_version").fetchone()[0]
        assert version == DB_VERSION
        db2.close()


class TestUpsertSession:
    def test_insert_new_session(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        upsert_session(db,
            session_id="sess-1", session_name="test", model_id="opus-4",
            model_display="Opus 4", claude_version="1.0", cwd="/tmp",
            project_dir="/tmp", transcript_path="/tmp/t.json",
            context_window_size=200000, duration_s=60, api_duration_ms=5000,
            lines_added=10, lines_removed=5, total_cost_usd="0.50",
            total_input_tokens=1000, total_output_tokens=500,
            cache_create_tokens=100, cache_read_tokens=200,
            context_used_pct=15)
        row = db.execute("SELECT session_id, model_id FROM sessions").fetchone()
        assert row[0] == "sess-1"
        assert row[1] == "opus-4"
        db.close()

    def test_upsert_updates_existing(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        kwargs = dict(
            session_id="sess-1", session_name="test", model_id="opus-4",
            model_display="Opus 4", claude_version="1.0", cwd="/tmp",
            project_dir="/tmp", transcript_path="/tmp/t.json",
            context_window_size=200000, duration_s=60, api_duration_ms=5000,
            lines_added=10, lines_removed=5, total_cost_usd="0.50",
            total_input_tokens=1000, total_output_tokens=500,
            cache_create_tokens=100, cache_read_tokens=200,
            context_used_pct=15)
        upsert_session(db, **kwargs)
        upsert_session(db, **{**kwargs, "duration_s": 120, "lines_added": 20})
        row = db.execute("SELECT duration_s, lines_added FROM sessions").fetchone()
        assert row[0] == 120
        assert row[1] == 20
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1
        db.close()


class TestAppendWeeklyUsage:
    def test_appends_new_row(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        append_weekly_usage(db,
            session_id="sess-1", week_start="2026-04-02",
            elapsed_hours=48, elapsed_day=2.0,
            weekly_pct=28.5, daily_avg_pct=14.3,
            five_hour_pct=5.0, five_hour_resets_at=0,
            seven_day_resets_at=0, projected_pct=100.0)
        count = db.execute("SELECT count(*) FROM weekly_usage").fetchone()[0]
        assert count == 1
        db.close()

    def test_dedup_skips_unchanged(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        kwargs = dict(
            session_id="sess-1", week_start="2026-04-02",
            elapsed_hours=48, elapsed_day=2.0,
            weekly_pct=28.5, daily_avg_pct=14.3,
            five_hour_pct=5.0, five_hour_resets_at=0,
            seven_day_resets_at=0, projected_pct=100.0)
        append_weekly_usage(db, **kwargs)
        append_weekly_usage(db, **kwargs)  # same values
        count = db.execute("SELECT count(*) FROM weekly_usage").fetchone()[0]
        assert count == 1  # dedup
        db.close()

    def test_appends_when_values_change(self, tmp_path):
        db = get_db(str(tmp_path / "test.db"))
        kwargs = dict(
            session_id="sess-1", week_start="2026-04-02",
            elapsed_hours=48, elapsed_day=2.0,
            weekly_pct=28.5, daily_avg_pct=14.3,
            five_hour_pct=5.0, five_hour_resets_at=0,
            seven_day_resets_at=0, projected_pct=100.0)
        append_weekly_usage(db, **kwargs)
        append_weekly_usage(db, **{**kwargs, "weekly_pct": 30.0})
        count = db.execute("SELECT count(*) FROM weekly_usage").fetchone()[0]
        assert count == 2
        db.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_db.py -v`
Expected: ImportError — `statusline.db` does not exist yet.

- [ ] **Step 3: Implement db.py**

```python
# statusline/db.py
"""SQLite schema migration and parameterized query helpers."""
import sqlite3
from datetime import datetime

DB_VERSION = 3


def get_db(path: str) -> sqlite3.Connection:
    """Open database, run migrations if needed, return connection."""
    db = sqlite3.connect(path)
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version < DB_VERSION:
        db.executescript("""
            DROP TABLE IF EXISTS sessions;
            DROP TABLE IF EXISTS weekly_usage;
            DROP TABLE IF EXISTS usage;
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                session_name TEXT,
                model_id TEXT NOT NULL,
                model_display TEXT NOT NULL,
                claude_version TEXT,
                cwd TEXT,
                project_dir TEXT,
                transcript_path TEXT,
                context_window_size INTEGER NOT NULL DEFAULT 0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                duration_s INTEGER NOT NULL,
                api_duration_ms INTEGER NOT NULL DEFAULT 0,
                lines_added INTEGER NOT NULL,
                lines_removed INTEGER NOT NULL,
                total_cost_usd TEXT NOT NULL,
                total_input_tokens INTEGER NOT NULL DEFAULT 0,
                total_output_tokens INTEGER NOT NULL DEFAULT 0,
                cache_create_tokens INTEGER NOT NULL DEFAULT 0,
                cache_read_tokens INTEGER NOT NULL DEFAULT 0,
                context_used_pct INTEGER NOT NULL
            );
            CREATE TABLE weekly_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                week_start TEXT NOT NULL,
                elapsed_hours INTEGER NOT NULL,
                day REAL NOT NULL,
                weekly_pct REAL NOT NULL,
                daily_avg_pct REAL NOT NULL,
                five_hour_pct REAL NOT NULL,
                five_hour_resets_at INTEGER,
                seven_day_resets_at INTEGER,
                projected_pct REAL NOT NULL
            );
        """)
        db.execute(f"PRAGMA user_version={DB_VERSION}")
        db.commit()
    return db


def upsert_session(db: sqlite3.Connection, **kw) -> None:
    """Insert or update a session record."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute("""
        INSERT INTO sessions (
            session_id, session_name, model_id, model_display, claude_version,
            cwd, project_dir, transcript_path, context_window_size,
            first_seen, last_seen, duration_s, api_duration_ms,
            lines_added, lines_removed, total_cost_usd,
            total_input_tokens, total_output_tokens,
            cache_create_tokens, cache_read_tokens, context_used_pct)
        VALUES (
            :session_id, :session_name, :model_id, :model_display, :claude_version,
            :cwd, :project_dir, :transcript_path, :context_window_size,
            :now, :now, :duration_s, :api_duration_ms,
            :lines_added, :lines_removed, :total_cost_usd,
            :total_input_tokens, :total_output_tokens,
            :cache_create_tokens, :cache_read_tokens, :context_used_pct)
        ON CONFLICT(session_id) DO UPDATE SET
            session_name=:session_name, last_seen=:now,
            duration_s=:duration_s, api_duration_ms=:api_duration_ms,
            lines_added=:lines_added, lines_removed=:lines_removed,
            total_cost_usd=:total_cost_usd,
            total_input_tokens=:total_input_tokens,
            total_output_tokens=:total_output_tokens,
            cache_create_tokens=:cache_create_tokens,
            cache_read_tokens=:cache_read_tokens,
            context_used_pct=:context_used_pct
    """, {**kw, "now": now})
    db.commit()


def append_weekly_usage(db: sqlite3.Connection, **kw) -> None:
    """Append a weekly usage row, skipping if values unchanged from last row."""
    last = db.execute("""
        SELECT weekly_pct, five_hour_pct, projected_pct
        FROM weekly_usage WHERE session_id=:session_id
        ORDER BY id DESC LIMIT 1
    """, {"session_id": kw["session_id"]}).fetchone()

    if last and (last[0] == kw["weekly_pct"] and last[1] == kw["five_hour_pct"]
                 and last[2] == kw["projected_pct"]):
        return  # no change

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.execute("""
        INSERT INTO weekly_usage (
            timestamp, session_id, week_start, elapsed_hours, day,
            weekly_pct, daily_avg_pct, five_hour_pct,
            five_hour_resets_at, seven_day_resets_at, projected_pct)
        VALUES (
            :now, :session_id, :week_start, :elapsed_hours, :elapsed_day,
            :weekly_pct, :daily_avg_pct, :five_hour_pct,
            :five_hour_resets_at, :seven_day_resets_at, :projected_pct)
    """, {**kw, "now": now})
    db.commit()
```

Note: The schema now stores `REAL` for percentage and day columns instead of the bash x10 integer hack. The `day` column is renamed from integer to `REAL` to store fractional days directly. This is a schema version bump but we keep `DB_VERSION = 3` since it drops and recreates anyway.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_db.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/custom-status-line/skills/custom-status-line/references/statusline/db.py \
       plugins/custom-status-line/tests/test_db.py
git commit -m "feat(status-line): add db module with SQLite schema and parameterized helpers"
git push
```

---

### Task 3: Create dispatcher.py

**Files:**
- Create: `plugins/custom-status-line/skills/custom-status-line/references/statusline/dispatcher.py`
- Create: `plugins/custom-status-line/tests/test_dispatcher.py`

- [ ] **Step 1: Write failing tests for dispatcher**

```python
# tests/test_dispatcher.py
import json
import os
import stat
import pytest
from statusline.dispatcher import run_pipeline, load_pipeline_config, run_external_script

MOCK_CLAUDE = {
    "model": {"display_name": "Test Model", "id": "test-model"},
    "context_window": {"remaining_percentage": 85, "context_window_size": 200000,
                       "total_input_tokens": 1000, "total_output_tokens": 500,
                       "current_usage": {"cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}},
    "cost": {"total_duration_ms": 60000, "total_api_duration_ms": 5000,
             "total_lines_added": 10, "total_lines_removed": 5, "total_cost_usd": 0.50},
    "cwd": "/tmp/test",
    "session_id": "test-session-123",
    "session_name": "",
    "rate_limits": {
        "five_hour": {"used_percentage": 5.0, "resets_at": 0},
        "seven_day": {"used_percentage": 28.5, "resets_at": 0},
    },
    "version": "1.0",
    "workspace": {"project_dir": "/tmp/test"},
    "transcript_path": "",
}


class TestLoadPipelineConfig:
    def test_creates_default_if_missing(self, tmp_path):
        config_path = tmp_path / "pipeline.json"
        config = load_pipeline_config(str(config_path))
        assert len(config["pipeline"]) >= 2
        assert config_path.exists()

    def test_reads_existing(self, tmp_path):
        config_path = tmp_path / "pipeline.json"
        config_path.write_text(json.dumps({
            "pipeline": [{"name": "test", "module": "base_info"}]
        }))
        config = load_pipeline_config(str(config_path))
        assert len(config["pipeline"]) == 1
        assert config["pipeline"][0]["name"] == "test"


class TestRunExternalScript:
    def test_runs_script_and_parses_output(self, tmp_path):
        script = tmp_path / "test.sh"
        script.write_text('#!/bin/bash\necho \'{"lines": ["hello"]}\'\n')
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        result = run_external_script(str(script), {"claude": {}, "lines": []})
        assert result == ["hello"]

    def test_returns_none_on_bad_script(self, tmp_path):
        script = tmp_path / "bad.sh"
        script.write_text("#!/bin/bash\nexit 1\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        result = run_external_script(str(script), {"claude": {}, "lines": []})
        assert result is None

    def test_returns_none_on_invalid_json(self, tmp_path):
        script = tmp_path / "bad.sh"
        script.write_text("#!/bin/bash\necho 'not json'\n")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        result = run_external_script(str(script), {"claude": {}, "lines": []})
        assert result is None


class TestRunPipeline:
    def test_module_entry_calls_function(self):
        def mock_run(claude_data, lines):
            return lines + ["added by mock"]

        modules = {"mock_mod": mock_run}
        pipeline = [{"name": "mock", "module": "mock_mod"}]
        result = run_pipeline(MOCK_CLAUDE, pipeline, modules)
        assert "added by mock" in result

    def test_skips_missing_module(self):
        pipeline = [{"name": "missing", "module": "nonexistent"}]
        result = run_pipeline(MOCK_CLAUDE, pipeline, {})
        assert result == []  # empty lines, nothing crashed

    def test_script_entry_runs_external(self, tmp_path):
        script = tmp_path / "ext.sh"
        script.write_text('#!/bin/bash\necho \'{"lines": ["from script"]}\'\n')
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        pipeline = [{"name": "ext", "script": str(script)}]
        result = run_pipeline(MOCK_CLAUDE, pipeline, {})
        assert result == ["from script"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_dispatcher.py -v`
Expected: ImportError — `statusline.dispatcher` does not exist yet.

- [ ] **Step 3: Implement dispatcher.py**

```python
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


def run_external_script(script_path: str, state: dict) -> list[str] | None:
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
    pipeline: list[dict],
    modules: dict[str, callable],
) -> list[str]:
    """Run the pipeline stages, return final lines."""
    lines: list[str] = []
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_dispatcher.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/custom-status-line/skills/custom-status-line/references/statusline/dispatcher.py \
       plugins/custom-status-line/tests/test_dispatcher.py
git commit -m "feat(status-line): add Python dispatcher with module + script pipeline support"
git push
```

---

### Task 4: Create base_info.py

This is the largest module. It generates 3 status lines with git info, model stats, and usage projection.

**Files:**
- Create: `plugins/custom-status-line/skills/custom-status-line/references/statusline/base_info.py`
- Create: `plugins/custom-status-line/tests/test_base_info.py`

- [ ] **Step 1: Write failing tests for base_info**

```python
# tests/test_base_info.py
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from statusline.formatting import BLUE, YELLOW, RED, RST, visible_len


def make_claude_data(**overrides):
    """Build a mock claude_data dict with sensible defaults."""
    base = {
        "model": {"display_name": "Claude Opus 4 (1M context)", "id": "claude-opus-4"},
        "context_window": {
            "remaining_percentage": 96,
            "context_window_size": 1000000,
            "total_input_tokens": 40000,
            "total_output_tokens": 5000,
            "current_usage": {
                "cache_creation_input_tokens": 1000,
                "cache_read_input_tokens": 2000,
            },
        },
        "cost": {
            "total_duration_ms": 3661000,  # 1h:01m
            "total_api_duration_ms": 300000,
            "total_lines_added": 150,
            "total_lines_removed": 30,
            "total_cost_usd": 1.25,
        },
        "cwd": "/Users/test/projects/myapp",
        "session_id": "test-session-abc",
        "session_name": "",
        "rate_limits": {
            "five_hour": {"used_percentage": 5.2, "resets_at": 0},
            "seven_day": {"used_percentage": 100.0, "resets_at": 0},
        },
        "version": "1.0.0",
        "workspace": {"project_dir": "/Users/test/projects/myapp"},
        "transcript_path": "/tmp/transcript.json",
    }
    for key, val in overrides.items():
        if isinstance(val, dict) and key in base and isinstance(base[key], dict):
            base[key] = {**base[key], **val}
        else:
            base[key] = val
    return base


class TestDurationFormat:
    """Test duration formatting logic extracted from base_info."""

    def test_format_duration_hours(self):
        from statusline.base_info import format_duration
        assert format_duration(3661000) == "1h:01m"

    def test_format_duration_minutes(self):
        from statusline.base_info import format_duration
        assert format_duration(125000) == "0h:02m"

    def test_format_duration_seconds(self):
        from statusline.base_info import format_duration
        assert format_duration(45000) == "45s"


class TestUsageProjection:
    """Test the weekly usage projection math."""

    def test_day7_100pct_projects_to_100(self):
        from statusline.base_info import compute_projection
        result = compute_projection(rate_7d=100.0, elapsed_hours=168)
        assert abs(result["projected"] - 100.0) < 0.1

    def test_day1_14pct_projects_to_98_ish(self):
        from statusline.base_info import compute_projection
        result = compute_projection(rate_7d=14.0, elapsed_hours=24)
        assert abs(result["projected"] - 98.0) < 1.0

    def test_overage_detected(self):
        from statusline.base_info import compute_projection
        result = compute_projection(rate_7d=50.0, elapsed_hours=24)
        # 50% in 24h => projected 350%
        assert result["projected"] > 100.0
        assert result["overage_dollars"] > 0

    def test_zero_usage(self):
        from statusline.base_info import compute_projection
        result = compute_projection(rate_7d=0.0, elapsed_hours=48)
        assert result["projected"] == 0.0
        assert result["daily_avg"] == 0.0

    def test_elapsed_hours_clamped_to_1(self):
        from statusline.base_info import compute_projection
        result = compute_projection(rate_7d=10.0, elapsed_hours=0)
        assert result["elapsed_hours"] == 1  # clamped


class TestRunOutputStructure:
    """Test that run() returns 3 lines with expected content."""

    @patch("statusline.base_info.git_cmd")
    @patch("statusline.base_info.log_to_db")
    def test_returns_three_lines(self, mock_log, mock_git):
        mock_git.return_value = ""
        from statusline.base_info import run
        data = make_claude_data()
        lines = run(data, [])
        assert len(lines) == 3

    @patch("statusline.base_info.git_cmd")
    @patch("statusline.base_info.log_to_db")
    def test_line1_contains_project_path(self, mock_log, mock_git):
        mock_git.return_value = ""
        from statusline.base_info import run
        data = make_claude_data(cwd="/Users/test/projects/myapp")
        lines = run(data, [])
        assert "myapp" in lines[0] or "projects" in lines[0]

    @patch("statusline.base_info.git_cmd")
    @patch("statusline.base_info.log_to_db")
    def test_line2_contains_model_name(self, mock_log, mock_git):
        mock_git.return_value = ""
        from statusline.base_info import run
        data = make_claude_data()
        lines = run(data, [])
        # Strip ANSI to check content
        plain = visible_len  # just need to check substring
        assert "Opus" in lines[1] or "opus" in lines[1].lower()

    @patch("statusline.base_info.git_cmd")
    @patch("statusline.base_info.log_to_db")
    def test_line3_contains_weekly_usage(self, mock_log, mock_git):
        mock_git.return_value = ""
        from statusline.base_info import run
        data = make_claude_data()
        lines = run(data, [])
        assert "Weekly usage" in lines[2] or "weekly" in lines[2].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_base_info.py -v`
Expected: ImportError — `statusline.base_info` does not exist yet.

- [ ] **Step 3: Implement base_info.py**

This is a direct port of `base-info.sh` with the following improvements:
- Real floats for all percentage math
- `format_duration()` and `compute_projection()` as testable pure functions
- `git_cmd()` helper wrapping subprocess
- `log_to_db()` extracted for easy mocking
- Parameterized SQL via `db.py`
- Column alignment via `formatting.py`

```python
#!/usr/bin/env python3
"""Pipeline module: base project/git info, model stats, weekly usage."""
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from statusline.formatting import (
    BLUE, YELLOW, GREEN, ORANGE, RED, DIM, RST,
    visible_len, pad_right, pad_left,
)
from statusline.db import get_db, upsert_session, append_weekly_usage


def git_cmd(*args: str) -> str:
    """Run a git command, return stdout or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def format_duration(duration_ms: int) -> str:
    """Format milliseconds as Xh:XXm or Xs."""
    total_s = duration_ms // 1000
    if total_s >= 3600:
        return f"{total_s // 3600}h:{(total_s % 3600) // 60:02d}m"
    elif total_s >= 60:
        return f"0h:{total_s // 60:02d}m"
    else:
        return f"{total_s}s"


def compute_projection(rate_7d: float, elapsed_hours: int) -> dict:
    """Compute weekly usage projection from current rate and elapsed time."""
    elapsed_hours = max(1, elapsed_hours)
    total_hours = 168  # 7 * 24
    daily_avg = rate_7d * 24 / elapsed_hours
    projected = rate_7d * total_hours / elapsed_hours
    elapsed_s = elapsed_hours * 3600
    elapsed_day = min(elapsed_s / 86400, 7.0)

    overage_dollars = 0
    if projected > 100.0:
        overage_dollars = int((projected - 100.0) * 10 / 5)

    return {
        "daily_avg": round(daily_avg, 1),
        "projected": round(projected, 1),
        "elapsed_day": round(elapsed_day, 2),
        "elapsed_hours": elapsed_hours,
        "overage_dollars": overage_dollars,
    }


def get_wed_10am_elapsed_hours() -> tuple[int, datetime]:
    """Calculate hours elapsed since last Wednesday 10am and return (hours, wed_datetime)."""
    now = datetime.now()
    dow = now.isoweekday()  # 1=Mon, 3=Wed, 7=Sun
    days_since_wed = (dow - 3) % 7
    if days_since_wed == 0 and now.hour < 10:
        days_since_wed = 7
    wed_10am = now.replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=days_since_wed)
    elapsed_s = (now - wed_10am).total_seconds()
    elapsed_hours = max(1, int(elapsed_s / 3600))
    return elapsed_hours, wed_10am


def log_to_db(claude: dict, session_id: str, context_pct: int,
              projection: dict, rate_5h: float, rate_7d: float,
              wed_10am: datetime, elapsed_hours: int) -> None:
    """Log session and usage data to SQLite."""
    try:
        db_path = os.path.expanduser("~/claude-usage.db")
        db = get_db(db_path)

        cost = claude.get("cost", {})
        ctx = claude.get("context_window", {})
        usage = ctx.get("current_usage", {})

        upsert_session(db,
            session_id=session_id,
            session_name=claude.get("session_name", ""),
            model_id=claude.get("model", {}).get("id", "unknown"),
            model_display=claude.get("model", {}).get("display_name", "unknown"),
            claude_version=claude.get("version", ""),
            cwd=claude.get("cwd", ""),
            project_dir=claude.get("workspace", {}).get("project_dir", ""),
            transcript_path=claude.get("transcript_path", ""),
            context_window_size=ctx.get("context_window_size", 0),
            duration_s=cost.get("total_duration_ms", 0) // 1000,
            api_duration_ms=cost.get("total_api_duration_ms", 0),
            lines_added=cost.get("total_lines_added", 0),
            lines_removed=cost.get("total_lines_removed", 0),
            total_cost_usd=f"{cost.get('total_cost_usd', 0):.2f}",
            total_input_tokens=ctx.get("total_input_tokens", 0),
            total_output_tokens=ctx.get("total_output_tokens", 0),
            cache_create_tokens=usage.get("cache_creation_input_tokens", 0),
            cache_read_tokens=usage.get("cache_read_input_tokens", 0),
            context_used_pct=context_pct,
        )

        append_weekly_usage(db,
            session_id=session_id,
            week_start=wed_10am.strftime("%Y-%m-%d"),
            elapsed_hours=elapsed_hours,
            elapsed_day=projection["elapsed_day"],
            weekly_pct=rate_7d,
            daily_avg_pct=projection["daily_avg"],
            five_hour_pct=rate_5h,
            five_hour_resets_at=claude.get("rate_limits", {}).get("five_hour", {}).get("resets_at", 0),
            seven_day_resets_at=claude.get("rate_limits", {}).get("seven_day", {}).get("resets_at", 0),
            projected_pct=projection["projected"],
        )
        db.close()
    except Exception:
        pass  # don't let logging failures break the status line


def run(claude_data: dict, lines: list[str]) -> list[str]:
    """Generate 3 status lines: project/git, model/stats, weekly usage."""
    claude = claude_data

    # Extract fields
    model_name = claude.get("model", {}).get("display_name", "unknown")
    rem_pct = int(claude.get("context_window", {}).get("remaining_percentage", 100))
    duration_ms = int(claude.get("cost", {}).get("total_duration_ms", 0))
    lines_added = int(claude.get("cost", {}).get("total_lines_added", 0))
    lines_removed = int(claude.get("cost", {}).get("total_lines_removed", 0))
    session_name = claude.get("session_name", "")
    total_changes = lines_added + lines_removed
    rate_5h = float(claude.get("rate_limits", {}).get("five_hour", {}).get("used_percentage", 0))
    rate_7d = float(claude.get("rate_limits", {}).get("seven_day", {}).get("used_percentage", 0))
    session_id = claude.get("session_id", "")

    duration = format_duration(duration_ms)

    # Project path — strip worktree suffixes
    cwd = claude.get("cwd", "")
    for suffix in ["/.claude/worktrees/", "/.worktrees/"]:
        if suffix in cwd:
            cwd = cwd[:cwd.index(suffix)]
    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = "~" + cwd[len(home):]

    # Git info
    branch = git_cmd("rev-parse", "--abbrev-ref", "HEAD")

    sep = f" {ORANGE}|{RST} "

    # Detect worktree
    is_worktree = False
    git_dir = git_cmd("rev-parse", "--git-dir")
    if git_dir and "/worktrees/" in git_dir:
        is_worktree = True

    # LINE 1
    l1c1 = f"{BLUE}{cwd}{RST}"
    if session_name:
        l1c1 += f" {DIM}({session_name}){RST}"

    l1c2 = ""
    l1c3 = ""
    if branch:
        dirty = git_cmd("status", "--porcelain")
        dirty_count = len(dirty.splitlines()) if dirty else 0

        if is_worktree:
            l1c2 = f"{GREEN}git-worktree{RST}:({YELLOW}{branch}{RST})"
        else:
            l1c2 = f"git:({YELLOW}{branch}{RST})"

        stats_parts = []
        if dirty_count > 0:
            stats_parts.append(f"{dirty_count} files changed")

        if branch not in ("main", "master"):
            commits = git_cmd("rev-list", "--count", "main..HEAD")
            if commits and int(commits) > 0:
                stats_parts.append(f"{commits} commits")
            behind = git_cmd("rev-list", "--count", "HEAD..main")
            if behind and int(behind) > 0:
                stats_parts.append(f"{behind} behind main")
        else:
            ahead = git_cmd("rev-list", "--count", "origin/main..HEAD")
            if ahead and int(ahead) > 0:
                stats_parts.append(f"{ahead} ahead of remote")
            behind = git_cmd("rev-list", "--count", "HEAD..origin/main")
            if behind and int(behind) > 0:
                stats_parts.append(f"{behind} behind remote")

        if not stats_parts:
            stats_parts.append("up to date")
        l1c3 = f"[{', '.join(stats_parts)}]"

    # LINE 2
    settings_path = os.path.expanduser("~/.claude/settings.json")
    effort = ""
    try:
        with open(settings_path) as f:
            effort = json.load(f).get("effortLevel", "")
    except (OSError, json.JSONDecodeError):
        pass

    l2c1 = model_name
    if effort:
        l2c1 += f", {effort}"

    # YOLO indicator
    if session_id:
        yolo_path = os.path.expanduser(f"~/.claude-yolo-sessions/{session_id}.json")
        if os.path.isfile(yolo_path):
            try:
                with open(yolo_path) as f:
                    yolo_data = json.load(f)
                needs_restart = yolo_data.get("needs_restart", False)
                if needs_restart:
                    l2c1 += f" {RED}YOLO{RST} {DIM}(needs restart){RST}"
                else:
                    l2c1 += f" {RED}YOLO{RST}"
            except (OSError, json.JSONDecodeError):
                l2c1 += f" {RED}YOLO{RST}"

    l2c2 = duration
    l2c3 = f"{total_changes} lines changed"

    used_pct = 100 - rem_pct
    is_opus_1m = "opus" in model_name.lower() and "1m" in model_name.lower()
    if is_opus_1m and used_pct > 20:
        context_col = f"{RED}{used_pct}% context used (compact needed){RST}"
    elif is_opus_1m and used_pct >= 18:
        context_col = f"{YELLOW}{used_pct}% context used{RST}"
    else:
        context_col = f"{used_pct}% context used"

    # LINE 3
    elapsed_hours, wed_10am = get_wed_10am_elapsed_hours()
    proj = compute_projection(rate_7d, elapsed_hours)

    l3c6 = ""
    predicted_display = f"{proj['projected']}% projected"
    if proj["projected"] > 100.0:
        l3c6 = f"~${proj['overage_dollars']} overage"
        predicted_display = f"{RED}{proj['projected']}%{RST} projected"

    l3c1 = f"Weekly usage {rate_7d:.1f}%"
    l3c2 = f"day: {proj['elapsed_day']:.2f}"
    l3c3 = f"daily ave: {proj['daily_avg']:.1f}%"
    l3c4 = f"5h: {rate_5h:.1f}%"
    l3c5 = predicted_display

    l2c4 = context_col

    # Column alignment
    col1_w = max(visible_len(l1c1), visible_len(l2c1), visible_len(l3c1))
    col2_w = max(visible_len(l1c2), visible_len(l2c2), visible_len(l3c2))
    col3_w = max(visible_len(l1c3), visible_len(l2c3), visible_len(l3c3))
    col4_w = max(visible_len(l2c4), visible_len(l3c4))
    col5_w = visible_len(l3c5)

    lbor = f"{ORANGE}|{RST} "

    line1 = f"{lbor}{pad_right(l1c1, col1_w)}"
    if branch:
        line1 += f"{sep}{pad_right(l1c2, col2_w)}{sep}{pad_right(l1c3, col3_w)}"

    line2 = f"{lbor}{pad_right(l2c1, col1_w)}{sep}{pad_right(l2c2, col2_w)}{sep}{pad_right(l2c3, col3_w)}{sep}{pad_right(l2c4, col4_w)}"

    line3 = f"{lbor}{pad_left(l3c1, col1_w)}{sep}{pad_right(l3c2, col2_w)}{sep}{pad_right(l3c3, col3_w)}{sep}{pad_right(l3c4, col4_w)}{sep}{pad_right(l3c5, col5_w)}"
    if l3c6:
        line3 += f"{sep}{l3c6}"

    # Log to SQLite (non-blocking)
    log_to_db(claude, session_id, used_pct, proj, rate_5h, rate_7d, wed_10am, elapsed_hours)

    return [line1, line2, line3]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_base_info.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/custom-status-line/skills/custom-status-line/references/statusline/base_info.py \
       plugins/custom-status-line/tests/test_base_info.py
git commit -m "feat(status-line): add base_info module — git stats, model info, usage projection"
git push
```

---

### Task 5: Create repo_cleanup.py

**Files:**
- Create: `plugins/custom-status-line/skills/custom-status-line/references/statusline/repo_cleanup.py`
- Create: `plugins/custom-status-line/tests/test_repo_cleanup.py`

- [ ] **Step 1: Write failing tests for repo_cleanup**

```python
# tests/test_repo_cleanup.py
import pytest
from unittest.mock import patch
from statusline.formatting import visible_len


def make_git_responses(**overrides):
    """Return a dict of git command -> response for mocking."""
    defaults = {
        ("rev-parse", "--git-dir"): ".git",
        ("symbolic-ref", "refs/remotes/origin/HEAD"): "refs/remotes/origin/main",
        ("branch", "-vv"): "  main abc1234 [origin/main] latest",
        ("branch", "--merged", "main"): "* main\n",
        ("worktree", "prune", "--dry-run"): "",
        ("branch", "-r"): "  origin/HEAD -> origin/main\n  origin/main\n",
        ("branch",): "* main\n",
        ("worktree", "list"): "/repo abc1234 [main]\n",
        ("rev-parse", "--show-toplevel"): "/repo",
    }
    defaults.update(overrides)
    return defaults


class TestRepoCleanupPassthrough:
    @patch("statusline.repo_cleanup.git_cmd")
    def test_no_git_repo_passes_through(self, mock_git):
        mock_git.return_value = ""
        from statusline.repo_cleanup import run
        lines = ["line1", "line2"]
        result = run({}, lines)
        assert result == lines

    @patch("statusline.repo_cleanup.git_cmd")
    def test_no_issues_passes_through(self, mock_git):
        responses = make_git_responses()
        def side_effect(*args):
            return responses.get(args, "")
        mock_git.side_effect = side_effect
        from statusline.repo_cleanup import run
        lines = ["line1", "line2"]
        result = run({}, lines)
        assert result == lines  # no warnings appended


class TestRepoCleanupWarnings:
    @patch("statusline.repo_cleanup.git_cmd")
    def test_stale_branches_detected(self, mock_git):
        responses = make_git_responses(**{
            ("branch", "-vv"): "  stale abc [origin/stale: gone] old\n  main def [origin/main] ok",
        })
        def side_effect(*args):
            return responses.get(args, "")
        mock_git.side_effect = side_effect
        from statusline.repo_cleanup import run
        lines = ["line1", "line2"]
        result = run({}, lines)
        assert "1 stale" in result[0]

    @patch("statusline.repo_cleanup.git_cmd")
    def test_merged_branches_detected(self, mock_git):
        responses = make_git_responses(**{
            ("branch", "--merged", "main"): "* main\n  feature-done\n",
        })
        def side_effect(*args):
            return responses.get(args, "")
        mock_git.side_effect = side_effect
        from statusline.repo_cleanup import run
        lines = ["line1", "line2"]
        result = run({}, lines)
        assert "1 merged" in result[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_repo_cleanup.py -v`
Expected: ImportError — `statusline.repo_cleanup` does not exist yet.

- [ ] **Step 3: Implement repo_cleanup.py**

```python
#!/usr/bin/env python3
"""Pipeline module: append repo cleanup warnings to line 1."""
import re
import subprocess
from statusline.formatting import ORANGE, RST


WARN = "\033[38;5;208m"


def git_cmd(*args: str) -> str:
    """Run a git command, return stdout or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def run(claude_data: dict, lines: list[str]) -> list[str]:
    """Detect repo issues and append warnings to line 1."""
    # Must be in a git repo
    if not git_cmd("rev-parse", "--git-dir"):
        return lines

    # Detect default branch
    default_branch = ""
    head_ref = git_cmd("symbolic-ref", "refs/remotes/origin/HEAD")
    if head_ref:
        default_branch = head_ref.replace("refs/remotes/origin/", "")
    if not default_branch:
        for candidate in ("main", "master"):
            check = git_cmd("show-ref", "--verify", "--quiet", f"refs/heads/{candidate}")
            # show-ref --quiet returns empty on success, but we need returncode
            # Since git_cmd returns "" on failure too, try rev-parse instead
            if git_cmd("rev-parse", "--verify", f"refs/heads/{candidate}"):
                default_branch = candidate
                break
    if not default_branch:
        return lines

    items = []

    # Stale branches — remote tracking branch deleted
    branch_vv = git_cmd("branch", "-vv")
    if branch_vv:
        stale = sum(1 for line in branch_vv.splitlines() if ": gone]" in line)
        if stale > 0:
            items.append(f"{stale} stale")

    # Merged branches — fully merged into default, safe to delete
    merged_output = git_cmd("branch", "--merged", default_branch)
    if merged_output:
        merged = 0
        for line in merged_output.splitlines():
            name = line.lstrip("* ").strip()
            if name and name not in (default_branch, "main", "master"):
                merged += 1
        if merged > 0:
            items.append(f"{merged} merged")

    # Prunable worktrees
    prune_output = git_cmd("worktree", "prune", "--dry-run")
    if prune_output:
        prunable = len(prune_output.splitlines())
        if prunable > 0:
            items.append(f"{prunable} prunable wt")

    # Remote-only branches
    remote_branches = git_cmd("branch", "-r")
    local_branches = git_cmd("branch")
    if remote_branches and local_branches:
        remotes = set()
        for line in remote_branches.splitlines():
            name = line.strip()
            if "/HEAD" not in name:
                remotes.add(re.sub(r"^origin/", "", name))
        locals_ = set()
        for line in local_branches.splitlines():
            locals_.add(line.lstrip("* ").strip())
        remote_only = len(remotes - locals_)
        if remote_only > 0:
            items.append(f"{remote_only} remote-only")

    # Finished worktrees — branch merged but worktree still exists
    wt_list = git_cmd("worktree", "list")
    main_path = git_cmd("rev-parse", "--show-toplevel")
    if wt_list and main_path:
        finished = 0
        for line in wt_list.splitlines():
            if not line.strip():
                continue
            parts = line.split()
            wt_path = parts[0] if parts else ""
            branch_match = re.search(r"\[(.+)\]", line)
            wt_branch = branch_match.group(1) if branch_match else ""
            if wt_path == main_path or not wt_branch:
                continue
            # Check if branch is ancestor of default
            check = subprocess.run(
                ["git", "merge-base", "--is-ancestor", wt_branch, default_branch],
                capture_output=True, timeout=5,
            )
            if check.returncode == 0:
                finished += 1
        if finished > 0:
            items.append(f"{finished} done wt")

    if not items:
        return lines

    sep = f" {ORANGE}|{RST} "
    status = ", ".join(items)
    warning = f"{sep}{WARN}\u26a0 {status}{RST}"
    result = list(lines)
    if result:
        result[0] = (result[0] or "") + warning
    else:
        result.append(warning)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_repo_cleanup.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/custom-status-line/skills/custom-status-line/references/statusline/repo_cleanup.py \
       plugins/custom-status-line/tests/test_repo_cleanup.py
git commit -m "feat(status-line): add repo_cleanup module — stale/merged/remote branch detection"
git push
```

---

### Task 6: Create progress_display.py

**Files:**
- Create: `plugins/custom-status-line/skills/custom-status-line/references/statusline/progress_display.py`
- Create: `plugins/custom-status-line/tests/test_progress_display.py`

- [ ] **Step 1: Write failing tests for progress_display**

```python
# tests/test_progress_display.py
import json
import pytest
from statusline.formatting import visible_len


class TestProgressDisplayPassthrough:
    def test_no_session_id_passes_through(self):
        from statusline.progress_display import run
        lines = ["line1", "line2"]
        result = run({}, lines)
        assert result == lines

    def test_no_progress_file_passes_through(self, tmp_path):
        from statusline.progress_display import run
        lines = ["line1", "line2"]
        result = run({"session_id": "no-such-session"}, lines)
        assert result == lines


class TestProgressDisplayRendering:
    def test_appends_six_lines(self, tmp_path, monkeypatch):
        # Write a progress file
        progress_dir = tmp_path / "progress"
        progress_dir.mkdir()
        progress_file = progress_dir / "test-sess.json"
        progress_file.write_text(json.dumps({
            "title": "Building",
            "subtitle": "Step",
            "count": 3,
            "max": 10,
            "cols": 60,
            "session_id": "test-sess",
        }))
        monkeypatch.setenv("HOME", str(tmp_path))
        # Create the expected directory structure
        sl_dir = tmp_path / ".claude-status-line" / "progress"
        sl_dir.mkdir(parents=True)
        (sl_dir / "test-sess.json").write_text(progress_file.read_text())

        from statusline.progress_display import run
        lines = ["line1", "line2"]
        result = run({"session_id": "test-sess"}, lines)
        assert len(result) == 8  # 2 original + 6 box lines

    def test_progress_bar_percentage(self, tmp_path, monkeypatch):
        sl_dir = tmp_path / ".claude-status-line" / "progress"
        sl_dir.mkdir(parents=True)
        (sl_dir / "sess.json").write_text(json.dumps({
            "title": "Test", "subtitle": "Working",
            "count": 5, "max": 10, "cols": 60, "session_id": "sess",
        }))
        monkeypatch.setenv("HOME", str(tmp_path))

        from statusline.progress_display import run
        result = run({"session_id": "sess"}, [])
        # Find the subtitle line — should contain "50%"
        text = " ".join(result)
        assert "50%" in text

    def test_count_clamped_to_max(self, tmp_path, monkeypatch):
        sl_dir = tmp_path / ".claude-status-line" / "progress"
        sl_dir.mkdir(parents=True)
        (sl_dir / "sess.json").write_text(json.dumps({
            "title": "Test", "subtitle": "Done",
            "count": 15, "max": 10, "cols": 60, "session_id": "sess",
        }))
        monkeypatch.setenv("HOME", str(tmp_path))

        from statusline.progress_display import run
        result = run({"session_id": "sess"}, [])
        text = " ".join(result)
        assert "100%" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_progress_display.py -v`
Expected: ImportError — `statusline.progress_display` does not exist yet.

- [ ] **Step 3: Implement progress_display.py**

```python
#!/usr/bin/env python3
"""Pipeline module: boxed progress bar display."""
import json
import os
import shutil
from pathlib import Path

from statusline.formatting import BLUE, GREEN, DIM, RST, visible_len


def run(claude_data: dict, lines: list[str]) -> list[str]:
    """Render a progress bar box if session has active progress."""
    session_id = claude_data.get("session_id", "")
    if not session_id:
        return lines

    progress_dir = os.path.expanduser("~/.claude-status-line/progress")
    progress_file = os.path.join(progress_dir, f"{session_id}.json")

    if not os.path.isfile(progress_file):
        return lines

    try:
        with open(progress_file) as f:
            progress = json.load(f)
    except (OSError, json.JSONDecodeError):
        return lines

    title = progress.get("title", "")
    subtitle = progress.get("subtitle", "")
    count = progress.get("count", 0)
    max_val = progress.get("max", 0)

    if not title or max_val <= 0:
        return lines

    # Clamp count
    count = max(0, min(count, max_val))
    pct = count * 100 // max_val

    # Terminal width
    cols = progress.get("cols")
    if not cols:
        cols = shutil.get_terminal_size((80, 24)).columns

    # Box dimensions
    inner = max(20, cols - 4)  # subtract "| " and " |"

    def center_line(text: str, text_vis_len: int) -> str:
        pad_left = (inner - text_vis_len) // 2
        pad_right = inner - text_vis_len - pad_left
        pad_left = max(0, pad_left)
        pad_right = max(0, pad_right)
        return f"{DIM}|{RST}{' ' * pad_left}{text}{' ' * pad_right}{DIM}|{RST}"

    # Border
    border = f"{DIM}|{'-' * inner}|{RST}"

    # Empty line
    empty = f"{DIM}|{RST}{' ' * inner}{DIM}|{RST}"

    # Title
    title_text = f"{BLUE}{title}{RST}"
    title_line = center_line(title_text, len(title))

    # Progress bar
    bar_width = max(10, inner - 6)  # subtract "  [" and "]  "
    filled = count * bar_width // max_val
    empty_bar = bar_width - filled
    bar_content = f"  {DIM}[{RST}{GREEN}{'=' * filled}{RST}{' ' * empty_bar}{DIM}]{RST}  "
    bar_vis_len = bar_width + 6
    bar_line = center_line(bar_content, bar_vis_len)

    # Subtitle
    sub_text = f"{subtitle} {count}/{max_val} ({pct}%)"
    sub_styled = f"{DIM}{sub_text}{RST}"
    sub_line = center_line(sub_styled, len(sub_text))

    return lines + [border, empty, title_line, bar_line, sub_line, border]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_progress_display.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/custom-status-line/skills/custom-status-line/references/statusline/progress_display.py \
       plugins/custom-status-line/tests/test_progress_display.py
git commit -m "feat(status-line): add progress_display module — boxed progress bar"
git push
```

---

### Task 7: Create update_progress.py (standalone CLI)

**Files:**
- Create: `plugins/custom-status-line/skills/custom-status-line/references/statusline/update_progress.py`
- Create: `plugins/custom-status-line/tests/test_update_progress.py`

- [ ] **Step 1: Write failing tests for update_progress**

```python
# tests/test_update_progress.py
import json
import pytest
from unittest.mock import patch


class TestSessionDiscovery:
    @patch("statusline.update_progress.find_session_id")
    def test_finds_session_id(self, mock_find):
        mock_find.return_value = "sess-123"
        from statusline.update_progress import find_session_id
        assert find_session_id() == "sess-123"


class TestUpdateProgress:
    def test_writes_progress_file(self, tmp_path, monkeypatch):
        progress_dir = tmp_path / ".claude-status-line" / "progress"
        monkeypatch.setenv("HOME", str(tmp_path))

        from statusline.update_progress import write_progress
        write_progress("sess-1", "Building", "Step", 3, 10, 80)

        pfile = progress_dir / "sess-1.json"
        assert pfile.exists()
        data = json.loads(pfile.read_text())
        assert data["title"] == "Building"
        assert data["count"] == 3
        assert data["max"] == 10

    def test_clear_removes_file(self, tmp_path, monkeypatch):
        progress_dir = tmp_path / ".claude-status-line" / "progress"
        progress_dir.mkdir(parents=True)
        pfile = progress_dir / "sess-1.json"
        pfile.write_text("{}")
        monkeypatch.setenv("HOME", str(tmp_path))

        from statusline.update_progress import clear_progress
        clear_progress("sess-1")
        assert not pfile.exists()

    def test_clear_missing_file_is_ok(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        from statusline.update_progress import clear_progress
        clear_progress("no-such-session")  # should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_update_progress.py -v`
Expected: ImportError — `statusline.update_progress` does not exist yet.

- [ ] **Step 3: Implement update_progress.py**

```python
#!/usr/bin/env python3
"""Standalone CLI: update per-session progress bar file.

Usage:
    python3 -m statusline.update_progress <title> <subtitle> <count> <max>
    python3 -m statusline.update_progress --clear
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_session_id() -> str:
    """Walk up the process tree to find the Claude session ID."""
    pid = os.getpid()
    home = os.path.expanduser("~")
    while pid > 1:
        session_file = os.path.join(home, ".claude", "sessions", f"{pid}.json")
        if os.path.isfile(session_file):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                    sid = data.get("sessionId", "")
                    if sid:
                        return sid
            except (OSError, json.JSONDecodeError):
                pass
        # Get parent PID
        try:
            result = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(pid)],
                capture_output=True, text=True, timeout=2,
            )
            pid = int(result.stdout.strip())
        except (subprocess.TimeoutExpired, ValueError, OSError):
            break
    return ""


def write_progress(session_id: str, title: str, subtitle: str,
                   count: int, max_val: int, cols: int) -> None:
    """Write a progress file for the given session."""
    progress_dir = os.path.expanduser("~/.claude-status-line/progress")
    os.makedirs(progress_dir, exist_ok=True)
    progress_file = os.path.join(progress_dir, f"{session_id}.json")
    data = {
        "title": title,
        "subtitle": subtitle,
        "count": count,
        "max": max_val,
        "cols": cols,
        "session_id": session_id,
    }
    with open(progress_file, "w") as f:
        json.dump(data, f)


def clear_progress(session_id: str) -> None:
    """Remove the progress file for the given session."""
    progress_dir = os.path.expanduser("~/.claude-status-line/progress")
    progress_file = os.path.join(progress_dir, f"{session_id}.json")
    try:
        os.remove(progress_file)
    except FileNotFoundError:
        pass


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--clear":
        session_id = find_session_id()
        if not session_id:
            print("Error: could not determine session ID", file=sys.stderr)
            sys.exit(1)
        clear_progress(session_id)
        print("Progress cleared.")
        return

    if len(sys.argv) < 5:
        print("Usage: python3 -m statusline.update_progress <title> <subtitle> <count> <max>")
        print("       python3 -m statusline.update_progress --clear")
        sys.exit(1)

    title = sys.argv[1]
    subtitle = sys.argv[2]
    count = int(sys.argv[3])
    max_val = int(sys.argv[4])

    session_id = find_session_id()
    if not session_id:
        print("Error: could not determine session ID", file=sys.stderr)
        sys.exit(1)

    cols = shutil.get_terminal_size((80, 24)).columns
    write_progress(session_id, title, subtitle, count, max_val, cols)

    pct = count * 100 // max_val if max_val > 0 else 0
    print(f"{title}: {subtitle} {count}/{max_val} ({pct}%)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_update_progress.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/custom-status-line/skills/custom-status-line/references/statusline/update_progress.py \
       plugins/custom-status-line/tests/test_update_progress.py
git commit -m "feat(status-line): add update_progress CLI — session-scoped progress writer"
git push
```

---

### Task 8: Create ensure_permissions.py (standalone CLI)

**Files:**
- Create: `plugins/custom-status-line/skills/custom-status-line/references/statusline/ensure_permissions.py`
- Create: `plugins/custom-status-line/tests/test_ensure_permissions.py`

- [ ] **Step 1: Write failing tests for ensure_permissions**

```python
# tests/test_ensure_permissions.py
import json
import pytest


class TestEnsurePermissions:
    def test_extracts_and_merges_bash_patterns(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "name: test\n"
            "allowed-tools: Read, Bash(chmod *), Bash(mkdir -p *)\n"
            "---\n"
            "# Test\n"
        )
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"permissions": {"allow": ["Read"]}}))

        from statusline.ensure_permissions import merge_permissions
        merge_permissions(str(skill_md), str(settings))

        result = json.loads(settings.read_text())
        allow = result["permissions"]["allow"]
        assert "Bash(chmod *)" in allow
        assert "Bash(mkdir -p *)" in allow
        assert "Read" in allow

    def test_deduplicates(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "allowed-tools: Bash(chmod *)\n"
            "---\n"
        )
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"permissions": {"allow": ["Bash(chmod *)"]}}))

        from statusline.ensure_permissions import merge_permissions
        merge_permissions(str(skill_md), str(settings))

        result = json.loads(settings.read_text())
        assert result["permissions"]["allow"].count("Bash(chmod *)") == 1

    def test_missing_skill_file_is_noop(self, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"permissions": {"allow": []}}))

        from statusline.ensure_permissions import merge_permissions
        merge_permissions("/nonexistent/SKILL.md", str(settings))

        result = json.loads(settings.read_text())
        assert result["permissions"]["allow"] == []

    def test_missing_settings_file_is_noop(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nallowed-tools: Bash(chmod *)\n---\n")

        from statusline.ensure_permissions import merge_permissions
        merge_permissions(str(skill_md), "/nonexistent/settings.json")
        # Should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_ensure_permissions.py -v`
Expected: ImportError — `statusline.ensure_permissions` does not exist yet.

- [ ] **Step 3: Implement ensure_permissions.py**

```python
#!/usr/bin/env python3
"""Standalone CLI: merge Bash() tool patterns from SKILL.md into settings.json.

Usage:
    python3 -m statusline.ensure_permissions /path/to/SKILL.md
"""
import json
import os
import re
import sys


def merge_permissions(skill_path: str, settings_path: str) -> None:
    """Extract Bash() patterns from SKILL.md frontmatter and merge into settings."""
    if not os.path.isfile(skill_path) or not os.path.isfile(settings_path):
        return

    # Read frontmatter
    try:
        with open(skill_path) as f:
            content = f.read()
    except OSError:
        return

    # Extract frontmatter between --- markers
    parts = content.split("---", 2)
    if len(parts) < 3:
        return
    frontmatter = parts[1]

    # Find Bash() patterns
    patterns = re.findall(r"Bash\([^)]+\)", frontmatter)
    if not patterns:
        return

    # Read settings
    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except (OSError, json.JSONDecodeError):
        return

    # Merge and deduplicate
    allow = settings.get("permissions", {}).get("allow", [])
    merged = list(dict.fromkeys(allow + patterns))  # preserves order, deduplicates
    settings.setdefault("permissions", {})["allow"] = merged

    # Write atomically
    tmp_path = settings_path + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(settings, f, indent=2)
        os.replace(tmp_path, settings_path)
    except OSError:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 -m statusline.ensure_permissions /path/to/SKILL.md")
        sys.exit(1)

    skill_path = sys.argv[1]
    settings_path = os.path.expanduser("~/.claude/settings.json")
    merge_permissions(skill_path, settings_path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/test_ensure_permissions.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/custom-status-line/skills/custom-status-line/references/statusline/ensure_permissions.py \
       plugins/custom-status-line/tests/test_ensure_permissions.py
git commit -m "feat(status-line): add ensure_permissions CLI — merge tool patterns into settings"
git push
```

---

### Task 9: Run full test suite and integration test

**Files:**
- None new — validate all existing tests pass together

- [ ] **Step 1: Run all tests**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/ -v`
Expected: All tests PASS across all modules.

- [ ] **Step 2: Run dispatcher integration test manually**

Create a quick manual integration test by piping mock JSON through the dispatcher:

```bash
cd plugins/custom-status-line/skills/custom-status-line/references
echo '{"model":{"display_name":"Test","id":"test"},"context_window":{"remaining_percentage":90,"context_window_size":200000,"total_input_tokens":0,"total_output_tokens":0,"current_usage":{"cache_creation_input_tokens":0,"cache_read_input_tokens":0}},"cost":{"total_duration_ms":60000,"total_api_duration_ms":5000,"total_lines_added":10,"total_lines_removed":5,"total_cost_usd":0.5},"cwd":"/tmp/test","session_id":"manual-test","session_name":"","rate_limits":{"five_hour":{"used_percentage":5.0,"resets_at":0},"seven_day":{"used_percentage":28.5,"resets_at":0}},"version":"1.0","workspace":{"project_dir":"/tmp"},"transcript_path":""}' | python3 -m statusline.dispatcher
```

Expected: 3 lines of plain text output with project info, model stats, and usage.

- [ ] **Step 3: Commit if any test fixes were needed**

If any tests needed fixes, commit them. If all passed, skip this step.

---

### Task 10: Remove old bash scripts

**Files:**
- Delete: `plugins/custom-status-line/skills/custom-status-line/references/dispatcher.sh`
- Delete: `plugins/custom-status-line/skills/custom-status-line/references/base-info.sh`
- Delete: `plugins/custom-status-line/skills/custom-status-line/references/repo-cleanup.sh`
- Delete: `plugins/custom-status-line/skills/custom-status-line/references/progress-display.sh`
- Delete: `plugins/custom-status-line/skills/custom-status-line/references/update-progress.sh`
- Delete: `plugins/custom-status-line/skills/custom-status-line/references/ensure-permissions.sh`

- [ ] **Step 1: Delete all old bash scripts**

```bash
git rm plugins/custom-status-line/skills/custom-status-line/references/dispatcher.sh \
       plugins/custom-status-line/skills/custom-status-line/references/base-info.sh \
       plugins/custom-status-line/skills/custom-status-line/references/repo-cleanup.sh \
       plugins/custom-status-line/skills/custom-status-line/references/progress-display.sh \
       plugins/custom-status-line/skills/custom-status-line/references/update-progress.sh \
       plugins/custom-status-line/skills/custom-status-line/references/ensure-permissions.sh
```

- [ ] **Step 2: Verify tests still pass**

Run: `cd plugins/custom-status-line && python3 -m pytest tests/ -v`
Expected: All tests PASS (no tests depend on .sh files).

- [ ] **Step 3: Commit**

```bash
git commit -m "refactor(status-line): remove bash scripts, replaced by Python statusline package"
git push
```

---

### Task 11: Update SKILL.md for Python install/uninstall

**Files:**
- Modify: `plugins/custom-status-line/skills/custom-status-line/SKILL.md`

- [ ] **Step 1: Update SKILL.md**

Update the following sections of SKILL.md:

**Startup** — change ensure-permissions call:
```
python3 ${CLAUDE_SKILL_DIR}/references/statusline/ensure_permissions.py ${CLAUDE_SKILL_DIR}/SKILL.md
```

**Help section** — update architecture diagram to show Python files instead of bash.

**Install section constants** — update source paths:
```
- **Dispatcher source**: `${CLAUDE_SKILL_DIR}/references/statusline/dispatcher.py`
- **Package source**: `${CLAUDE_SKILL_DIR}/references/statusline/`
- **Update progress source**: `${CLAUDE_SKILL_DIR}/references/statusline/update_progress.py`
```

**Install Step 3** — change to copy the Python package:
```
Copy the entire statusline package from ${CLAUDE_SKILL_DIR}/references/statusline/ to ~/.claude-status-line/statusline/.
Write a shell wrapper at ~/.claude-status-line/progress/update-progress.sh:
#!/bin/bash
exec python3 -m statusline.update_progress "$@"
Make it executable: chmod +x ~/.claude-status-line/progress/update-progress.sh
```

**Install Step 4** — update default pipeline.json to use `"module"` keys:
```json
{
  "pipeline": [
    {"name": "base-info", "module": "base_info"},
    {"name": "repo-cleanup", "module": "repo_cleanup"},
    {"name": "progress-display", "module": "progress_display"}
  ]
}
```

When migrating existing pipeline.json: replace `"script"` entries that reference built-in `.sh` files with `"module"` entries. Preserve any user-added external script entries.

**Install Step 5** — update statusLine command:
```json
"statusLine": {
  "type": "command",
  "command": "PYTHONPATH=$HOME/.claude-status-line python3 -m statusline.dispatcher"
}
```

**Version** — bump to 4.0.0 (major: breaking change to Python runtime).

- [ ] **Step 2: Verify the skill file is syntactically valid**

Read the updated SKILL.md and check that the YAML frontmatter is valid and all sections are present.

- [ ] **Step 3: Commit**

```bash
git add plugins/custom-status-line/skills/custom-status-line/SKILL.md
git commit -m "feat(status-line): update SKILL.md for Python install/uninstall, bump to v4.0.0"
git push
```

---

### Task 12: Update documentation

**Files:**
- Modify: `plugins/custom-status-line/how-to-add-status-line-scripts.md`
- Modify: `plugins/custom-status-line/README.md`
- Modify: `plugins/custom-status-line/.claude-plugin/plugin.json`

- [ ] **Step 1: Update how-to-add-status-line-scripts.md**

Update the architecture diagram to show Python files. Update the script protocol section to note that the dispatcher is now Python-based. External drop-in scripts still use the same JSON-on-stdin protocol and can be any language. Keep all bash examples intact (they're for external script authors). Add a note that built-in modules use `"module"` keys in pipeline.json while external scripts use `"script"` keys.

- [ ] **Step 2: Update README.md**

Update references from `.sh` to Python. Update the version number to 4.0.0.

- [ ] **Step 3: Update plugin.json version**

Read `plugins/custom-status-line/.claude-plugin/plugin.json` and bump the version to "4.0.0".

- [ ] **Step 4: Commit**

```bash
git add plugins/custom-status-line/how-to-add-status-line-scripts.md \
       plugins/custom-status-line/README.md \
       plugins/custom-status-line/.claude-plugin/plugin.json
git commit -m "docs(status-line): update documentation for Python conversion, v4.0.0"
git push
```

---

### Task 13: Live validation

- [ ] **Step 1: Install the updated plugin**

Run `/custom-status-line install` in a Claude session to install the Python version.

- [ ] **Step 2: Verify status line renders correctly**

Start a new Claude session and verify:
- 3-line status display appears
- Project path, git info, model name, usage stats all render
- Column alignment is correct
- ANSI colors display properly

- [ ] **Step 3: Verify progress bar works**

```bash
~/.claude-status-line/progress/update-progress.sh "Test" "Step" 3 10
# Verify progress bar appears in status line
~/.claude-status-line/progress/update-progress.sh --clear
# Verify progress bar disappears
```

- [ ] **Step 4: Verify external script compatibility**

If any external drop-in scripts exist in pipeline.json, verify they still run.

- [ ] **Step 5: Report results**

Report pass/fail for each verification step.
