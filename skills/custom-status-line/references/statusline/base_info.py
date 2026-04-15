#!/usr/bin/env python3
"""Pipeline module: all status lines — project/git, model, sessions, usage, version."""
import json
import os
import sqlite3
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timedelta

from statusline.formatting import (
    BLUE, YELLOW, GREEN, ORANGE, RED, DIM, RST,
    Row,
)
from statusline.db import get_db, upsert_session, append_weekly_usage


# --- Usage costs constants ---

USAGE_DB = os.path.expanduser("~/.claude/usage.db")
SCANNER_DIR = os.path.expanduser("~/projects/external/claude-usage")
THROTTLE_FILE = os.path.expanduser("~/.claude-status-line/scanner-last-run")
SCAN_INTERVAL = 300  # 5 minutes

PRICING = {
    "opus":   (15.00, 75.00),
    "sonnet": ( 3.00, 15.00),
    "haiku":  ( 0.80,  4.00),
}



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


def get_wed_10am_elapsed_hours() -> tuple:
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

        cost = claude.get("cost") or {}
        ctx = claude.get("context_window") or {}
        usage = ctx.get("current_usage") or {}

        upsert_session(db,
            session_id=session_id,
            session_name=claude.get("session_name", ""),
            model_id=(claude.get("model") or {}).get("id") or "unknown",
            model_display=(claude.get("model") or {}).get("display_name") or "unknown",
            claude_version=claude.get("version", ""),
            cwd=claude.get("cwd", ""),
            project_dir=(claude.get("workspace") or {}).get("project_dir") or "",
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
            five_hour_resets_at=((claude.get("rate_limits") or {}).get("five_hour") or {}).get("resets_at") or 0,
            seven_day_resets_at=((claude.get("rate_limits") or {}).get("seven_day") or {}).get("resets_at") or 0,
            projected_pct=projection["projected"],
        )
        db.close()
    except Exception:
        pass  # don't let logging failures break the status line


# --- Usage costs helpers ---

def model_family(model_id: str) -> str:
    if not model_id:
        return "sonnet"
    m = model_id.lower()
    for fam in ("opus", "sonnet", "haiku"):
        if fam in m:
            return fam
    return "sonnet"


def calc_cost(model_id: str, inp: int, out: int, cr: int, cc: int) -> float:
    ip, op = PRICING[model_family(model_id)]
    return (
        inp * ip / 1_000_000
        + out * op / 1_000_000
        + cr * ip * 0.10 / 1_000_000
        + cc * ip * 1.25 / 1_000_000
    )


def maybe_run_scanner():
    try:
        if os.path.exists(THROTTLE_FILE):
            if time.time() - os.path.getmtime(THROTTLE_FILE) < SCAN_INTERVAL:
                return
        if not os.path.isfile(os.path.join(SCANNER_DIR, "scanner.py")):
            return
        with open(THROTTLE_FILE, "w") as f:
            f.write(str(time.time()))
        subprocess.run(
            ["python3", os.path.join(SCANNER_DIR, "scanner.py")],
            capture_output=True, timeout=30,
        )
    except Exception:
        pass


def get_wed_10am() -> datetime:
    now = datetime.now()
    dow = now.isoweekday()
    days_since_wed = (dow - 3) % 7
    if days_since_wed == 0 and now.hour < 10:
        days_since_wed = 7
    return now.replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=days_since_wed)


def query_week_stats(db: sqlite3.Connection, start_str: str, end_str: str) -> tuple:
    """Return (total_cost, total_tokens) for turns in [start_str, end_str)."""
    rows = db.execute("""
        SELECT model,
               sum(input_tokens), sum(output_tokens),
               sum(cache_read_tokens), sum(cache_creation_tokens)
        FROM turns WHERE timestamp >= ? AND timestamp < ?
        GROUP BY model
    """, (start_str, end_str)).fetchall()

    total_cost = 0.0
    total_tokens = 0
    for model, inp, out, cr, cc in rows:
        i, o, r, c = (inp or 0), (out or 0), (cr or 0), (cc or 0)
        total_cost += calc_cost(model, i, o, r, c)
        total_tokens += i + o + r + c
    return total_cost, total_tokens


def format_tokens(n: int) -> str:
    """Format token count as 1.2M, 45.3k, or 123."""
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(int(n))


def get_week_comparison_rows(wed_10am: datetime, now: datetime):
    """Return list of Row objects comparing this week to last week."""
    if not os.path.exists(USAGE_DB):
        return []
    try:
        db = sqlite3.connect(USAGE_DB, timeout=2)
    except Exception:
        return []

    try:
        last_start = wed_10am - timedelta(days=7)
        last_start_str = last_start.strftime("%Y-%m-%dT%H:%M:%S")
        wed_str = wed_10am.strftime("%Y-%m-%dT%H:%M:%S")
        now_str = now.strftime("%Y-%m-%dT%H:%M:%S")

        last_cost, last_tokens = query_week_stats(db, last_start_str, wed_str)
        this_cost, this_tokens = query_week_stats(db, wed_str, now_str)
        db.close()
    except Exception:
        try:
            db.close()
        except Exception:
            pass
        return []

    if last_tokens == 0 and this_tokens == 0:
        return []

    # Percentage delta on tokens
    if last_tokens > 0:
        delta_pct = (this_tokens - last_tokens) / last_tokens * 100
    else:
        delta_pct = 0.0

    if delta_pct < 0:
        delta_str = f"{GREEN}{delta_pct:.0f}%{RST}"
    else:
        delta_str = f"{ORANGE}+{delta_pct:.0f}%{RST}"

    last_tok = format_tokens(last_tokens)
    this_tok = format_tokens(this_tokens)
    last_cost_s = f"${last_cost:.2f}"
    this_cost_s = f"${this_cost:.2f}"

    from statusline.formatting import Row

    return [Row(
        "usage last week",
        f"{last_tok} / {last_cost_s}",
        f"this wk: {this_tok} / {this_cost_s}",
        delta_str,
    )]


def query_daily_costs(db: sqlite3.Connection, since_str: str) -> dict:
    """Return {date_str: dollar_cost} for each day since the given timestamp."""
    rows = db.execute("""
        SELECT substr(timestamp, 1, 10) as day, model,
               sum(input_tokens), sum(output_tokens),
               sum(cache_read_tokens), sum(cache_creation_tokens)
        FROM turns WHERE timestamp >= ?
        GROUP BY day, model
    """, (since_str,)).fetchall()

    daily = defaultdict(float)
    for day, model, inp, out, cr, cc in rows:
        daily[day] += calc_cost(model, inp or 0, out or 0, cr or 0, cc or 0)
    return dict(daily)


def get_usage_columns(claude_data: dict) -> tuple:
    """Compute usage line columns. Returns (c1, c2, c3, c4, c5, c6) or None if no data."""
    maybe_run_scanner()

    rate_7d = float(
        ((claude_data.get("rate_limits") or {})
         .get("seven_day") or {})
        .get("used_percentage") or 0
    )
    if rate_7d <= 0:
        return None

    rate_5h = float(
        ((claude_data.get("rate_limits") or {})
         .get("five_hour") or {})
        .get("used_percentage") or 0
    )

    if not os.path.exists(USAGE_DB):
        return None

    try:
        db = sqlite3.connect(USAGE_DB, timeout=2)
    except Exception:
        return None

    try:
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        wed_10am = get_wed_10am()
        wed_str = wed_10am.strftime("%Y-%m-%dT%H:%M:%S")

        daily_costs = query_daily_costs(db, wed_str)
        total_cost = sum(daily_costs.values())

        db.close()
    except Exception:
        try:
            db.close()
        except Exception:
            pass
        return None

    if total_cost <= 0:
        return None

    pct_per_dollar = rate_7d / total_cost

    today_cost = daily_costs.get(today_str, 0)
    today_pct = today_cost * pct_per_dollar

    elapsed_s = (now - wed_10am).total_seconds()
    elapsed_hours = max(1, elapsed_s / 3600)
    elapsed_days = elapsed_s / 86400
    remaining_days = max(0, 7.0 - elapsed_days)

    too_early = elapsed_hours < 6

    def _quota_color(pct: float) -> str:
        if pct >= 100.0:
            return RED
        if pct >= 95.0:
            return YELLOW
        return ""

    wk_col = _quota_color(rate_7d)
    c1 = f"weekly: {wk_col}{rate_7d:.1f}%{RST}" if wk_col else f"weekly: {rate_7d:.1f}%"
    resets_at = int(
        ((claude_data.get("rate_limits") or {})
         .get("five_hour") or {})
        .get("resets_at") or 0
    )
    fh_col = _quota_color(rate_5h)
    c2 = f"5h: {fh_col}{rate_5h:.1f}%{RST}" if fh_col else f"5h: {rate_5h:.1f}%"
    c7 = ""
    if resets_at > 0:
        remaining_s = resets_at - now.timestamp()
        if remaining_s > 0:
            remaining_m = int(remaining_s // 60)
            h, m = divmod(remaining_m, 60)
            c7 = f"{h}h {m:02d}m left" if h > 0 else f"{m}m left"
    c3 = f"today: {today_pct:.1f}%"
    remaining_minutes = max(0, int(remaining_days * 24 * 60))
    rd, rem = divmod(remaining_minutes, 24 * 60)
    rh, rm = divmod(rem, 60)
    if rd > 0:
        c5 = f"{rd}d {rh}h {rm:02d}m left"
    elif rh > 0:
        c5 = f"{rh}h {rm:02d}m left"
    else:
        c5 = f"{rm}m left"

    if too_early:
        c4 = f"{DIM}daily ave: --{RST}"
        c6 = f"{DIM}too early{RST}"
    else:
        daily_avg_pct = rate_7d / elapsed_days
        projected = daily_avg_pct * 7.0
        c4 = f"daily ave: {daily_avg_pct:.1f}%"
        c6 = f"{RED}{projected:.1f}%{RST} projected" if projected > 100.0 else f"{projected:.1f}% projected"

    return (c1, c2, c3, c4, c5, c6, c7)


# --- Version tracker helpers ---

def run(claude_data: dict, lines: list, rows: list = None) -> list:
    """Generate all status lines: path, git, model, sessions, usage, version.

    When called with a shared `rows` list (from the dispatcher), appends Row
    objects for centralized formatting. When called standalone (rows=None),
    formats and appends rows to lines directly.
    """
    _standalone = rows is None
    if _standalone:
        rows = []
    claude = claude_data

    # Extract fields
    model_name = (claude.get("model") or {}).get("display_name") or "unknown"
    # Distinguish "genuinely full context" from "field missing/null" so the UI
    # doesn't silently claim 0% used when Claude just didn't report the value.
    _cw = claude.get("context_window") or {}
    _raw_rem = _cw.get("remaining_percentage")
    rem_pct_known = isinstance(_raw_rem, (int, float))
    rem_pct = int(_raw_rem) if rem_pct_known else 100
    duration_ms = int((claude.get("cost") or {}).get("total_duration_ms") or 0)
    rate_5h = float(((claude.get("rate_limits") or {}).get("five_hour") or {}).get("used_percentage") or 0)
    rate_7d = float(((claude.get("rate_limits") or {}).get("seven_day") or {}).get("used_percentage") or 0)
    session_id = claude.get("session_id") or ""

    duration = format_duration(duration_ms)

    # Project path relative to ~ (use worktree.original_cwd when in a worktree)
    wt = claude.get("worktree") or {}
    project_dir = wt.get("original_cwd") or (claude.get("workspace") or {}).get("project_dir") or claude.get("cwd", "")
    home = os.path.expanduser("~")
    display_path = project_dir.replace(home, "~") if project_dir.startswith(home) else project_dir

    # Git info
    branch = git_cmd("rev-parse", "--abbrev-ref", "HEAD")

    UP = "\u2191"
    DN = "\u2193"

    def _c(n, sym):
        s = f"{sym}{n}"
        return f"{YELLOW}{s}{RST}" if n > 0 else s

    # LINE 1 — <path relative to ~> on <git branch>
    if branch:
        line1 = f"{BLUE}{display_path}{RST} on {YELLOW}{branch}{RST}"
    else:
        line1 = f"{BLUE}{display_path}{RST}"

    # LINE 2 — git (heading row) + git details row
    gs2 = ""
    gs3 = ""
    gs4 = ""
    if branch:
        porcelain = git_cmd("status", "--porcelain")
        added = 0
        deleted = 0
        changed = 0
        if porcelain:
            for line in porcelain.splitlines():
                code = line[:2]
                if code == "??":
                    added += 1
                elif "D" in code:
                    deleted += 1
                else:
                    changed += 1

        gs2 = f"files: {_c(changed, '~')} {_c(added, '+')} {_c(deleted, '-')}"

        has_remote = bool(git_cmd("rev-parse", "--verify", f"origin/{branch}"))
        if has_remote:
            ahead_remote = git_cmd("rev-list", "--count", f"origin/{branch}..HEAD")
            ahead_remote = int(ahead_remote) if ahead_remote else 0
            behind_remote = git_cmd("rev-list", "--count", f"HEAD..origin/{branch}")
            behind_remote = int(behind_remote) if behind_remote else 0
            if ahead_remote == 0 and behind_remote == 0:
                gs3 = f"remote: {DIM}in sync{RST}"
            else:
                gs3 = f"remote: {_c(ahead_remote, UP)}{_c(behind_remote, DN)}"
        else:
            gs3 = f"remote: {DIM}none{RST}"

        if branch not in ("main", "master"):
            commits = git_cmd("rev-list", "--count", "main..HEAD")
            commits = int(commits) if commits else 0
            behind_main = git_cmd("rev-list", "--count", "HEAD..main")
            behind_main = int(behind_main) if behind_main else 0
            if commits == 0 and behind_main == 0:
                gs4 = f"main: {DIM}in sync{RST}"
            else:
                gs4 = f"main: {_c(commits, UP)}{_c(behind_main, DN)}"

    # LINE 3 — model (col1=model, col2=duration, col3=context)
    ctx_size = int(_cw.get("context_window_size") or 200000)
    # `(extended)` should only render when the window really is the 1M extended
    # one. A 200k window with exceeds_200k_tokens=true is internally
    # contradictory — treat the flag as meaningful only on >200k windows.
    exceeds_200k = bool(claude.get("exceeds_200k_tokens")) and ctx_size > 200000
    ctx_label = "1M" if ctx_size > 200000 else "200k"
    used_pct = 100 - rem_pct
    pct_display = f"{used_pct}%" if rem_pct_known else "?%"

    mc1 = f"{GREEN}{model_name}{RST}" if "opus" in model_name.lower() else f"{RED}{model_name}{RST}"
    mc2 = duration

    # Threshold colors mirror the quota rows: RED at >=95% used (urgent), YELLOW
    # at >=80%. The extended-1M indicator keeps its own red styling on top.
    if not rem_pct_known:
        ctx_color = ""
    elif used_pct >= 95:
        ctx_color = RED
    elif used_pct >= 80:
        ctx_color = YELLOW
    elif ctx_size > 200000 and used_pct > 20:
        ctx_color = YELLOW  # preserve old "you're past 200k on an extended window" hint
    else:
        ctx_color = ""

    if exceeds_200k:
        mc3 = f"{RED}{pct_display} / {ctx_label} ctx (extended){RST}"
    elif ctx_color:
        mc3 = f"{ctx_color}{pct_display} / {ctx_label} ctx{RST}"
    else:
        mc3 = f"{pct_display} / {ctx_label} ctx"

    # YOLO indicator (trailing on line 3)
    yolo_col = ""
    if session_id:
        yolo_path = os.path.expanduser(f"~/.claude-yolo-sessions/{session_id}.json")
        if os.path.isfile(yolo_path):
            try:
                with open(yolo_path) as f:
                    yolo_data = json.load(f)
                needs_restart = yolo_data.get("needs_restart", False)
                if needs_restart:
                    yolo_col = f"{RED}YOLO \U0001f525{RST} {DIM}(needs restart){RST}"
                else:
                    yolo_col = f"{RED}YOLO \U0001f525{RST}"
            except (OSError, json.JSONDecodeError):
                yolo_col = f"{RED}YOLO \U0001f525{RST}"

    # LINE 4 — sessions
    sessions_dir = os.path.expanduser("~/.claude-status-line/sessions")
    s_thinking = 0
    s_waiting = 0
    if os.path.isdir(sessions_dir):
        now = time.time()
        for fname in os.listdir(sessions_dir):
            if not fname.endswith(".json"):
                continue
            spath = os.path.join(sessions_dir, fname)
            try:
                if now - os.path.getmtime(spath) > 3600:
                    os.remove(spath)
                    continue
                with open(spath) as f:
                    sdata = json.load(f)
                if sdata.get("state") == "thinking":
                    s_thinking += 1
                else:
                    s_waiting += 1
            except (OSError, json.JSONDecodeError):
                continue
    s_active = s_thinking + s_waiting
    sc1 = f"{DIM}all sessions{RST}"
    sc2 = f"{s_active} active"
    sc3 = f"{s_thinking} thinking"
    sc4 = f"{s_waiting} waiting"

    # LINE 5 — usage costs (optional)
    usage_cols = get_usage_columns(claude)

    # --- Append rows to shared list ---
    if branch:
        # "git" is a section label — standalone heading (no grid alignment).
        rows.append(Row(f"{DIM}git{RST}", heading=True))
        # Detail row participates in the shared column grid one column to the
        # left of where it used to sit: the old empty col 0 indent is gone,
        # so files/remote/main now occupy col 0/1/2 and align with the model,
        # sessions, usage, graphify-savings, and version-check rows below.
        #
        # Repo-hygiene warning (stale/merged branches, done worktrees) is
        # attached as free-form trailing text so it sits at the end of the
        # git line without widening any grid column.
        try:
            from statusline.repo_cleanup import compute_warning_text
            warning_text = compute_warning_text()
        except Exception:
            warning_text = ""
        rows.append(Row(gs2, gs3, gs4, trailing=warning_text))

    model_row = Row(mc1, mc2, mc3)
    if yolo_col:
        model_row.columns.append(yolo_col)
    rows.append(model_row)

    rows.append(Row(sc1, sc2, sc3, sc4))

    # Week-over-week comparison (show 3 variants so user can pick)
    wed_10am = get_wed_10am()
    week_rows = get_week_comparison_rows(wed_10am, datetime.now())

    # "Usage" section: rate-limit rows (if rate_limits present) and/or the
    # week-over-week comparison row. Heading sits above whichever rows exist
    # so the weekly-spend context is always visually grouped.
    if usage_cols or week_rows:
        rows.append(Row(f"{DIM}Usage{RST}", heading=True))
    if usage_cols:
        uc1, uc2, uc3, uc4, uc5, uc6, uc7 = usage_cols
        rows.append(Row(uc1, uc4, uc5, uc6))
        rows.append(Row(uc3, uc2, uc7))
    for r in week_rows:
        rows.append(r)

    # --- Non-columnar output ---
    result = [line1]

    # Standalone mode: format and render rows inline
    if _standalone:
        from statusline.formatting import compute_column_widths, format_rows
        widths = compute_column_widths(rows)
        format_rows(rows, widths)
        for row in rows:
            result.append(row.render())

    # Log to SQLite (non-blocking)
    elapsed_hours, wed_10am = get_wed_10am_elapsed_hours()
    proj = compute_projection(rate_7d, elapsed_hours)
    log_to_db(claude, session_id, used_pct, proj, rate_5h, rate_7d, wed_10am, elapsed_hours)

    return result
