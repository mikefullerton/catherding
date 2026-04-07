"""Deploy services for a site-manager project."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from site_manager import MANIFEST_PATH, LEGACY_MANIFEST_PATH


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)


def _read_manifest() -> dict:
    for path in (MANIFEST_PATH, LEGACY_MANIFEST_PATH):
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text())
    print("error: no .site/manifest.json found", file=sys.stderr)
    print("Run: site-manager init", file=sys.stderr)
    sys.exit(1)


def _save_manifest(data: dict) -> None:
    p = Path(MANIFEST_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _deploy_backend(manifest: dict) -> bool:
    print("Deploying backend (Railway)...")
    out = _run(["railway", "up", "--detach"], cwd="backend")
    if out.returncode != 0:
        print(f"  FAILED: {out.stderr.strip()}", file=sys.stderr)
        return False
    print("  Railway: deployed")

    # Get domain
    domain_out = _run(["railway", "domain"], cwd="backend")
    if domain_out.returncode == 0 and domain_out.stdout.strip():
        url = domain_out.stdout.strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        manifest["services"]["backend"]["url"] = url

    manifest["services"]["backend"]["status"] = "deployed"
    manifest["services"]["backend"]["lastDeployed"] = _now_iso()
    return True


def _deploy_site(name: str, manifest: dict) -> bool:
    site_dir = f"sites/{name}"
    if not Path(site_dir).exists():
        print(f"  {name}: directory not found, skipping")
        return False

    print(f"Deploying {name} (Wrangler)...")

    # Build first
    build = _run(["npx", "vite", "build"], cwd=site_dir)
    if build.returncode != 0:
        print(f"  {name} build FAILED: {build.stderr.strip()}", file=sys.stderr)
        return False

    # Deploy
    out = _run(["npx", "wrangler", "deploy"], cwd=site_dir)
    if out.returncode != 0:
        print(f"  {name} deploy FAILED: {out.stderr.strip()}", file=sys.stderr)
        return False

    print(f"  {name}: deployed")
    manifest["services"][name]["status"] = "deployed"
    manifest["services"][name]["lastDeployed"] = _now_iso()
    return True


def deploy_all(output_json: bool = False) -> None:
    manifest = _read_manifest()
    results = {}

    results["backend"] = _deploy_backend(manifest)
    for name in ("main", "admin", "dashboard"):
        results[name] = _deploy_site(name, manifest)

    _save_manifest(manifest)

    if output_json:
        print(json.dumps(results))
        return

    print("\nDeploy complete:")
    for name, ok in results.items():
        icon = "+" if ok else "-"
        print(f"  [{icon}] {name}")
    print()

    if not all(results.values()):
        sys.exit(1)


def deploy_single(service: str, output_json: bool = False) -> None:
    manifest = _read_manifest()

    if service == "backend":
        ok = _deploy_backend(manifest)
    elif service in ("main", "admin", "dashboard"):
        ok = _deploy_site(service, manifest)
    else:
        print(f"error: unknown service '{service}'", file=sys.stderr)
        sys.exit(1)

    _save_manifest(manifest)

    if output_json:
        print(json.dumps({"service": service, "deployed": ok}))
        return

    if ok:
        print(f"\n{service}: deployed\n")
    else:
        print(f"\n{service}: FAILED\n", file=sys.stderr)
        sys.exit(1)
