#!/usr/bin/env python3
"""Manage Caddy routes for local tools.

Provides a CLI and importable API for registering, removing, and listing
routes on the always-on local Caddy server (localhost:2019 admin API).

CLI usage:
    caddy_routes.py publish <name> <file_or_dir>      # copy to ~/www/<name>/, immediately live
    caddy_routes.py unpublish <name>                   # remove ~/www/<name>/
    caddy_routes.py add   <path> <root_dir>            # serve a directory (dynamic route)
    caddy_routes.py add   <path> <root_dir> --browse   # with directory listing
    caddy_routes.py remove <path>                      # remove a dynamic route
    caddy_routes.py list
    caddy_routes.py status

Python usage:
    from caddy_routes import publish, unpublish, add_route, remove_route, list_routes, status
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

WWW_ROOT = Path.home() / "www"

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


def publish(name: str, source: str) -> str:
    """Copy a file or directory into ~/www/<name>/ so Caddy serves it immediately.

    Args:
        name: URL path name — content will be at http://localhost:2080/<name>/
        source: Path to an HTML file or a directory of files

    Returns:
        The URL where the content is now live
    """
    src = Path(source)
    if not src.exists():
        print(f"Error: source not found: {source}", file=sys.stderr)
        sys.exit(1)

    dest = WWW_ROOT / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    if src.is_file():
        # Single file → copy as index.html (unless it already has that name)
        target_name = src.name if src.name != "index.html" else "index.html"
        shutil.copy2(src, dest / target_name)
        if target_name != "index.html":
            shutil.copy2(src, dest / "index.html")
    else:
        # Directory → copy contents
        shutil.copytree(src, dest, dirs_exist_ok=True)

    url = f"http://localhost:2080/{name}/"
    print(f"Published: {url}")
    return url


def unpublish(name: str) -> bool:
    """Remove ~/www/<name>/ and its contents.

    Args:
        name: The name used in publish()

    Returns:
        True if the directory was found and removed
    """
    dest = WWW_ROOT / name
    if not dest.exists():
        print(f"Nothing published at {name}", file=sys.stderr)
        return False
    shutil.rmtree(dest)
    print(f"Unpublished: {name}")
    return True


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
    """List all registered routes and published sites.

    Returns:
        List of route dicts from Caddy config
    """
    # Published sites in ~/www
    published = sorted(p for p in WWW_ROOT.iterdir() if p.is_dir()) if WWW_ROOT.exists() else []
    if published:
        print("Published sites (~/www):")
        for p in published:
            print(f"  http://localhost:2080/{p.name}/")
    else:
        print("No published sites.")

    # Dynamic routes
    routes = _get_routes()
    if routes:
        print("Dynamic routes:")
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

    pub_p = sub.add_parser("publish", help="Copy content to ~/www/<name>/ for instant serving")
    pub_p.add_argument("name", help="URL path name (e.g. my-tool)")
    pub_p.add_argument("source", help="HTML file or directory to publish")

    unpub_p = sub.add_parser("unpublish", help="Remove ~/www/<name>/")
    unpub_p.add_argument("name", help="Name to unpublish")

    add_p = sub.add_parser("add", help="Add a dynamic file server route")
    add_p.add_argument("path", help="URL path prefix (e.g. /my-tool)")
    add_p.add_argument("root", help="Directory to serve (absolute path)")
    add_p.add_argument("--browse", action="store_true", help="Enable directory listing")

    rm_p = sub.add_parser("remove", help="Remove a dynamic route")
    rm_p.add_argument("path", help="URL path prefix to remove")

    sub.add_parser("list", help="List all routes and published sites")
    sub.add_parser("status", help="Check Caddy status")

    args = parser.parse_args()

    if args.command == "publish":
        publish(args.name, args.source)
    elif args.command == "unpublish":
        unpublish(args.name)
    elif args.command == "add":
        add_route(args.path, args.root, args.browse)
    elif args.command == "remove":
        remove_route(args.path)
    elif args.command == "list":
        list_routes()
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()
