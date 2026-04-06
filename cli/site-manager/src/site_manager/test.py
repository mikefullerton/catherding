"""Run smoke/validation tests via the plugin's smoke-test.py script."""

import json
import subprocess
import sys
from pathlib import Path


def _find_smoke_script() -> str:
    """Locate the site-manager plugin's smoke-test.py."""
    candidates = [
        Path.home() / ".claude" / "plugins" / "cache" / "site-manager" / "skills" / "site-manager" / "references" / "smoke-test.py",
    ]
    cache_dir = Path.home() / ".claude" / "plugins" / "cache"
    if cache_dir.exists():
        for match in cache_dir.rglob("site-manager/references/smoke-test.py"):
            candidates.append(match)

    candidates.append(Path(__file__).parent.parent.parent.parent.parent / "plugins" / "site-manager" / "skills" / "site-manager" / "references" / "smoke-test.py")

    for c in candidates:
        if c.exists():
            return str(c)

    print("error: cannot find smoke-test.py from site-manager plugin", file=sys.stderr)
    print("Ensure the site-manager plugin is installed.", file=sys.stderr)
    sys.exit(1)


def _get_urls() -> dict:
    """Extract service URLs from site-manifest.json."""
    p = Path("site-manifest.json")
    if not p.exists():
        print("error: no site-manifest.json found", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(p.read_text())
    domain = manifest.get("project", {}).get("domain", "")
    backend_url = manifest.get("services", {}).get("backend", {}).get("url", "")

    if not backend_url:
        print("error: backend URL not set in manifest", file=sys.stderr)
        print("Run: site-manager deploy backend", file=sys.stderr)
        sys.exit(1)

    return {
        "base_url": backend_url.rstrip("/"),
        "main_url": f"https://{domain}",
        "admin_url": f"https://admin.{domain}",
        "dashboard_url": f"https://dashboard.{domain}",
    }


def run_smoke(output_json: bool = False) -> None:
    script = _find_smoke_script()
    urls = _get_urls()

    cmd = [
        "python3", script, "smoke",
        "--base-url", urls["base_url"],
        "--main-url", urls["main_url"],
        "--admin-url", urls["admin_url"],
        "--dashboard-url", urls["dashboard_url"],
    ]

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def run_validate(admin_email: str, admin_password: str, output_json: bool = False) -> None:
    script = _find_smoke_script()
    urls = _get_urls()

    cmd = [
        "python3", script, "validate",
        "--base-url", urls["base_url"],
        "--main-url", urls["main_url"],
        "--admin-url", urls["admin_url"],
        "--dashboard-url", urls["dashboard_url"],
        "--admin-email", admin_email,
        "--admin-password", admin_password,
    ]

    result = subprocess.run(cmd)
    sys.exit(result.returncode)
