#!/usr/bin/env python3
"""Pipeline module: base project/git info, model stats, weekly usage."""
import json
import os
import subprocess
import time
from datetime import datetime, timedelta

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


def run(claude_data: dict, lines: list) -> list:
    """Generate 3 status lines: project/git, model/stats, weekly usage."""
    claude = claude_data

    # Extract fields — use `or` to coalesce None values to defaults
    model_name = (claude.get("model") or {}).get("display_name") or "unknown"
    rem_pct = int((claude.get("context_window") or {}).get("remaining_percentage") or 100)
    duration_ms = int((claude.get("cost") or {}).get("total_duration_ms") or 0)
    lines_added = int((claude.get("cost") or {}).get("total_lines_added") or 0)
    lines_removed = int((claude.get("cost") or {}).get("total_lines_removed") or 0)
    session_name = claude.get("session_name") or ""
    total_changes = lines_added + lines_removed
    rate_5h = float(((claude.get("rate_limits") or {}).get("five_hour") or {}).get("used_percentage") or 0)
    rate_7d = float(((claude.get("rate_limits") or {}).get("seven_day") or {}).get("used_percentage") or 0)
    session_id = claude.get("session_id") or ""

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

    # Detect worktree — prefer the field Claude provides, fall back to git
    wt_field = (claude.get("workspace") or {}).get("git_worktree")
    if wt_field is not None:
        is_worktree = bool(wt_field)
    else:
        git_dir = git_cmd("rev-parse", "--git-dir")
        is_worktree = bool(git_dir and "/worktrees/" in git_dir)

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

    ctx_size = int((claude.get("context_window") or {}).get("context_window_size") or 200000)
    exceeds_200k = bool(claude.get("exceeds_200k_tokens"))
    ctx_label = "1M" if ctx_size > 200000 else "200k"

    l2c1 = model_name
    if effort:
        l2c1 += f", {effort}"

    # YOLO indicator (appended as last column on line 2)
    yolo_col = ""
    if session_id:
        yolo_path = os.path.expanduser(f"~/.claude-yolo-sessions/{session_id}.json")
        if os.path.isfile(yolo_path):
            try:
                with open(yolo_path) as f:
                    yolo_data = json.load(f)
                needs_restart = yolo_data.get("needs_restart", False)
                if needs_restart:
                    yolo_col = f"{RED}\U0001f525 YOLO{RST} {DIM}(needs restart){RST}"
                else:
                    yolo_col = f"{RED}\U0001f525 YOLO{RST}"
            except (OSError, json.JSONDecodeError):
                yolo_col = f"{RED}\U0001f525 YOLO{RST}"

    l2c2 = duration
    l2c3 = f"{total_changes} lines changed"

    used_pct = 100 - rem_pct

    if exceeds_200k:
        l2c5 = f"{RED}{used_pct}% context (extended){RST}"
    elif ctx_size > 200000 and used_pct > 20:
        l2c5 = f"{YELLOW}{used_pct}% context{RST}"
    else:
        l2c5 = f"{used_pct}% context"

    # LINE 3
    elapsed_hours, wed_10am = get_wed_10am_elapsed_hours()
    proj = compute_projection(rate_7d, elapsed_hours)

    too_early = elapsed_hours < 6

    if too_early:
        l3c4 = f"{DIM}projected: too early{RST}"
        l3c3 = f"{DIM}daily ave: --{RST}"
    elif proj["projected"] > 100.0:
        l3c4 = f"{RED}{proj['projected']}%{RST} projected (~${proj['overage_dollars']} overage)"
        l3c3 = f"daily ave: {proj['daily_avg']:.1f}%"
    else:
        l3c4 = f"{proj['projected']}% projected"
        l3c3 = f"daily ave: {proj['daily_avg']:.1f}%"

    l3c1 = f"Weekly usage {rate_7d:.1f}%"
    l3c2 = f"day: {proj['elapsed_day']:.2f}"

    l2c4 = ctx_label

    # SESSION LINE
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

    # Column alignment
    col1_w = max(visible_len(l1c1), visible_len(l2c1), visible_len(sc1), visible_len(l3c1))
    col2_w = max(visible_len(l1c2), visible_len(l2c2), visible_len(sc2), visible_len(l3c2))
    col3_w = max(visible_len(l1c3), visible_len(l2c3), visible_len(sc3), visible_len(l3c3))
    col4_w = max(visible_len(l2c4), visible_len(sc4), visible_len(l3c4))

    lbor = f"{ORANGE}|{RST} "

    line1 = f"{lbor}{pad_right(l1c1, col1_w)}"
    if branch:
        line1 += f"{sep}{pad_right(l1c2, col2_w)}{sep}{pad_right(l1c3, col3_w)}"

    line2 = f"{lbor}{pad_right(l2c1, col1_w)}{sep}{pad_right(l2c2, col2_w)}{sep}{pad_right(l2c3, col3_w)}{sep}{pad_right(l2c4, col4_w)}{sep}{l2c5}"
    if yolo_col:
        line2 += f"  {yolo_col}"

    session_line = f"{lbor}{pad_left(sc1, col1_w)}{sep}{pad_right(sc2, col2_w)}{sep}{pad_right(sc3, col3_w)}{sep}{pad_right(sc4, col4_w)}"

    line3 = f"{lbor}{pad_left(l3c1, col1_w)}{sep}{pad_right(l3c2, col2_w)}{sep}{pad_right(l3c3, col3_w)}{sep}{l3c4}"

    # Log to SQLite (non-blocking)
    log_to_db(claude, session_id, used_pct, proj, rate_5h, rate_7d, wed_10am, elapsed_hours)

    return [line1, line2, session_line, line3]
