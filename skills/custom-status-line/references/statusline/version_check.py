"""Pipeline module: database-backed Claude version tracking.

Detects new Claude versions, stores field snapshots in the DB, and displays
upgrade lines for versions newer than BUILT_FOR_VERSION. Runs as the last
pipeline stage so version rows appear at the bottom of the status line.
"""
import os
import time

from statusline.formatting import YELLOW, GREEN, DIM, RST, Row
from statusline.db import get_db, get_version, insert_version, get_versions_after, _extract_paths

# The version the status line was last upgraded to use. Update this constant
# (and commit) when acknowledging new fields after a Claude upgrade.
BUILT_FOR_VERSION = "2.1.107"

DB_PATH = os.path.expanduser("~/claude-usage.db")
CHECK_INTERVAL = 300  # 5 minutes

_last_check_time = 0
_cached_version_rows = None  # cached list of Row objects between checks



def _check_version(claude_data):
    """Check for new version, insert into DB if needed, return version Rows."""
    current_version = claude_data.get("version", "")
    if not current_version:
        return []

    try:
        db = get_db(DB_PATH)
    except Exception:
        return []

    try:
        # Insert current version if not already in DB
        if not get_version(db, current_version):
            field_paths = sorted(_extract_paths(claude_data))
            insert_version(db, current_version, claude_data, len(field_paths))

        # Get all versions newer than what the status line was built for
        new_versions = get_versions_after(db, BUILT_FOR_VERSION)
        if not new_versions:
            db.close()
            return []

        # Build rows: diff each version against its predecessor
        version_rows = []
        for i, ver in enumerate(new_versions):
            if i == 0:
                # First new version: diff against BUILT_FOR_VERSION
                prev = get_version(db, BUILT_FOR_VERSION)
                prev_fields = set(prev["field_paths"]) if prev else set()
            else:
                prev_fields = set(new_versions[i - 1]["fields"])

            current_fields = set(ver["field_paths"])
            new_fields = sorted(current_fields - prev_fields)
            removed_fields = sorted(prev_fields - current_fields)

            v1 = f"claude {ver['claude_version']}"
            count = len(new_fields)
            if count > 0:
                v2 = f"{GREEN}{count} new field{'s' if count != 1 else ''}{RST}"
                # Show field names, abbreviated if many
                if count <= 3:
                    v3 = f"{DIM}{', '.join(new_fields)}{RST}"
                else:
                    v3 = f"{DIM}{', '.join(new_fields[:3])}, +{count - 3} more{RST}"
            else:
                v2 = f"{DIM}no new fields{RST}"
                v3 = ""

            if removed_fields:
                rm_count = len(removed_fields)
                v2 += f" {DIM}(-{rm_count}){RST}"

            version_rows.append(Row(v1, v2, v3))

        db.close()
        return version_rows
    except Exception:
        try:
            db.close()
        except Exception:
            pass
        return []


def run(claude_data, lines, rows=None):
    """Append version upgrade rows to the shared rows list."""
    if rows is None:
        rows = []

    global _last_check_time, _cached_version_rows

    now = time.time()
    if _last_check_time == 0 or now - _last_check_time >= CHECK_INTERVAL:
        _last_check_time = now
        _cached_version_rows = _check_version(claude_data)

    if _cached_version_rows:
        rows.extend(_cached_version_rows)

    return lines
