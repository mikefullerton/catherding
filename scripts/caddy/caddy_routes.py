#!/usr/bin/env python3
"""Publish and manage local sites served by Caddy at ~/www.

Tools drop content into ~/www/<name>/ and it's immediately live at
http://localhost:2080/<name>/. A root index.html auto-refreshes to
show all published sites.

CLI usage:
    caddy_routes publish <name> <file_or_dir>   # copy to ~/www/<name>/
    caddy_routes unpublish <name>                # remove ~/www/<name>/
    caddy_routes list                            # show published sites
    caddy_routes status                          # check if Caddy is running

Python usage:
    from caddy_routes import publish, unpublish, list_sites, status
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

WWW_ROOT = Path.home() / "www"
CADDY_ADMIN = "http://localhost:2019"

INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Local Sites</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
    background: #1a1a2e; color: #e0e0e0;
    display: flex; justify-content: center;
    padding: 3rem 1rem;
  }
  .container { max-width: 640px; width: 100%%; }
  h1 { font-size: 1.4rem; color: #8888cc; margin-bottom: 0.5rem; }
  .subtitle { color: #666; font-size: 0.85rem; margin-bottom: 2rem; }
  .sites { list-style: none; }
  .sites li {
    border: 1px solid #2a2a4a; border-radius: 6px;
    margin-bottom: 0.5rem; transition: border-color 0.15s;
  }
  .sites li:hover { border-color: #8888cc; }
  .sites a {
    display: block; padding: 0.8rem 1rem;
    color: #c0c0e0; text-decoration: none;
    font-size: 0.95rem;
  }
  .sites a:hover { color: #fff; }
  .meta { color: #555; font-size: 0.75rem; float: right; }
  .empty { color: #555; font-style: italic; padding: 0.8rem 0; }
</style>
</head>
<body>
<div class="container">
  <h1>Local Sites</h1>
  <p class="subtitle">~/www &middot; auto-refreshes every 5s</p>
  <ul class="sites" id="sites">
%s
  </ul>
</div>
<script>
// Site data embedded as JSON for safe DOM rebuilding
var siteData = %s;
function buildList(data) {
  var ul = document.getElementById("sites");
  while (ul.firstChild) ul.removeChild(ul.firstChild);
  if (data.length === 0) {
    var li = document.createElement("li");
    li.className = "empty";
    li.textContent = "No sites published. Use: caddy_routes publish <name> <path>";
    ul.appendChild(li);
    return;
  }
  data.forEach(function(site) {
    var li = document.createElement("li");
    var a = document.createElement("a");
    a.href = "/" + site.name + "/";
    a.textContent = site.name;
    var span = document.createElement("span");
    span.className = "meta";
    span.textContent = site.modified;
    a.appendChild(span);
    li.appendChild(a);
    ul.appendChild(li);
  });
}
function poll() {
  fetch(location.href)
    .then(function(r) { return r.text(); })
    .then(function(html) {
      var match = html.match(/var siteData = (\\[.*?\\]);/);
      if (match) {
        var newData = JSON.parse(match[1]);
        if (JSON.stringify(newData) !== JSON.stringify(siteData)) {
          siteData = newData;
          buildList(siteData);
        }
      }
    })
    .catch(function() {})
    .finally(function() { setTimeout(poll, 5000); });
}
setTimeout(poll, 5000);
</script>
</body>
</html>
"""


def _rebuild_index():
    """Regenerate ~/www/index.html with links to all published sites."""
    WWW_ROOT.mkdir(parents=True, exist_ok=True)
    sites = sorted(p for p in WWW_ROOT.iterdir() if p.is_dir())

    site_data = []
    html_items = []
    for s in sites:
        mtime = datetime.fromtimestamp(s.stat().st_mtime).strftime("%b %d %H:%M")
        site_data.append({"name": s.name, "modified": mtime})
        html_items.append(
            f'    <li><a href="/{s.name}/">{s.name}'
            f'<span class="meta">{mtime}</span></a></li>'
        )

    if html_items:
        site_list_html = "\n".join(html_items)
    else:
        site_list_html = '    <li class="empty">No sites published. Use: caddy_routes publish &lt;name&gt; &lt;path&gt;</li>'

    site_data_json = json.dumps(site_data)
    (WWW_ROOT / "index.html").write_text(INDEX_TEMPLATE % (site_list_html, site_data_json))


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
        shutil.copy2(src, dest / src.name)
        if src.name != "index.html":
            shutil.copy2(src, dest / "index.html")
    else:
        shutil.copytree(src, dest, dirs_exist_ok=True)

    _rebuild_index()
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
    _rebuild_index()
    print(f"Unpublished: {name}")
    return True


def list_sites() -> list:
    """List all published sites in ~/www.

    Returns:
        List of site directory names
    """
    sites = sorted(p.name for p in WWW_ROOT.iterdir() if p.is_dir()) if WWW_ROOT.exists() else []
    if sites:
        print("Published sites:")
        for name in sites:
            print(f"  http://localhost:2080/{name}/")
    else:
        print("No published sites.")
    return sites


def status() -> bool:
    """Check if Caddy is running and reachable.

    Returns:
        True if Caddy is responsive
    """
    try:
        with urllib.request.urlopen(f"{CADDY_ADMIN}/config/") as resp:
            config = json.loads(resp.read())
            servers = config.get("apps", {}).get("http", {}).get("servers", {})
            listen = []
            for srv in servers.values():
                listen.extend(srv.get("listen", []))
            print("Caddy is running")
            print(f"  Admin API: {CADDY_ADMIN}")
            print(f"  Listening: {', '.join(listen)}")
            print(f"  Root:      {WWW_ROOT}")
            return True
    except Exception as e:
        print(f"Caddy is not reachable: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Publish and manage local sites served by Caddy")
    sub = parser.add_subparsers(dest="command", required=True)

    pub_p = sub.add_parser("publish", help="Copy content to ~/www/<name>/")
    pub_p.add_argument("name", help="Site name (e.g. my-tool)")
    pub_p.add_argument("source", help="HTML file or directory to publish")

    unpub_p = sub.add_parser("unpublish", help="Remove ~/www/<name>/")
    unpub_p.add_argument("name", help="Site name to remove")

    sub.add_parser("list", help="Show published sites")
    sub.add_parser("status", help="Check Caddy status")

    args = parser.parse_args()

    if args.command == "publish":
        publish(args.name, args.source)
    elif args.command == "unpublish":
        unpublish(args.name)
    elif args.command == "list":
        list_sites()
    elif args.command == "status":
        status()


if __name__ == "__main__":
    main()
