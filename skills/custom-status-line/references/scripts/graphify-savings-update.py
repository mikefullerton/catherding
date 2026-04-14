#!/usr/bin/env python3
"""Background updater for graphify savings cache.

Scans all projects for graphify-out/, queries usage.db, writes results to
~/.claude-status-line/graphify-savings-cache.json. Designed to run as a
detached subprocess, finishing in a few seconds.
"""
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta

USAGE_DB = os.path.expanduser("~/.claude/usage.db")
PROJECTS_ROOT = os.path.expanduser("~/projects")
CACHE_FILE = os.path.expanduser("~/.claude-status-line/graphify-savings-cache.json")
EXPLORE_TOOLS = ("Read", "Grep", "Glob")
MIN_POST_SESSIONS = 1


def scan_graphify_projects():
    """Find all projects with graphify-out/. Returns [(display_name, path, install_date), ...]."""
    results = []
    for root, dirs, _files in os.walk(PROJECTS_ROOT):
        depth = root.replace(PROJECTS_ROOT, "").count(os.sep)
        if depth >= 3:
            dirs.clear()
            continue
        if "graphify-out" in dirs:
            install_date = None
            for name in ("GRAPH_REPORT.md", "graph.json"):
                p = os.path.join(root, "graphify-out", name)
                if os.path.exists(p):
                    ts = os.path.getmtime(p)
                    install_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")
                    break
            if install_date:
                display = root.replace(PROJECTS_ROOT + "/", "")
                results.append((display, root, install_date))
            dirs.remove("graphify-out")
    return results


def resolve_project_names(projects, db):
    """Map project paths to DB project_names. Returns {display_name: (set_of_db_names, install_date)}.

    A single filesystem project may have multiple DB names (e.g. 'active/temporal'
    and 'projects/temporal') from directory reorganizations. We merge all matches.
    """
    rows = db.execute("SELECT DISTINCT project_name FROM sessions WHERE project_name != ''").fetchall()
    known = {r[0] for r in rows}
    home = os.path.expanduser("~")

    result = {}
    for display_name, project_path, install_date in projects:
        rel = project_path.replace(home + "/", "")
        parts = rel.split("/")
        # Collect ALL matching DB names (not just first match)
        db_names = set()
        # The repo basename (e.g. "temporal") — match any project_name ending with it
        basename = parts[-1]
        for k in known:
            if k.endswith("/" + basename) or k == basename:
                db_names.add(k)
        if db_names:
            result[display_name] = (db_names, install_date)
    return result


def find_install_sessions(projects):
    """Read graphify-out/.install_session_id markers to get exact session IDs."""
    install_sessions = set()
    for display_name, project_path, install_date in projects:
        marker = os.path.join(project_path, "graphify-out", ".install_session_id")
        if os.path.exists(marker):
            try:
                with open(marker) as f:
                    for line in f.read().strip().splitlines():
                        line = line.strip()
                        if line:
                            install_sessions.add(line)
            except OSError:
                pass
    return install_sessions


def format_tokens(n):
    if n >= 1_000_000:
        return "{:.1f}M".format(n / 1_000_000)
    if n >= 1_000:
        return "{:.1f}k".format(n / 1_000)
    return str(int(n))


def main():
    projects = scan_graphify_projects()
    if not projects:
        _write_cache([])
        return

    if not os.path.exists(USAGE_DB):
        _write_cache([])
        return

    db = sqlite3.connect(USAGE_DB, timeout=5)

    name_map = resolve_project_names(projects, db)
    if not name_map:
        db.close()
        _write_cache([])
        return

    install_sessions = find_install_sessions(projects)

    # Collect all DB names across all projects for bulk query
    all_db_names = set()
    for display_name, (db_names, _) in name_map.items():
        all_db_names.update(db_names)
    all_db_names = list(all_db_names)
    placeholders = ",".join("?" for _ in all_db_names)

    explore_rows = db.execute("""
        SELECT s.project_name, t.session_id,
               sum(t.input_tokens + t.output_tokens) as explore_tokens,
               min(t.timestamp) as first_turn, max(t.timestamp) as last_turn
        FROM turns t
        JOIN sessions s ON t.session_id = s.session_id
        WHERE s.project_name IN ({})
          AND t.tool_name IN (?, ?, ?)
        GROUP BY s.project_name, t.session_id
    """.format(placeholders), all_db_names + list(EXPLORE_TOOLS)).fetchall()

    db.close()

    # Map DB names back to display names
    db_name_to_display = {}
    for display_name, (db_names, _) in name_map.items():
        for n in db_names:
            db_name_to_display[n] = display_name

    # Bucket into pre/post per display_name (merging all DB aliases)
    pre_by_project = defaultdict(dict)
    post_by_project = defaultdict(dict)

    for pname, session_id, explore_tokens, first_turn, last_turn in explore_rows:
        display_name = db_name_to_display.get(pname)
        if not display_name:
            continue
        _, install_date = name_map[display_name]
        if session_id in install_sessions:
            continue
        if last_turn < install_date:
            pre_by_project[display_name][session_id] = explore_tokens
        else:
            post_by_project[display_name][session_id] = explore_tokens

    # Compute results
    output = []

    def avg(m):
        vals = list(m.values())
        return sum(vals) / len(vals) if vals else 0.0

    for display_name, (db_names, install_date) in sorted(name_map.items()):
        pre = pre_by_project.get(display_name, {})
        post = post_by_project.get(display_name, {})
        n_pre = len(pre)
        n_post = len(post)

        if n_post < MIN_POST_SESSIONS:
            if n_pre > 0:
                output.append({
                    "name": display_name,
                    "status": "collecting",
                    "label": "collecting",
                    "detail": "baseline: {}".format(format_tokens(avg(pre))),
                    "info": "{} pre".format(n_pre),
                    "sort": 99,
                })
            continue

        pre_avg = avg(pre)
        post_avg = avg(post)

        if n_pre == 0:
            output.append({
                "name": display_name,
                "status": "no_baseline",
                "label": "no baseline",
                "detail": "{}".format(format_tokens(post_avg)),
                "info": "{} post".format(n_post),
                "sort": 98,
            })
            continue

        saving_pct = (pre_avg - post_avg) / pre_avg * 100 if pre_avg > 0 else 0.0

        if saving_pct > 5:
            status = "saving"
            label = "saving {:.0f}%".format(saving_pct)
            sort = -saving_pct
        elif saving_pct > -5:
            status = "neutral"
            label = "~0%"
            sort = 50
        else:
            status = "worse"
            label = "+{:.0f}%".format(abs(saving_pct))
            sort = 60 + abs(saving_pct)

        output.append({
            "name": display_name,
            "status": status,
            "label": label,
            "detail": "{} \u2192 {}".format(
                format_tokens(pre_avg), format_tokens(post_avg)
            ),
            "info": "{} pre \xb7 {} post".format(n_pre, n_post),
            "sort": sort,
            "pre_avg": pre_avg,
            "post_avg": post_avg,
            "n_post": n_post,
        })

    output.sort(key=lambda x: x["sort"])
    _write_cache(output)


def _write_cache(rows):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"ts": datetime.now().isoformat(), "rows": rows}, f)
    os.replace(tmp, CACHE_FILE)


if __name__ == "__main__":
    main()
