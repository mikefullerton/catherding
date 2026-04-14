# Status Line System Design

## Architecture Overview

The status line is a modular pipeline that runs on every Claude Code prompt. Claude Code passes session JSON to stdin, the pipeline produces formatted text lines for display.

```
stdin (JSON) --> dispatcher.py --> [pipeline stages] --> stdout (text lines)
```

### Invocation

Configured in `~/.claude/settings.json`:

```json
"statusLine": {
  "command": "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$HOME/.claude-status-line python3 -m statusline.dispatcher",
  "type": "command"
}
```

Each invocation is a fresh Python process. `PYTHONDONTWRITEBYTECODE=1` prevents `.pyc` caching so file updates take effect immediately across all sessions.

### Installed Location

```
~/.claude-status-line/
  pipeline.json                     # Pipeline config: stage order, progress style
  statusline/                       # Python package
    __init__.py
    dispatcher.py                   # Entry point: reads stdin, runs pipeline, prints output
    formatting.py                   # Row class, ANSI colors, column alignment
    base_info.py                    # Primary module: path, git, model, sessions, usage, version
    repo_cleanup.py                 # Appends cleanup warnings to header line
    progress_display.py             # Progress bar rendering (standard or compact)
    graphify_savings.py             # Graphify token savings per project
    version_check.py                # Version tracking: DB-backed, runs last in pipeline
    usage_costs.py                  # Legacy standalone usage module (not in active pipeline)
    version_tracker.py              # Legacy standalone version module (not in active pipeline)
    db.py                           # SQLite schema and logging helpers (DB_VERSION=4)
    update_progress.py              # CLI for updating progress from hooks
  scripts/
    graphify-savings-update.py      # Background updater for graphify savings cache
  progress/
    update-progress.py              # Progress update entry point
  sessions/                         # Per-session state files ({session_id}.json)
  graphify-savings-cache.json       # Cached graphify savings data
  graphify-savings.lock             # Rate-limit lock for graphify updater
  scanner-last-run                  # Rate-limit timestamp for usage scanner
  dispatcher.log                    # Error log
```

### Source Location

```
skills/custom-status-line/
  references/
    statusline/                     # Python package source (copied to ~/.claude-status-line/)
    scripts/                        # Background scripts source
  SKILL.md                          # Install/uninstall instructions
  tests/                            # 100 tests
```

---

## Pipeline Architecture

### dispatcher.py

The dispatcher reads `pipeline.json`, imports modules, and runs them in order:

```json
{
  "progress_style": "compact",
  "pipeline": [
    {"name": "base-info",         "module": "base_info"},
    {"name": "repo-cleanup",      "module": "repo_cleanup"},
    {"name": "progress-display",  "module": "progress_display"},
    {"name": "graphify-savings",  "module": "graphify_savings"}
  ]
}
```

Two data structures flow through the pipeline:

- **`lines`** (list of strings) -- non-columnar output (header, warnings, progress bars). Each stage receives and returns this list.
- **`rows`** (list of Row objects) -- columnar data. Shared across all stages. Modules that accept a `rows` parameter append Row objects to it.

After all stages complete, the dispatcher does **one formatting pass** on all rows:

```python
widths = compute_column_widths(rows)
format_rows(rows, widths)
for row in rows:
    lines.append(row.render())
```

This ensures all columns align across every module's output.

### Module Interface

Modules implement `run(claude_data, lines, rows=None) -> list`:

- **Columnar modules** (`base_info`, `graphify_savings`) accept `rows` and append Row objects.
- **Non-columnar modules** (`repo_cleanup`, `progress_display`) only use `lines`.
- The dispatcher uses `inspect.signature()` to detect which interface a module supports.

External scripts receive `{"claude": claude_data, "lines": lines}` on stdin and return `{"lines": [...]}` on stdout.

---

## Row Class and Formatting

### Row

```python
class Row:
    def __init__(self, *columns):
        self.columns = [c.strip() if c else "" for c in columns]
        self.formatted = []

    def render(self):
        return "| " + " | ".join(self.formatted)
```

- Raw column values are whitespace-trimmed on construction
- `formatted` is populated by `format_rows()` -- padded to shared column widths
- `render()` joins formatted columns with `" | "` separator and `"| "` border

### Column Alignment

```python
def compute_column_widths(rows) -> list[int]:
    # Returns max visible_len per column across all rows
    # No extra padding -- separator " | " provides spacing

def format_rows(rows, widths) -> None:
    # Col 0: right-aligned (pad_left)
    # Cols 1+: left-aligned (pad_right)
    # Trailing empty columns omitted; interior empty columns padded
    # Verification: raises ValueError if any column position has inconsistent widths
```

### ANSI-Aware Measurement

`visible_len(s)` strips ANSI escape codes (`\033[...m`) before measuring. All padding functions use visible length, not string length, so colored text aligns correctly.

### Color Constants

```python
BLUE   = "\033[38;5;117m"   # paths
YELLOW = "\033[38;5;229m"   # branches, warnings, version numbers
GREEN  = "\033[38;5;151m"   # opus model, savings, new fields
ORANGE = "\033[38;5;214m"   # progress bars
RED    = "\033[38;5;210m"   # non-opus model, overages, extended context
DIM    = "\033[38;5;245m"   # labels, inactive states
RST    = "\033[0m"          # reset
```

---

## Output Layout

### Line 1 -- Header (non-columnar)

```
~/projects/active/cat-herding on worktree-split-usage-lines | !! 2 stale | 1 merged
```

- Path relative to `~` (blue), branch (yellow)
- Worktree: uses `worktree.original_cwd` for the path
- `repo_cleanup` appends warnings (orange) if any: stale branches, merged branches, prunable worktrees, remote-only branches, finished worktrees

### Lines 2+ -- Columnar Rows

All rows share column widths. Col 0 is right-aligned, rest left-aligned.

```
| col0 (right)  | col1 (left)      | col2 (left)      | col3 (left)       |
```

#### Git Row (if in a git repo)

| Col 0 | Col 1 | Col 2 | Col 3 |
|-------|-------|-------|-------|
| `git` | `files: ~N +N -N` | `remote: in sync` or `remote: up/dn` | `main: in sync` or `main: up/dn` |

- File counts from `git status --porcelain`
- Remote sync from `git rev-list --count` against `origin/{branch}`
- Main comparison only shown when not on main/master
- Non-zero counts colored yellow

#### Model Row

| Col 0 | Col 1 | Col 2 | Col 3 (optional) |
|-------|-------|-------|-------|
| model name | duration | `X% / 200k ctx` | `YOLO` |

- Model name: green for Opus, red otherwise
- Duration: `format_duration(total_duration_ms)` -- `Xh:XXm`, `0h:XXm`, or `Xs`
- Context: yellow if >200k and >20% used, red if extended beyond 200k
- YOLO indicator: red, only when `~/.claude-yolo-sessions/{session_id}.json` exists

#### Sessions Row

| Col 0 | Col 1 | Col 2 | Col 3 |
|-------|-------|-------|-------|
| `all sessions` (dim) | `N active` | `N thinking` | `N waiting` |

- Reads `~/.claude-status-line/sessions/*.json`
- Removes stale files (mtime > 1 hour)
- State is `"thinking"` or `"waiting"`

#### Usage Row 1 -- Weekly

| Col 0 | Col 1 | Col 2 | Col 3 |
|-------|-------|-------|-------|
| `weekly: X.X%` | `daily ave: X.X%` | `X.Xd left` | `X.X% projected` |

- Only shown if `rate_7d > 0` and usage.db exists with cost data
- Projected > 100% shown in red
- First 6 hours: daily ave and projected show as dim `--` / `too early`

#### Usage Row 2 -- Today

| Col 0 | Col 1 | Col 2 |
|-------|-------|-------|
| `today: X.X%` | `5h: X.X%` | `-Xh XXm` |

- Today's percentage: calibrated from daily cost
- 5h: the 5-hour rolling quota percentage
- Countdown: time until 5h quota resets (omitted if no active countdown)

#### Graphify Savings Rows (per project)

| Col 0 | Col 1 | Col 2 | Col 3 |
|-------|-------|-------|-------|
| project name (dim) | `saving X%` (green) | `36.4k -> 4.9k` | `75 pre . 4 post` (dim) |

- One row per project with graphify installed
- Savings: green if >5%, dim if ~0%, orange if worse
- Token counts: pre-average -> post-average
- Last row: `TOTAL` with weighted net savings across all projects

#### Version Rows (last, optional, one per new version)

| Col 0 | Col 1 | Col 2 |
|-------|-------|-------|
| `claude 2.1.108` | `2 new fields` (green) | `field.a, field.b` (dim) |
| `claude 2.1.109` | `no new fields` (dim) | |

- Only shown when versions exist above `BUILT_FOR_VERSION` in version_check.py
- One row per new version, in ascending order
- Each row diffs against the previous version in the DB (not cumulative)
- Produced by `version_check.py` (last pipeline stage)
- Throttled: checked every 5 minutes + on session start

### Progress Bar (non-columnar, after all rows)

**Compact style** (2 lines, sized to status line width):
```
|||||||||||||||||              |
| title       [3/10] (30%)    |
```

**Standard style** (6 lines, boxed):
```
|-------------------------------------|
|                                     |
|             title                   |
|        [=======          ]          |
|       subtitle 3/10 (30%)          |
|-------------------------------------|
```

---

## Database

### Status Line DB (`~/claude-usage.db`)

DB_VERSION = 4. Logged by `base_info.py` (sessions, weekly_usage) and `version_check.py` (claude_versions) on every pipeline run.

#### claude_versions table

```sql
CREATE TABLE claude_versions (
    claude_version TEXT PRIMARY KEY,
    fields TEXT NOT NULL,           -- full claude_data JSON blob
    fields_count INTEGER NOT NULL,  -- count of extracted field paths
    first_seen TEXT NOT NULL        -- ISO timestamp
);
```

One row per Claude version ever seen. The `fields` column stores the complete `claude_data` JSON object as self-contained, pretty-printed JSON. Field paths are extracted on read.

#### sessions table

```sql
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
    first_seen TEXT NOT NULL,        -- ISO timestamp
    last_seen TEXT NOT NULL,         -- ISO timestamp (updated each run)
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
```

Upserted on every pipeline run. `first_seen` preserved, `last_seen` updated.

#### weekly_usage table

```sql
CREATE TABLE weekly_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    week_start TEXT NOT NULL,       -- Wednesday date (YYYY-MM-DD)
    elapsed_hours INTEGER NOT NULL,
    day REAL NOT NULL,              -- elapsed days (0.0 - 7.0)
    weekly_pct REAL NOT NULL,
    daily_avg_pct REAL NOT NULL,
    five_hour_pct REAL NOT NULL,
    five_hour_resets_at INTEGER,    -- epoch seconds
    seven_day_resets_at INTEGER,    -- epoch seconds
    projected_pct REAL NOT NULL
);
```

Appended on every pipeline run. Deduplication: skips if all values unchanged from last row.

### Usage DB (`~/.claude/usage.db`)

Built by external scanner (`~/projects/external/claude-usage/scanner.py`). Read-only by status line.

#### turns table

```sql
CREATE TABLE turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp TEXT,
    model TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_creation_tokens INTEGER DEFAULT 0,
    tool_name TEXT,
    cwd TEXT,
    message_id TEXT
);
```

One row per Claude API turn. Source of truth for token counts.

---

## Usage Cost Calculations

### Weekly Window

Wednesday 10:00 AM to Wednesday 10:00 AM (7 days, 168 hours).

```python
def get_wed_10am():
    now = datetime.now()
    dow = now.isoweekday()  # 1=Mon, 3=Wed, 7=Sun
    days_since_wed = (dow - 3) % 7
    if days_since_wed == 0 and now.hour < 10:
        days_since_wed = 7
    return now.replace(hour=10, minute=0, second=0) - timedelta(days=days_since_wed)
```

### Cost Calculation

Per-MTok pricing:

| Model | Input | Output |
|-------|-------|--------|
| Opus | $15.00 | $75.00 |
| Sonnet | $3.00 | $15.00 |
| Haiku | $0.80 | $4.00 |

```python
cost = (input_tokens * input_price / 1M
      + output_tokens * output_price / 1M
      + cache_read_tokens * input_price * 0.10 / 1M
      + cache_creation_tokens * input_price * 1.25 / 1M)
```

Cache read: 10% of input price. Cache creation: 125% of input price.

### Calibration

Maps Claude's reported percentage to actual dollar costs:

```python
pct_per_dollar = rate_7d / total_cost_since_wednesday
```

This ratio converts dollar costs to rate-limit percentages. Used for:
- **Today's %**: `daily_cost_in_dollars * pct_per_dollar`
- **Daily average**: `rate_7d / elapsed_days`
- **Projected**: `daily_average * 7.0`

### Scanner

The external scanner (`~/projects/external/claude-usage`) parses JSONL transcript files and populates `~/.claude/usage.db`. The status line triggers it at most once per 5 minutes via `maybe_run_scanner()`, using a throttle file (`~/.claude-status-line/scanner-last-run`).

---

## Graphify Savings Calculations

### Data Flow

```
graphify-savings-update.py (background, every 60s)
  --> scans ~/projects for graphify-out/ directories
  --> queries usage.db for Read/Grep/Glob tool usage per session
  --> buckets sessions into pre/post by install date
  --> writes ~/.claude-status-line/graphify-savings-cache.json

graphify_savings.py (pipeline module)
  --> reads cache file (skips if >5min old)
  --> builds Row objects from cache
  --> appends to shared rows list
```

### Pre/Post Bucketing

For each project with graphify installed:
- **Pre sessions**: last turn timestamp < install date
- **Post sessions**: last turn timestamp >= install date
- **Install session**: excluded (the session that installed graphify)
- **Minimum**: 2 post sessions required to report

### Savings Formula

```python
pre_avg = sum(explore_tokens) / len(pre_sessions)
post_avg = sum(explore_tokens) / len(post_sessions)
saving_pct = (pre_avg - post_avg) / pre_avg * 100
```

Only counts Read/Grep/Glob tool tokens (the tools graphify replaces).

### Net Summary

Weighted average across all projects with data:

```python
total_pre = sum(pre_avg * n_post for each project)
total_post = sum(post_avg * n_post for each project)
net_saving_pct = (total_pre - total_post) / total_pre * 100
net_tokens = (total_pre - total_post) / total_sessions
```

---

## Version Tracking

### Architecture

Version tracking is database-backed and split across two components:

- **`version_check.py`** -- pipeline module, runs last, detects and displays version changes
- **`db.py`** -- `claude_versions` table stores the full JSON blob per version

### Database Table: `claude_versions`

In `~/claude-usage.db`:

```sql
CREATE TABLE claude_versions (
    claude_version TEXT PRIMARY KEY,
    fields TEXT NOT NULL,           -- full claude_data JSON blob (self-contained, as if from a file)
    fields_count INTEGER NOT NULL,  -- count of extracted field paths (for quick display)
    first_seen TEXT NOT NULL        -- ISO timestamp when first detected
);
```

The `fields` column stores the **complete `claude_data` JSON object** -- not just field paths. This means you can extract it directly from the DB and read it as a standalone JSON file. Field paths are derived on read via `_extract_paths()` in `db.py`.

**Note:** Conditional fields (e.g. `worktree.*` only present in worktree sessions, `session_name` absent in worktrees) mean the field snapshot reflects the session context at capture time. The same Claude version may produce slightly different field sets depending on session type.

### DB Helper Functions (in `db.py`)

- **`_extract_paths(obj, prefix="")`** -- recursively extracts dotted field paths from a JSON object
- **`_parse_version_row(row)`** -- parses a DB row, returns dict with `claude_version`, `blob` (the full JSON), `field_paths` (derived), `fields_count`, `first_seen`
- **`get_version(db, version)`** -- fetch a single version row, or None
- **`insert_version(db, version, claude_data, fields_count)`** -- insert if not exists, stores `claude_data` as pretty-printed JSON
- **`get_versions_after(db, version)`** -- all versions > given, ordered ascending

### Built-For Version

```python
# in version_check.py
BUILT_FOR_VERSION = "2.1.107"
```

This constant represents the Claude version the status line was last upgraded to use. It lives in the code and gets updated (with a commit) when the developer acknowledges new fields after a Claude upgrade.

### Detection Flow

The `version_check.py` module runs as the **last pipeline stage** (after `graphify_savings`):

1. **Throttle check**: skip if checked within 5 minutes (module-level `_last_check_time`), always check on first invocation (`_last_check_time == 0` at session start)
2. Read `claude_data["version"]`
3. Open `~/claude-usage.db`
4. **If version not in DB**: extract field paths, insert new row with the full `claude_data` blob (done once per version, ever)
5. Query all versions > `BUILT_FOR_VERSION`, ordered ascending
6. **If none**: no output (no upgrade lines shown)
7. **If any**: build one Row per version, diff each against its **predecessor** in the DB (not cumulative vs `BUILT_FOR_VERSION`)

### Display

Version rows are the **last rows** in the status line table. One row per new version in ascending order:

```
| claude 2.1.108 | 2 new fields     | worktree.foo, model.bar          |
| claude 2.1.109 | no new fields    |                                  |
```

Each row shows:
- `claude X.Y.Z` -- the version number
- `N new fields` (green) or `no new fields` (dim), with `(-N)` suffix if fields were removed
- Field names: up to 3 listed, then `+N more` if many

### Caching

Between checks, the module caches the list of version Row objects in `_cached_version_rows`. This avoids DB queries on every pipeline tick (which runs on every prompt). The cache refreshes every 5 minutes or on session start.

### Upgrade Workflow

When the user requests to upgrade the status line for a new Claude version:

1. Query all versions > `BUILT_FOR_VERSION` from the DB
2. For each version, show new fields (diff against previous version in DB)
3. Discuss with the user how to use the new fields in the status line
4. Update `BUILT_FOR_VERSION` in `version_check.py`
5. Commit the change

This cleanly separates **detection** (automatic, stored in DB on first sight) from **acknowledgment** (manual, updating the constant in code).

---

## Session Tracking

### Session State Files

```
~/.claude-status-line/sessions/{session_id}.json
```

```json
{"state": "thinking", "ts": 1776170773.6}
```

- Created/updated by external hooks
- States: `"thinking"` (Claude is working) or `"waiting"` (waiting for user)
- Cleaned up by base_info.py: removed if mtime > 1 hour

### Session Counting

```python
s_thinking = count where state == "thinking"
s_waiting = count where state == "waiting"
s_active = s_thinking + s_waiting
```

---

## Rate Limiting

Several expensive operations are rate-limited:

| Operation | Interval | Mechanism |
|-----------|----------|-----------|
| Usage scanner | 5 min | `~/.claude-status-line/scanner-last-run` mtime |
| Graphify updater | 60 sec | `~/.claude-status-line/graphify-savings.lock` mtime |
| Graphify cache staleness | 5 min | Cache file mtime check |
| Version check (proposed) | 5 min | Module-level timestamp |

All use the same pattern: check file mtime, skip if too recent, touch file before running.

---

## Input Schema

The JSON passed on stdin by Claude Code. See `~/.claude-status-line/claude_version.json` for the full field list. Key fields used by the status line:

```
version                              -- Claude Code version string
session_id                           -- unique session identifier
session_name                         -- user-assigned session name (may be absent in worktrees)
cwd                                  -- current working directory
transcript_path                      -- path to session transcript

model.id                             -- e.g. "claude-opus-4-6"
model.display_name                   -- e.g. "Claude Opus 4.6"

context_window.context_window_size   -- 200000 or 1000000
context_window.remaining_percentage  -- 0-100
context_window.used_percentage       -- 0-100
context_window.total_input_tokens    -- cumulative input
context_window.total_output_tokens   -- cumulative output

cost.total_duration_ms               -- session duration
cost.total_cost_usd                  -- API cost
cost.total_lines_added               -- lines of code added
cost.total_lines_removed             -- lines of code removed

rate_limits.five_hour.used_percentage  -- 5h rolling quota (0-100)
rate_limits.five_hour.resets_at        -- epoch seconds
rate_limits.seven_day.used_percentage  -- 7d quota (0-100)
rate_limits.seven_day.resets_at        -- epoch seconds

workspace.project_dir                -- project root
workspace.git_worktree               -- boolean

worktree.branch                      -- worktree branch name (conditional)
worktree.name                        -- worktree name (conditional)
worktree.original_branch             -- branch before entering worktree (conditional)
worktree.original_cwd                -- original cwd before worktree (conditional)
worktree.path                        -- worktree filesystem path (conditional)

output_style.name                    -- output style
exceeds_200k_tokens                  -- boolean, extended context
```

The `worktree.*` fields are only present when the session is inside a git worktree. `session_name` may be absent in worktree sessions.
