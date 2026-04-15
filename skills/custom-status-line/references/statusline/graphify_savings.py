#!/usr/bin/env python3
"""Pipeline module: graphify savings indicator.

Reads pre-computed savings data from a cache file. The heavy DB work runs
in a background subprocess spawned at most once per minute.
"""
import json
import os
import subprocess
import sys
import time

from statusline.formatting import GREEN, DIM, ORANGE, RST, Row

CACHE_FILE = os.path.expanduser("~/.claude-status-line/graphify-savings-cache.json")
UPDATER = os.path.expanduser("~/.claude-status-line/scripts/graphify-savings-update.py")
LOCK_FILE = os.path.expanduser("~/.claude-status-line/graphify-savings.lock")
UPDATE_INTERVAL = 60  # seconds


def _maybe_trigger_update():
    # type: () -> None
    """Spawn the background updater if it hasn't run recently."""
    try:
        if os.path.exists(LOCK_FILE):
            if time.time() - os.path.getmtime(LOCK_FILE) < UPDATE_INTERVAL:
                return
        with open(LOCK_FILE, "w") as f:
            f.write(str(time.time()))
        subprocess.Popen(
            [sys.executable, UPDATER],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def _format_tokens(n):
    # type: (float) -> str
    if abs(n) >= 1_000_000:
        return "{:.1f}M".format(n / 1_000_000)
    if abs(n) >= 1_000:
        return "{:.1f}k".format(n / 1_000)
    return str(int(n))


def run(claude_data, lines, rows=None):
    # type: (dict, list, list) -> list
    """Read cached graphify savings and append Row objects to shared rows list."""
    if rows is None:
        rows = []
    _maybe_trigger_update()

    if not os.path.exists(CACHE_FILE):
        return lines

    try:
        if time.time() - os.path.getmtime(CACHE_FILE) > 300:
            return lines
        with open(CACHE_FILE) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return lines

    cache_rows = [r for r in data.get("rows", []) if r.get("status") not in ("collecting", "no_baseline")]
    if not cache_rows:
        return lines

    # Build column values for each row
    row_cols = []
    for r in cache_rows:
        status = r["status"]
        label_text = r["label"]
        detail = r.get("detail", "")
        info = r.get("info", "")

        short_name = r["name"].rsplit("/", 1)[-1]
        name = "{}{}{}".format(DIM, short_name, RST)
        if status == "saving":
            label = "{}{}{}".format(GREEN, label_text, RST)
        elif status == "worse":
            label = "{}{}{}".format(ORANGE, label_text, RST)
        else:
            label = "{}{}{}".format(DIM, label_text, RST)

        row_cols.append((name, label, detail, "{}{}{}".format(DIM, info, RST)))

    # Summary line: weighted net savings across all projects with data
    total_pre = 0.0
    total_post = 0.0
    total_sessions = 0
    n_projects = 0

    for r in cache_rows:
        pre = r.get("pre_avg", 0)
        post = r.get("post_avg", 0)
        n_post = r.get("n_post", 0)
        if pre > 0 and n_post > 0:
            total_pre += pre * n_post
            total_post += post * n_post
            total_sessions += n_post
            n_projects += 1

    if total_sessions > 0 and total_pre > 0:
        net_saving_pct = (total_pre - total_post) / total_pre * 100
        net_tokens = (total_pre - total_post) / total_sessions

        if net_saving_pct > 0:
            color = GREEN
            pct_label = "{}saving {:.0f}%{}".format(color, net_saving_pct, RST)
            token_label = "{}net: -{}{}".format(color, _format_tokens(abs(net_tokens)), RST)
        else:
            color = ORANGE
            pct_label = "{}+{:.0f}%{}".format(color, abs(net_saving_pct), RST)
            token_label = "{}net: +{}{}".format(color, _format_tokens(abs(net_tokens)), RST)

        name = "{}TOTAL{}".format(DIM, RST)
        info = "{}{} projects{}".format(DIM, n_projects, RST)
        row_cols.append((name, pct_label, token_label, info))

    if not row_cols:
        return lines

    rows.append(Row("{}graphify stats{}".format(DIM, RST), heading=True))
    for cols in row_cols:
        rows.append(Row(*cols))

    return lines
