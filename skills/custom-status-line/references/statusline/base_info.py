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
    visible_len, pad_right, pad_left,
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

# --- Version tracker constants ---

VERSION_FILE = os.path.expanduser("~/.claude-status-line/claude_version.json")


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
    """Compute usage line columns. Returns (c1, c2, c3, c4, c5) or None if no data."""
    maybe_run_scanner()

    rate_7d = float(
        ((claude_data.get("rate_limits") or {})
         .get("seven_day") or {})
        .get("used_percentage") or 0
    )
    if rate_7d <= 0:
        return None

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

    c1 = f"weekly usage: {rate_7d:.1f}%"
    c2 = f"today's usage: {today_pct:.1f}%"
    c4 = f"{remaining_days:.1f}d left"

    if too_early:
        c3 = f"{DIM}daily usage ave: --{RST}"
        c5 = f"{DIM}too early{RST}"
    else:
        daily_avg_pct = rate_7d / elapsed_days
        projected = daily_avg_pct * 7.0
        c3 = f"daily usage ave: {daily_avg_pct:.1f}%"
        c5 = f"{RED}{projected:.1f}%{RST} projected" if projected > 100.0 else f"{projected:.1f}% projected"

    return (c1, c2, c3, c4, c5)


# --- Version tracker helpers ---

def extract_paths(obj, prefix=""):
    """Recursively extract all dotted field paths from a JSON object."""
    paths = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            paths.append(p)
            paths.extend(extract_paths(v, p))
    elif isinstance(obj, list) and obj:
        paths.extend(extract_paths(obj[0], prefix + "[]"))
    return paths


def get_version_columns(claude_data: dict) -> tuple:
    """Compute version line columns. Returns (v1, v2, v3) or None if no upgrade."""
    try:
        with open(VERSION_FILE) as f:
            info = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    current_version = claude_data.get("version", "")
    built_against = info.get("built_against", "")
    known_fields = set(info.get("fields", []))

    if not current_version or current_version == built_against:
        return None

    current_fields = set(extract_paths(claude_data))
    new_fields = sorted(current_fields - known_fields)

    v1 = "claude upgrade"
    v2 = f"{YELLOW}{current_version}{RST} (from {built_against})"
    if new_fields:
        count = len(new_fields)
        v3 = f"{GREEN}{count} new field{'s' if count != 1 else ''}{RST}"
    else:
        v3 = f"{DIM}no new fields{RST}"

    return (v1, v2, v3)


def run(claude_data: dict, lines: list) -> list:
    """Generate all status lines: path, git, model, sessions, usage, version."""
    claude = claude_data

    # Extract fields
    model_name = (claude.get("model") or {}).get("display_name") or "unknown"
    rem_pct = int((claude.get("context_window") or {}).get("remaining_percentage") or 100)
    duration_ms = int((claude.get("cost") or {}).get("total_duration_ms") or 0)
    session_name = claude.get("session_name") or ""
    rate_5h = float(((claude.get("rate_limits") or {}).get("five_hour") or {}).get("used_percentage") or 0)
    rate_7d = float(((claude.get("rate_limits") or {}).get("seven_day") or {}).get("used_percentage") or 0)
    session_id = claude.get("session_id") or ""

    duration = format_duration(duration_ms)

    # Project path relative to ~ (stable across cd)
    project_dir = (claude.get("workspace") or {}).get("project_dir") or claude.get("cwd", "")
    home = os.path.expanduser("~")
    display_path = project_dir.replace(home, "~") if project_dir.startswith(home) else project_dir

    # Git info
    branch = git_cmd("rev-parse", "--abbrev-ref", "HEAD")

    sep = " | "
    lbor = "| "
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

    # LINE 2 — git details
    gs1 = ""
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

        gs1 = "git"
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

    # LINE 3 — model (col1=session_name, col2=model, col3=duration, col4=context)
    ctx_size = int((claude.get("context_window") or {}).get("context_window_size") or 200000)
    exceeds_200k = bool(claude.get("exceeds_200k_tokens"))
    ctx_label = "1M" if ctx_size > 200000 else "200k"
    used_pct = 100 - rem_pct

    mc1 = session_name
    mc2 = model_name
    mc3 = duration

    if exceeds_200k:
        mc4 = f"{RED}{used_pct}% of {ctx_label} context (extended){RST}"
    elif ctx_size > 200000 and used_pct > 20:
        mc4 = f"{YELLOW}{used_pct}% of {ctx_label} context{RST}"
    else:
        mc4 = f"{used_pct}% of {ctx_label} context"

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

    # LINE 6 — version tracker (optional)
    version_cols = get_version_columns(claude)

    # --- Column alignment across all lines ---
    # col1 (right-aligned): git, session_name, all sessions, weekly usage, claude upgrade
    # col2 (left-aligned):  files, model, N active, today's usage, version string
    # col3 (left-aligned):  remote, duration, N thinking, daily usage ave, new fields
    # col4 (left-aligned):  main, context%, N waiting, Xd left
    col1_vals = [gs1, mc1, sc1]
    col2_vals = [gs2, mc2, sc2]
    col3_vals = [gs3, mc3, sc3]
    col4_vals = [gs4, mc4, sc4]

    if usage_cols:
        uc1, uc2, uc3, uc4, uc5 = usage_cols
        col1_vals.append(uc1)
        col2_vals.append(uc2)
        col3_vals.append(uc3)
        col4_vals.append(uc4)

    if version_cols:
        vc1, vc2, vc3 = version_cols
        col1_vals.append(vc1)
        col2_vals.append(vc2)
        col3_vals.append(vc3)

    col1_w = max(visible_len(v) for v in col1_vals if v)
    col2_w = max(visible_len(v) for v in col2_vals if v)
    col3_w = max(visible_len(v) for v in col3_vals if v)
    col4_w = max((visible_len(v) for v in col4_vals if v), default=0)

    # --- Build output ---
    result = [line1]

    # LINE 2 — git
    if branch:
        git_line = f"{lbor}{pad_left(gs1, col1_w)}{sep}{pad_right(gs2, col2_w)}{sep}{pad_right(gs3, col3_w)}"
        if gs4:
            git_line += f"{sep}{gs4}"
        result.append(git_line)

    # LINE 3 — model
    model_line = f"{lbor}{pad_left(mc1, col1_w)}{sep}{pad_right(mc2, col2_w)}{sep}{pad_right(mc3, col3_w)}{sep}{pad_right(mc4, col4_w)}"
    if yolo_col:
        model_line += f"{sep}{yolo_col}"
    result.append(model_line)

    # LINE 4 — sessions
    session_line = f"{lbor}{pad_left(sc1, col1_w)}{sep}{pad_right(sc2, col2_w)}{sep}{pad_right(sc3, col3_w)}{sep}{pad_right(sc4, col4_w)}"
    result.append(session_line)

    # LINE 5 — usage (optional)
    if usage_cols:
        usage_line = f"{lbor}{pad_left(uc1, col1_w)}{sep}{pad_right(uc2, col2_w)}{sep}{pad_right(uc3, col3_w)}{sep}{pad_right(uc4, col4_w)}{sep}{uc5}"
        result.append(usage_line)

    # LINE 6 — version (optional, only on upgrade)
    if version_cols:
        ver_line = f"{lbor}{pad_left(vc1, col1_w)}{sep}{pad_right(vc2, col2_w)}{sep}{pad_right(vc3, col3_w)}"
        result.append(ver_line)

    # Log to SQLite (non-blocking)
    elapsed_hours, wed_10am = get_wed_10am_elapsed_hours()
    proj = compute_projection(rate_7d, elapsed_hours)
    log_to_db(claude, session_id, used_pct, proj, rate_5h, rate_7d, wed_10am, elapsed_hours)

    return result
