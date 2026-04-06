"""Read, display, and validate site-manifest.json."""

import json
import re
import sys
from pathlib import Path

MANIFEST_FILE = "site-manifest.json"


def _find_manifest() -> dict:
    p = Path(MANIFEST_FILE)
    if not p.exists():
        print("error: no site-manifest.json found in current directory", file=sys.stderr)
        print("Run: site-manager init", file=sys.stderr)
        sys.exit(1)
    return json.loads(p.read_text())


def show_manifest(output_json: bool = False) -> None:
    data = _find_manifest()

    if output_json:
        print(json.dumps(data, indent=2))
        return

    proj = data.get("project", {})
    print(f"\nProject: {proj.get('name', '?')} ({proj.get('domain', '?')})")
    if proj.get("displayName"):
        print(f"Display: {proj['displayName']}")
    print(f"Version: {data.get('version', '?')}")
    print(f"Created: {str(proj.get('created', ''))[:10]}")

    print("\nServices:")
    for name, svc in data.get("services", {}).items():
        status = svc.get("status", "unknown")
        platform = svc.get("platform", "")
        url = svc.get("url", "")
        deployed = str(svc.get("lastDeployed", ""))[:10]
        print(f"  {name:<12} {status:<12} {platform:<12} {url or 'not deployed'}")
        if deployed:
            print(f"  {'':<12} last deployed: {deployed}")

    features = data.get("features", {})
    if features:
        print("\nFeatures:")
        for name, feat in features.items():
            enabled = feat.get("enabled", False)
            icon = "+" if enabled else "-"
            extras = []
            if "providers" in feat:
                extras.append(f"providers={','.join(feat['providers'])}")
            if "adminSeeded" in feat:
                extras.append(f"adminSeeded={feat['adminSeeded']}")
            if "provider" in feat:
                extras.append(f"provider={feat['provider']}")
            if "structured" in feat:
                extras.append(f"structured={feat['structured']}")
            detail = " ".join(extras)
            print(f"  [{icon}] {name:<16} {detail}")

    dns = data.get("dns", {})
    if dns:
        print("\nDNS:")
        print(f"  provider:    {dns.get('provider', 'not set')}")
        print(f"  zoneId:      {dns.get('zoneId') or 'not set'}")
        ns = dns.get("nameservers", [])
        print(f"  nameservers: {', '.join(ns) if ns else 'not set'}")
        records = dns.get("records", [])
        print(f"  records:     {len(records)}")

    print()


def validate_manifest(output_json: bool = False) -> None:
    data = _find_manifest()
    errors = []

    # version
    v = data.get("version", "")
    if not v or not re.match(r"^\d+\.\d+\.\d+", v):
        errors.append("version: missing or not semver")

    # project
    proj = data.get("project", {})
    if not proj.get("name"):
        errors.append("project.name: missing or empty")
    if not proj.get("domain"):
        errors.append("project.domain: missing or empty")
    if not proj.get("created"):
        errors.append("project.created: missing")

    # services
    for svc_name in ("backend", "main", "admin", "dashboard"):
        svc = data.get("services", {}).get(svc_name, {})
        if not svc:
            errors.append(f"services.{svc_name}: missing")
            continue
        if svc.get("status") not in ("scaffolded", "deployed", "error"):
            errors.append(f"services.{svc_name}.status: invalid '{svc.get('status')}'")
        if not svc.get("platform"):
            errors.append(f"services.{svc_name}.platform: missing")

    # features.auth
    auth = data.get("features", {}).get("auth", {})
    if not isinstance(auth.get("enabled"), bool):
        errors.append("features.auth.enabled: missing or not boolean")
    providers = auth.get("providers", [])
    if not providers:
        errors.append("features.auth.providers: empty or missing")

    if output_json:
        result = {"valid": len(errors) == 0, "errors": errors}
        print(json.dumps(result, indent=2))
        return

    if errors:
        print(f"\nManifest validation: {len(errors)} error(s)\n")
        for e in errors:
            print(f"  - {e}")
        print()
        sys.exit(1)
    else:
        print(f"\nManifest valid (v{data.get('version', '?')})\n")
