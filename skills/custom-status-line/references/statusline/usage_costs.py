#!/usr/bin/env python3
"""Pipeline module: transcript-calibrated weekly usage with extended use tracking."""
import os
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timedelta

from statusline.formatting import (
    ORANGE, RED, DIM, RST,
    visible_len, pad_right, pad_left,
)

USAGE_DB = os.path.expanduser("~/.claude/usage.db")
SCANNER_DIR = os.path.expanduser("~/projects/external/claude-usage")
THROTTLE_FILE = os.path.expanduser("~/.claude-status-line/scanner-last-run")
SCAN_INTERVAL = 300  # 5 minutes

# Estimated ratio: actual extended use charges / API-equivalent cost
# Derived from: ~$200 actual charges / ~$1,300 API-equivalent post-limit usage
EXTENDED_USE_DISCOUNT = 0.15

# Per-MTok pricing (input, output) — matches claude-usage/cli.py
PRICING = {
    "opus":   (15.00, 75.00),
    "sonnet": ( 3.00, 15.00),
    "haiku":  ( 0.80,  4.00),
}


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
        import subprocess
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


def query_cost_since(db: sqlite3.Connection, since_str: str) -> float:
    """Total API-equivalent cost since a timestamp."""
    rows = db.execute("""
        SELECT model, sum(input_tokens), sum(output_tokens),
               sum(cache_read_tokens), sum(cache_creation_tokens)
        FROM turns WHERE timestamp >= ?
        GROUP BY model
    """, (since_str,)).fetchall()
    return sum(calc_cost(m, i or 0, o or 0, cr or 0, cc or 0) for m, i, o, cr, cc in rows)


def run(claude_data: dict, lines: list) -> list:
    """Append a transcript-calibrated usage line with extended use tracking."""
    maybe_run_scanner()

    rate_7d = float(
        ((claude_data.get("rate_limits") or {})
         .get("seven_day") or {})
        .get("used_percentage") or 0
    )
    if rate_7d <= 0:
        return lines

    if not os.path.exists(USAGE_DB):
        return lines

    try:
        db = sqlite3.connect(USAGE_DB, timeout=2)
    except Exception:
        return lines

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
        return lines

    if total_cost <= 0:
        return lines

    # Calibrate: Claude's percentage maps to transcript total cost
    pct_per_dollar = rate_7d / total_cost

    # Today's usage as % of weekly limit
    today_cost = daily_costs.get(today_str, 0)
    today_pct = today_cost * pct_per_dollar

    # Days elapsed in the 7-day window
    elapsed_s = (now - wed_10am).total_seconds()
    elapsed_hours = max(1, elapsed_s / 3600)
    elapsed_days = elapsed_s / 86400
    remaining_days = max(0, 7.0 - elapsed_days)

    # Too early to project reliably
    too_early = elapsed_hours < 6

    lbor = f"{ORANGE}|{RST} "
    sep = f" {ORANGE}|{RST} "

    c1 = f"Weekly usage {rate_7d:.1f}%"
    c2 = f"Today: {today_pct:.1f}%"
    c3 = f"{remaining_days:.1f} days left"

    if too_early:
        c4 = f"{DIM}daily ave: --{RST}"
        c5 = f"{DIM}projected: too early{RST}"
    else:
        daily_avg_pct = rate_7d / elapsed_days
        projected = daily_avg_pct * 7.0

        c4 = f"daily ave: {daily_avg_pct:.1f}%"

        if projected > 100.0:
            cost_per_pct = total_cost / rate_7d
            proj_overage_api = (projected - 100.0) * cost_per_pct
            proj_overage_actual = proj_overage_api * EXTENDED_USE_DISCOUNT
            c5 = f"{RED}{projected:.1f}%{RST} projected (~${proj_overage_actual:.0f} extended use)"
        else:
            c5 = f"{projected:.1f}% projected"

    # Match column widths from existing lines
    col_widths = _extract_col_widths(lines)
    if col_widths and len(col_widths) >= 4:
        c1 = pad_left(c1, col_widths[0])
        c2 = pad_right(c2, col_widths[1])
        c3 = pad_right(c3, col_widths[2])
        c4 = pad_right(c4, col_widths[3])

    lines.append(f"{lbor}{c1}{sep}{c2}{sep}{c3}{sep}{c4}{sep}{c5}")
    return lines


def _extract_col_widths(lines):
    """Extract column visible widths from existing status lines.

    Splits on the literal separator (' | ' with ANSI orange) used by
    base_info.  The first part includes the leading '| ' border, so we
    subtract 2 from its visible length to get the true column 1 width.
    """
    sep = f" {ORANGE}|{RST} "

    # Prefer line index 3 (weekly usage) or 1 (model/stats) — both 4-col
    for idx in (3, 1, 2):
        if idx >= len(lines):
            continue
        parts = lines[idx].split(sep)
        if len(parts) >= 4:
            # Part 0 includes "| " border prefix (2 visible chars)
            widths = [visible_len(parts[0]) - 2]
            widths.extend(visible_len(p) for p in parts[1:])
            return widths
    return None
