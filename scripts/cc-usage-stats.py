#!/usr/bin/env python3
"""Token/cost stats from ~/.claude/usage.db.

Usage:
  usage-stats.py --today
  usage-stats.py --week           (current Wed-Wed window)
  usage-stats.py --last-week      (previous Wed-Wed window)
  usage-stats.py --compare        (this week vs last week)
  usage-stats.py --history N      (last N weeks)
  usage-stats.py --since YYYY-MM-DD
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta

USAGE_DB = os.path.expanduser("~/.claude/usage.db")

PRICING = {
    "opus":   (15.00, 75.00),
    "sonnet": ( 3.00, 15.00),
    "haiku":  ( 0.80,  4.00),
}


def model_family(m):
    if not m: return "sonnet"
    m = m.lower()
    for f in ("opus", "sonnet", "haiku"):
        if f in m: return f
    return "sonnet"


def calc_cost(m, i, o, r, c):
    ip, op = PRICING[model_family(m)]
    return i*ip/1e6 + o*op/1e6 + r*ip*0.10/1e6 + c*ip*1.25/1e6


def fmt_tokens(n):
    if n >= 1_000_000_000: return f"{n/1e9:.2f}B"
    if n >= 1_000_000: return f"{n/1e6:.1f}M"
    if n >= 1_000: return f"{n/1e3:.1f}k"
    return str(int(n))


def wed_10am(now=None):
    now = now or datetime.now()
    dow = now.isoweekday()
    days_since_wed = (dow - 3) % 7
    if days_since_wed == 0 and now.hour < 10:
        days_since_wed = 7
    return now.replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=days_since_wed)


def window_stats(db, start, end):
    rows = db.execute("""
        SELECT model,
               sum(input_tokens), sum(output_tokens),
               sum(cache_read_tokens), sum(cache_creation_tokens)
        FROM turns WHERE timestamp >= ? AND timestamp < ?
        GROUP BY model
    """, (start.strftime("%Y-%m-%dT%H:%M:%S"),
          end.strftime("%Y-%m-%dT%H:%M:%S"))).fetchall()
    total_tok = 0
    total_cost = 0.0
    for m, i, o, r, c in rows:
        i, o, r, c = (i or 0), (o or 0), (r or 0), (c or 0)
        total_tok += i + o + r + c
        total_cost += calc_cost(m, i, o, r, c)
    return total_tok, total_cost


def main():
    ap = argparse.ArgumentParser(description="Token/cost stats.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--today", action="store_true")
    g.add_argument("--week", action="store_true")
    g.add_argument("--last-week", action="store_true")
    g.add_argument("--compare", action="store_true")
    g.add_argument("--history", type=int, metavar="N", help="last N weeks")
    g.add_argument("--since", metavar="YYYY-MM-DD")
    args = ap.parse_args()

    if not os.path.exists(USAGE_DB):
        print(f"{USAGE_DB} not found", file=sys.stderr)
        sys.exit(1)
    db = sqlite3.connect(USAGE_DB, timeout=5)

    now = datetime.now()
    wed = wed_10am(now)

    if args.today:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tok, cost = window_stats(db, start, now)
        print(f"today: {fmt_tokens(tok)} / ${cost:.2f}")

    elif args.week:
        tok, cost = window_stats(db, wed, now)
        print(f"this week ({wed:%Y-%m-%d} -> now): {fmt_tokens(tok)} / ${cost:.2f}")

    elif args.last_week:
        start = wed - timedelta(days=7)
        tok, cost = window_stats(db, start, wed)
        print(f"last week ({start:%Y-%m-%d} -> {wed:%Y-%m-%d}): {fmt_tokens(tok)} / ${cost:.2f}")

    elif args.compare:
        this_tok, this_cost = window_stats(db, wed, now)
        last_start = wed - timedelta(days=7)
        last_tok, last_cost = window_stats(db, last_start, wed)
        delta = ((this_tok - last_tok) / last_tok * 100) if last_tok else 0.0
        print(f"last: {fmt_tokens(last_tok)} / ${last_cost:.2f}")
        print(f"this: {fmt_tokens(this_tok)} / ${this_cost:.2f}")
        print(f"delta: {delta:+.0f}%")

    elif args.history:
        weeks = []
        for i in range(args.history):
            start = wed - timedelta(days=7*i)
            end = wed - timedelta(days=7*(i-1)) if i > 0 else now
            tok, cost = window_stats(db, start, end)
            if tok == 0: continue
            days = (end - start).total_seconds() / 86400
            weeks.append((start, days, tok, cost))
        weeks.reverse()  # oldest first
        print(f"{'week of':<12} {'days':>5} {'tokens':>10} {'cost':>10}")
        for start, days, tok, cost in weeks:
            print(f"{start:%Y-%m-%d}  {days:>5.1f} {fmt_tokens(tok):>10} ${cost:>9.2f}")

    elif args.since:
        start = datetime.fromisoformat(args.since)
        tok, cost = window_stats(db, start, now)
        days = (now - start).total_seconds() / 86400
        print(f"since {args.since} ({days:.1f} days): {fmt_tokens(tok)} / ${cost:.2f}")
        if days > 0:
            print(f"per day: {fmt_tokens(tok/days)} / ${cost/days:.2f}")

    db.close()


if __name__ == "__main__":
    main()
