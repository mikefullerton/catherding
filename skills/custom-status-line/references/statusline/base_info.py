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
    rate_5h = float(((claude.get("rate_limits") or {}).get("five_hour") or {}).get("used_percentage") or 0)
    rate_7d = float(((claude.get("rate_limits") or {}).get("seven_day") or {}).get("used_percentage") or 0)
    session_id = claude.get("session_id") or ""

    duration = format_duration(duration_ms)

    # Project name — extract worktree name, then strip suffixes
    cwd = claude.get("cwd", "")
    worktree_name = ""
    for suffix in ["/.claude/worktrees/", "/.worktrees/"]:
        if suffix in cwd:
            worktree_name = cwd[cwd.index(suffix) + len(suffix):].split("/")[0]
            cwd = cwd[:cwd.index(suffix)]
            break
    cwd = os.path.basename(cwd) or cwd

    # Git info
    branch = git_cmd("rev-parse", "--abbrev-ref", "HEAD")

    sep = " | "

    # Detect worktree — prefer the field Claude provides, fall back to git
    wt_field = (claude.get("workspace") or {}).get("git_worktree")
    if wt_field is not None:
        is_worktree = bool(wt_field)
    else:
        git_dir = git_cmd("rev-parse", "--git-dir")
        is_worktree = bool(git_dir and "/worktrees/" in git_dir)

    # LINE 1
    l1c1 = f"{BLUE}{cwd}{RST}"

    l1c2 = ""
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

        l1c2 = f"git:({YELLOW}{branch}{RST})"

        UP = "\u2191"
        DN = "\u2193"

        def _c(n, sym):
            s = f"{sym}{n}"
            return f"{YELLOW}{s}{RST}" if n > 0 else s

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
        else:
            gs4 = ""

    # LINE 2
    ctx_size = int((claude.get("context_window") or {}).get("context_window_size") or 200000)
    exceeds_200k = bool(claude.get("exceeds_200k_tokens"))
    ctx_label = "1M" if ctx_size > 200000 else "200k"

    l2c1 = model_name

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
                    yolo_col = f"{RED}YOLO \U0001f525{RST} {DIM}(needs restart){RST}"
                else:
                    yolo_col = f"{RED}YOLO \U0001f525{RST}"
            except (OSError, json.JSONDecodeError):
                yolo_col = f"{RED}YOLO \U0001f525{RST}"

    l2c2 = duration

    used_pct = 100 - rem_pct

    if exceeds_200k:
        l2c3 = f"{RED}{used_pct}% of {ctx_label} context (extended){RST}"
    elif ctx_size > 200000 and used_pct > 20:
        l2c3 = f"{YELLOW}{used_pct}% of {ctx_label} context{RST}"
    else:
        l2c3 = f"{used_pct}% of {ctx_label} context"

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

    # Column alignment — line 1 is free-form, align lines 2+ only
    col1_w = max(visible_len(gs1), visible_len(l2c1), visible_len(sc1))
    col2_w = max(visible_len(gs2), visible_len(l2c2), visible_len(sc2))
    col3_w = max(visible_len(gs3), visible_len(l2c3), visible_len(sc3))
    col4_w = max(visible_len(gs4), visible_len(sc4))

    # Session name as col0 — prepended to all aligned lines
    if session_name:
        col0_w = visible_len(session_name)
        col0_val = pad_right(session_name, col0_w) + sep
        col0_pad = pad_right("", col0_w) + sep
    else:
        col0_val = ""
        col0_pad = ""

    lbor = "| "

    line1 = f"{l1c1}"
    if branch:
        line1 += f"{sep}{l1c2}"
    if is_worktree and worktree_name:
        line1 += f"{sep}{GREEN}worktree{RST}:({YELLOW}{worktree_name}{RST})"

    result = [line1]

    if branch:
        git_line = f"{lbor}{col0_pad}{pad_left(gs1, col1_w)}{sep}{pad_right(gs2, col2_w)}{sep}{pad_right(gs3, col3_w)}"
        if gs4:
            git_line += f"{sep}{gs4}"
        result.append(git_line)

    line2 = f"{lbor}{col0_val}{pad_left(l2c1, col1_w)}{sep}{pad_right(l2c2, col2_w)}{sep}{pad_right(l2c3, col3_w)}"
    if yolo_col:
        line2 += f"{sep}{yolo_col}"

    session_line = f"{lbor}{col0_pad}{pad_left(sc1, col1_w)}{sep}{pad_right(sc2, col2_w)}{sep}{pad_right(sc3, col3_w)}{sep}{pad_right(sc4, col4_w)}"

    result.extend([line2, session_line])

    # Log to SQLite (non-blocking)
    elapsed_hours, wed_10am = get_wed_10am_elapsed_hours()
    proj = compute_projection(rate_7d, elapsed_hours)
    log_to_db(claude, session_id, used_pct, proj, rate_5h, rate_7d, wed_10am, elapsed_hours)

    return result
