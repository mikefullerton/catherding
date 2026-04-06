"""Check health of all services in a site-manager project."""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path


def _check_url(url: str, timeout: int = 5) -> tuple[bool, int | None]:
    """Check if a URL responds. Returns (healthy, status_code)."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, resp.status
    except urllib.error.HTTPError as e:
        return False, e.code
    except Exception:
        return False, None


def show_status(output_json: bool = False) -> None:
    p = Path("site-manifest.json")
    if not p.exists():
        print("error: no site-manifest.json found", file=sys.stderr)
        print("Run: site-manager init", file=sys.stderr)
        sys.exit(1)

    data = json.loads(p.read_text())
    proj = data.get("project", {})
    domain = proj.get("domain", "")

    results = {}
    services = data.get("services", {})

    # Backend health check
    backend = services.get("backend", {})
    if backend.get("status") == "deployed" and backend.get("url"):
        url = backend["url"].rstrip("/")
        healthy, code = _check_url(f"{url}/api/health")
        results["backend"] = {"status": "healthy" if healthy else "unhealthy", "url": url, "http": code}
    else:
        results["backend"] = {"status": "not deployed", "url": None}

    # Frontend sites
    for name in ("main", "admin", "dashboard"):
        svc = services.get(name, {})
        if svc.get("status") == "deployed":
            if name == "main":
                url = f"https://{domain}"
            else:
                url = f"https://{name}.{domain}"
            healthy, code = _check_url(url)
            results[name] = {"status": "healthy" if healthy else "unhealthy", "url": url, "http": code}
        else:
            results[name] = {"status": "not deployed", "url": None}

    if output_json:
        print(json.dumps({"project": proj, "services": results}, indent=2))
        return

    print(f"\nProject: {proj.get('name', '?')} ({domain})")
    if proj.get("displayName"):
        print(f"Display: {proj['displayName']}")
    print()

    for name, info in results.items():
        status = info["status"]
        if status == "healthy":
            icon = "+"
        elif status == "unhealthy":
            icon = "!"
        else:
            icon = "-"
        url = info.get("url") or "not deployed"
        print(f"  [{icon}] {name:<12} {status:<14} {url}")

    # Features summary
    features = data.get("features", {})
    auth = features.get("auth", {})
    if auth:
        providers = ", ".join(auth.get("providers", []))
        seeded = "yes" if auth.get("adminSeeded") else "no"
        print(f"\n  Auth: {providers}  (admin seeded: {seeded})")

    print()
