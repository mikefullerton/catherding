#!/usr/bin/env python3
"""Watch ~/.local-server/sites/ and log additions/removals.

Polls every 3 seconds, writes timestamped JSON lines to
~/.local-server/activity.log. Designed to run as a launchd daemon.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

SITES_DIR = Path.home() / ".local-server" / "sites"
LOG_FILE = Path.home() / ".local-server" / "activity.log"
POLL_INTERVAL = 3
IGNORED = {".DS_Store", "activity.log"}


def current_sites() -> set:
    if not SITES_DIR.exists():
        return set()
    return {p.name for p in SITES_DIR.iterdir() if p.name not in IGNORED}


def log_event(action: str, name: str):
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "name": name,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    SITES_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.touch(exist_ok=True)

    # Symlink log into sites dir so Caddy serves it
    served_log = SITES_DIR / "activity.log"
    if not served_log.exists():
        served_log.symlink_to(LOG_FILE)

    known = current_sites()

    # Log initial state
    for name in sorted(known):
        log_event("present", name)

    while True:
        time.sleep(POLL_INTERVAL)
        now = current_sites()
        for name in sorted(now - known):
            log_event("added", name)
        for name in sorted(known - now):
            log_event("removed", name)
        known = now


if __name__ == "__main__":
    main()
