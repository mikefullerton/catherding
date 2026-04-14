#!/usr/bin/env python3
"""Summarize graphify installation and savings status.

Usage:
  graphify-status.py              summary of all projects
  graphify-status.py --saving     only projects with measurable savings
  graphify-status.py --collecting only projects still collecting data
  graphify-status.py --total      weighted net savings across all projects
"""
import argparse
import json
import os
import sys

CACHE = os.path.expanduser("~/.claude-status-line/graphify-savings-cache.json")


def fmt_tokens(n):
    if n >= 1e6: return f"{n/1e6:.1f}M"
    if n >= 1e3: return f"{n/1e3:.1f}k"
    return str(int(n))


def load():
    if not os.path.exists(CACHE):
        print(f"cache not found: {CACHE}", file=sys.stderr)
        print("run ~/.claude-status-line/scripts/graphify-savings-update.py first", file=sys.stderr)
        sys.exit(1)
    with open(CACHE) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser(description="Graphify savings status.")
    ap.add_argument("--saving", action="store_true", help="only projects with savings")
    ap.add_argument("--collecting", action="store_true", help="only collecting")
    ap.add_argument("--total", action="store_true", help="weighted net across all")
    args = ap.parse_args()

    data = load()
    rows = data.get("rows", [])

    if args.total:
        total_pre = total_post = total_sessions = 0.0
        n_projects = 0
        for r in rows:
            pre = r.get("pre_avg", 0)
            post = r.get("post_avg", 0)
            n_post = r.get("n_post", 0)
            if pre > 0 and n_post > 0:
                total_pre += pre * n_post
                total_post += post * n_post
                total_sessions += n_post
                n_projects += 1
        if total_sessions == 0 or total_pre == 0:
            print("no data yet")
            return
        net_pct = (total_pre - total_post) / total_pre * 100
        net_tok = (total_pre - total_post) / total_sessions
        print(f"{n_projects} projects, {int(total_sessions)} post sessions")
        print(f"weighted net savings: {net_pct:+.0f}% ({fmt_tokens(net_tok)}/session)")
        return

    if args.saving:
        rows = [r for r in rows if r.get("status") == "saving"]
    elif args.collecting:
        rows = [r for r in rows if r.get("status") == "collecting"]

    if not rows:
        print("(none)")
        return

    name_w = max(len(r.get("name", "")) for r in rows)
    for r in rows:
        status = r.get("status", "?")
        name = r.get("name", "?")
        label = r.get("label", "")
        detail = r.get("detail", "")
        info = r.get("info", "")
        print(f"{name:<{name_w}}  {status:<12} {label:<15} {detail:<25} {info}")


if __name__ == "__main__":
    main()
