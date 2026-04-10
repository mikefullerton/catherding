#!/usr/bin/env python3
"""Watch ~/.local-server/sites/ and log additions/removals.

Polls every 3 seconds, writes timestamped JSON lines to
~/.local-server/activity.log. Designed to run as a launchd daemon.
Extracts <title> and <meta description> from HTML files for rich log entries.
"""

from __future__ import annotations

import json
import re
import shutil
import time
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote

SITES_DIR = Path.home() / ".local-server" / "sites"
LOG_FILE = Path.home() / ".local-server" / "activity.log"
API_PORT = 2081
POLL_INTERVAL = 1
IGNORED = {".DS_Store", "activity.log"}

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_DESC_RE = re.compile(
    r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)


def read_metadata(name: str) -> dict:
    """Extract title and description from a site's HTML."""
    path = SITES_DIR / name
    if path.is_dir():
        path = path / "index.html"
    elif not name.endswith(".html"):
        return {}
    try:
        html = path.read_text(errors="ignore")[:8192]
    except (OSError, UnicodeDecodeError):
        return {}
    meta = {}
    m = _TITLE_RE.search(html)
    if m:
        meta["title"] = m.group(1).strip()
    m = _DESC_RE.search(html)
    if m:
        meta["description"] = m.group(1).strip()
    return meta


def current_sites() -> set:
    if not SITES_DIR.exists():
        return set()
    return {p.name for p in SITES_DIR.iterdir() if p.name not in IGNORED}


def format_duration(seconds: float) -> str:
    """Format seconds into a human-readable duration string."""
    s = int(seconds)
    if s < 60:
        return f"{s}s"
    m = s // 60
    if m < 60:
        return f"{m}m {s % 60}s"
    h = m // 60
    if h < 24:
        return f"{h}h {m % 60}m"
    d = h // 24
    return f"{d}d {h % 24}h {m % 60}m"


def log_event(action: str, name: str, extra: dict | None = None):
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "name": name,
    }
    if extra:
        entry.update(extra)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


class APIHandler(BaseHTTPRequestHandler):
    """Handles DELETE requests to remove sites."""

    def do_DELETE(self):
        name = unquote(self.path.lstrip("/"))
        if not name or "/" in name or name in IGNORED:
            self._respond(400, {"error": "invalid name"})
            return
        target = SITES_DIR / name
        if not target.exists():
            self._respond(404, {"error": "not found"})
            return
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        self._respond(200, {"deleted": name})

    def _respond(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # suppress request logs


def start_api_server():
    server = HTTPServer(("127.0.0.1", API_PORT), APIHandler)
    server.serve_forever()


def main():
    SITES_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.touch(exist_ok=True)

    # Start API server in background thread
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    # Symlink log into sites dir so Caddy serves it
    served_log = SITES_DIR / "activity.log"
    if not served_log.exists():
        served_log.symlink_to(LOG_FILE)

    known = current_sites()
    # Track install time and cached metadata per site
    install_times: dict[str, float] = {}
    cached_meta: dict[str, dict] = {}
    for name in known:
        install_times[name] = time.time()
        cached_meta[name] = read_metadata(name)

    # Log initial state with metadata
    for name in sorted(known):
        log_event("present", name, cached_meta[name])

    while True:
        time.sleep(POLL_INTERVAL)
        now = current_sites()
        for name in sorted(now - known):
            install_times[name] = time.time()
            meta = read_metadata(name)
            cached_meta[name] = meta
            log_event("installed", name, meta)
        for name in sorted(known - now):
            duration = time.time() - install_times.pop(name, time.time())
            extra = dict(cached_meta.pop(name, {}))
            extra["duration"] = format_duration(duration)
            log_event("removed", name, extra)
        known = now


if __name__ == "__main__":
    main()
