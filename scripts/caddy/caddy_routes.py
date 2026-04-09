#!/usr/bin/env python3
"""Manage Caddy routes for local tools.

Provides a CLI and importable API for registering, removing, and listing
routes on the always-on local Caddy server (localhost:2019 admin API).

CLI usage:
    caddy_routes.py add   <path> <root_dir>          # serve a directory
    caddy_routes.py add   <path> <root_dir> --browse  # with directory listing
    caddy_routes.py remove <path>
    caddy_routes.py list
    caddy_routes.py status

Python usage:
    from caddy_routes import add_route, remove_route, list_routes, status
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Optional

ADMIN_API = "http://localhost:2019"
ROUTES_PATH = "/config/apps/http/servers/srv0/routes"


def _request(method: str, path: str, data: Optional[dict] = None):
    url = f"{ADMIN_API}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error: {e.code} from Caddy API: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: cannot reach Caddy admin API at {ADMIN_API}", file=sys.stderr)
        print(f"  Is Caddy running? Try: brew services start caddy", file=sys.stderr)
        print(f"  Detail: {e}", file=sys.stderr)
        sys.exit(1)


def _get_routes() -> list:
    result = _request("GET", ROUTES_PATH)
    return result if isinstance(result, list) else []


def _find_route_index(path_prefix: str) -> Optional[int]:
    routes = _get_routes()
    normalized = path_prefix.rstrip("/") + "/*" if not path_prefix.endswith("/*") else path_prefix
    for i, route in enumerate(routes):
        for matcher in route.get("match", []):
            if normalized in matcher.get("path", []):
                return i
    return None


def add_route(path_prefix: str, root_dir: str, browse: bool = False) -> bool:
    """Register a file_server route with Caddy.

    Args:
        path_prefix: URL path prefix, e.g. "/my-tool" (auto-appended with /*)
        root_dir: Absolute path to the directory to serve
        browse: Enable directory listing

    Returns:
        True if the route was added successfully
    """
    normalized = path_prefix.rstrip("/")
    match_path = normalized + "/*"

    # Remove existing route for same path
    existing = _find_route_index(match_path)
    if existing is not None:
        _request("DELETE", f"{ROUTES_PATH}/{existing}")

    handler: dict = {
        "handler": "file_server",
        "root": root_dir,
    }
    if browse:
        handler["browse"] = {}

    route = {
        "match": [{"path": [match_path]}],
        "handle": [
            {"handler": "rewrite", "strip_path_prefix": normalized},
            handler,
        ],
    }
    # Insert before catch-all routes: remove catch-alls, add new route, re-add catch-alls
    routes = _get_routes()
    catchall_indices = [i for i, r in enumerate(routes) if not r.get("match")]
    catchalls = [routes[i] for i in catchall_indices]
    # Delete catch-alls from end to preserve indices
    for i in sorted(catchall_indices, reverse=True):
        _request("DELETE", f"{ROUTES_PATH}/{i}")
    # Append new route, then re-append catch-alls
    _request("POST", ROUTES_PATH, route)
    for ca in catchalls:
        _request("POST", ROUTES_PATH, ca)
    print(f"Route added: http://localhost:2080{normalized}/")
    return True


def remove_route(path_prefix: str) -> bool:
    """Remove a route by its path prefix.

    Returns:
        True if a route was found and removed
    """
    normalized = path_prefix.rstrip("/") + "/*" if not path_prefix.endswith("/*") else path_prefix
    idx = _find_route_index(normalized)
    if idx is None:
        print(f"No route found matching {path_prefix}", file=sys.stderr)
        return False
    _request("DELETE", f"{ROUTES_PATH}/{idx}")
    print(f"Route removed: {path_prefix}")
    return True


def list_routes() -> list:
    """List all registered routes.

    Returns:
        List of route dicts from Caddy config
    """
    routes = _get_routes()
    if not routes:
        print("No routes configured.")
        return []

    for i, route in enumerate(routes):
        paths = []
        for m in route.get("match", []):
            paths.extend(m.get("path", []))
        roots = []
        for h in route.get("handle", []):
            if h.get("handler") == "file_server" and "root" in h:
                roots.append(h["root"])
        path_str = ", ".join(paths) if paths else "(catch-all)"
        root_str = " -> ".join(roots) if roots else ""
        print(f"  [{i}] {path_str}  {root_str}")

    return routes


def status() -> bool:
    """Check if Caddy is running and reachable.

    Returns:
        True if Caddy is responsive
    """
    try:
        url = f"{ADMIN_API}/config/"
        with urllib.request.urlopen(url) as resp:
            config = json.loads(resp.read())
            servers = config.get("apps", {}).get("http", {}).get("servers", {})
            listen = []
            for srv in servers.values():
                listen.extend(srv.get("listen", []))
            print(f"Caddy is running")
            print(f"  Admin API: {ADMIN_API}")
            print(f"  Listening: {', '.join(listen)}")
            return True
    except Exception as e:
        print(f"Caddy is not reachable: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Manage local Caddy routes")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add a file server route")
    add_p.add_argument("path", help="URL path prefix (e.g. /my-tool)")
    add_p.add_argument("root", help="Directory to serve (absolute path)")
    add_p.add_argument("--browse", action="store_true", help="Enable directory listing")

    rm_p = sub.add_parser("remove", help="Remove a route")
    rm_p.add_argument("path", help="URL path prefix to remove")

    sub.add_parser("list", help="List all routes")
    sub.add_parser("status", help="Check Caddy status")

    args = parser.parse_args()

    if args.command == "add":
        add_route(args.path, args.root, args.browse)
    elif args.command == "remove":
        remove_route(args.path)
    elif args.command == "list":
        list_routes()
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()
