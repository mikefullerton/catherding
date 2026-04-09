"""Run post-deployment verification via the plugin's verify.py script."""

import json
import subprocess
import sys
from pathlib import Path

# The plugin's verify.py location (installed via plugin cache)
PLUGIN_VERIFY = None


def _find_verify_script() -> str:
    """Locate the site-manager plugin's verify.py."""
    candidates = [
        Path.home() / ".claude" / "plugins" / "cache" / "site-manager" / "skills" / "site-manager" / "references" / "verify.py",
    ]
    # Also check via glob in plugin cache
    cache_dir = Path.home() / ".claude" / "plugins" / "cache"
    if cache_dir.exists():
        for match in cache_dir.rglob("site-manager/references/verify.py"):
            candidates.append(match)

    # Also check local dev path
    candidates.append(Path(__file__).parent.parent.parent.parent.parent / "plugins" / "site-manager" / "skills" / "site-manager" / "references" / "verify.py")

    for c in candidates:
        if c.exists():
            return str(c)

    print("error: cannot find verify.py from site-manager plugin", file=sys.stderr)
    print("Ensure the site-manager plugin is installed.", file=sys.stderr)
    sys.exit(1)


def run_verify(output_json: bool = False) -> None:
    p = Path("site-manifest.json")
    if not p.exists():
        print("error: no site-manifest.json found", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(p.read_text())
    script = _find_verify_script()

    cmd = ["python3", script, "--manifest", "site-manifest.json"]

    # Add OAuth check if providers configured
    providers = manifest.get("features", {}).get("auth", {}).get("providers", [])
    oauth_providers = [p for p in providers if p in ("github", "google")]
    if oauth_providers:
        cmd.extend(["--check-oauth", ",".join(oauth_providers)])

    # Add domain if custom domain
    domain = manifest.get("project", {}).get("domain", "")
    if domain and ".workers.dev" not in domain:
        cmd.extend(["--domain", domain])

    result = subprocess.run(cmd)
    sys.exit(result.returncode)
