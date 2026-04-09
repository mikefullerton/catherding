"""Unified verification runner.

Runs all verification suites by default, or individual suites via flags.
Writes issues to .site/issues.json for consumption by `site-manager repair`.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from site_manager import __version__
from site_manager.check import CheckRecorder, BOLD, RESET, YELLOW
from site_manager.dns_check import DNSChecker, count_checks as dns_count
from site_manager.e2e import E2ERunner, count_checks as e2e_count


SITE_DIR = ".site"
MANIFEST_FILE = f"{SITE_DIR}/manifest.json"
ISSUES_FILE = f"{SITE_DIR}/issues.json"


def _count_manifest_checks(manifest: dict) -> int:
    total = 4 + 4
    for site_name in ("main", "admin", "dashboard"):
        total += 1
        if site_name != "dashboard":
            total += 1
    return total


def _count_smoke_checks() -> int:
    return 10


def _run_manifest_checks(manifest: dict, rec: CheckRecorder):
    """Manifest integrity, API health, and frontend HTTP checks."""
    import urllib.request
    import urllib.error

    project = manifest.get("project", {})
    services = manifest.get("services", {})
    display_name = project.get("displayName", "")
    backend_url = (services.get("backend") or {}).get("url", "").rstrip("/")
    domain = project.get("domain", "")

    rec.section("Manifest Integrity")

    missing = []
    for f in ("name", "domain", "created"):
        if not project.get(f):
            missing.append(f"project.{f}")
    for svc_name in ("backend", "main", "admin", "dashboard"):
        svc = services.get(svc_name) or {}
        if not svc.get("status"):
            missing.append(f"services.{svc_name}.status")
        if not svc.get("platform"):
            missing.append(f"services.{svc_name}.platform")
    rec.record("Required fields present", not missing, suite="manifest",
               detail=("Missing: " + ", ".join(missing)) if missing else "")

    rec.record("Display name set", bool(display_name), suite="manifest",
               detail="" if display_name else "project.displayName is missing")

    bad = []
    for svc_name in ("backend", "main", "admin", "dashboard"):
        svc = services.get(svc_name) or {}
        if svc.get("status") == "deployed" and not (svc.get("url") or svc.get("domain")):
            bad.append(svc_name)
    rec.record("Service URLs for deployed services", not bad, suite="manifest",
               detail=("Missing URLs: " + ", ".join(bad)) if bad else "")

    providers = manifest.get("features", {}).get("auth", {}).get("providers", [])
    rec.record("Auth providers configured", bool(providers), suite="manifest",
               detail="" if providers else "features.auth.providers is empty or missing")

    rec.section("API Health")

    def _get(url, timeout=10):
        req = urllib.request.Request(url, headers={"User-Agent": "site-manager-verify/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as e:
            return 0, str(e)

    def _options(url):
        req = urllib.request.Request(url, method="OPTIONS",
                                     headers={"User-Agent": "site-manager-verify/1.0",
                                              "Origin": "https://example.com"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, dict(resp.headers)
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers)
        except Exception:
            return 0, {}

    if backend_url:
        status, body = _get(f"{backend_url}/api/health")
        try:
            parsed = json.loads(body)
            ok = status == 200 and parsed.get("status") == "ok"
        except (json.JSONDecodeError, ValueError):
            ok = False
        rec.record("Backend /api/health", ok, suite="manifest",
                   detail="" if ok else f"Expected 200 {{status:ok}}, got {status}")

        status, body = _get(f"{backend_url}/api/health/ready")
        rec.record("Backend /api/health/ready", status == 200, suite="manifest",
                   detail="" if status == 200 else f"Expected 200, got {status}")

        status, headers = _options(f"{backend_url}/api/health")
        has_cors = any("access-control" in k.lower() for k in headers)
        rec.record("CORS headers", has_cors, suite="manifest",
                   detail="" if has_cors else "No Access-Control-* headers")

        status, body = _get(f"{backend_url}/api/nonexistent")
        try:
            parsed = json.loads(body)
            ok = status == 404 and "type" in parsed and "title" in parsed
        except (json.JSONDecodeError, ValueError):
            ok = False
        rec.record("Error format (RFC 9457)", ok, suite="manifest",
                   detail="" if ok else f"Expected 404 + Problem Details, got {status}")
    else:
        for name in ("Backend /api/health", "Backend /api/health/ready",
                     "CORS headers", "Error format (RFC 9457)"):
            rec.skip(name, "No backend URL in manifest", suite="manifest")

    rec.section("Frontend Sites")

    for site_name in ("main", "admin", "dashboard"):
        if domain:
            site_url = f"https://{domain}" if site_name == "main" else f"https://{site_name}.{domain}"
        else:
            site_url = ""

        svc = services.get(site_name) or {}
        if not domain:
            rec.skip(f"{site_name} responds (HTTP)", "No domain in manifest", suite="manifest")
            if site_name != "dashboard":
                rec.skip(f"{site_name} has correct content-type", "No domain", suite="manifest")
            continue

        if svc.get("status") != "deployed":
            rec.skip(f"{site_name} responds (HTTP)", "Not deployed", suite="manifest")
            if site_name != "dashboard":
                rec.skip(f"{site_name} has correct content-type", "Not deployed", suite="manifest")
            continue

        status, body = _get(site_url)
        rec.record(f"{site_name} responds (HTTP)", status == 200, suite="manifest",
                   detail="" if status == 200 else f"Expected 200, got {status}")

        if site_name != "dashboard":
            has_html = "<!doctype html" in body.lower() or "<html" in body.lower()
            rec.record(f"{site_name} has correct content-type", has_html, suite="manifest",
                       detail="" if has_html else "Response doesn't look like HTML")


def _run_smoke_checks(manifest: dict, rec: CheckRecorder):
    """Run functional smoke tests via the plugin's smoke-test.py."""
    from site_manager.test import _find_smoke_script, _get_urls

    rec.section("Smoke Tests")

    try:
        script = _find_smoke_script()
    except SystemExit:
        for i in range(10):
            rec.skip(f"smoke test {i+1}", "smoke-test.py not found", suite="smoke")
        return

    try:
        urls = _get_urls()
    except SystemExit:
        for i in range(10):
            rec.skip(f"smoke test {i+1}", "Could not read URLs from manifest", suite="smoke")
        return

    cmd = [
        "python3", script, "smoke",
        "--base-url", urls["base_url"],
        "--main-url", urls["main_url"],
        "--admin-url", urls["admin_url"],
        "--dashboard-url", urls["dashboard_url"],
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if "PASS" in line:
            name = line.split("PASS")[-1].strip()
            rec.record(name or "smoke check", True, suite="smoke")
        elif "FAIL" in line:
            name = line.split("FAIL")[-1].strip()
            rec.record(name or "smoke check", False, suite="smoke")
        elif "SKIP" in line:
            name = line.split("SKIP")[-1].strip()
            rec.skip(name or "smoke check", suite="smoke")


def _write_issues(rec: CheckRecorder):
    """Write failed/warning checks to .site/issues.json for repair."""
    site_dir = Path(SITE_DIR)
    site_dir.mkdir(exist_ok=True)

    issues = []
    for r in rec.results:
        if r.passed and not r.warning:
            continue
        issues.append({
            "check": r.name,
            "suite": r.suite,
            "severity": "warning" if r.warning else "error",
            "detail": r.detail,
        })

    data = {
        "tool_version": __version__,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "total_checks": len(rec.results),
        "passed": sum(1 for r in rec.results if r.passed),
        "failed": sum(1 for r in rec.results if not r.passed and not r.warning),
        "warnings": sum(1 for r in rec.results if not r.passed and r.warning),
        "issues": issues,
    }

    Path(ISSUES_FILE).write_text(json.dumps(data, indent=2) + "\n")


def _check_tool_version(manifest: dict):
    """Note if site-manager has been updated since the project was last scaffolded."""
    last_tool_version = manifest.get("_site_manager_version")
    if not last_tool_version:
        return

    if last_tool_version != __version__:
        print(f"\n  {YELLOW}Note:{RESET} Project was last updated with site-manager {last_tool_version}.")
        print(f"  You are now running {BOLD}{__version__}{RESET}.")
        print(f"  Run {BOLD}site-manager update{RESET} to apply new templates or fixes.")


def run_verify(
    run_manifest: bool = True,
    run_dns: bool = True,
    run_e2e: bool = True,
    run_smoke: bool = True,
    output_json: bool = False,
) -> None:
    p = Path(MANIFEST_FILE)
    if not p.exists():
        # Also check legacy location
        legacy = Path("site-manifest.json")
        if legacy.exists():
            print(f"Migrating site-manifest.json → {MANIFEST_FILE}")
            site_dir = Path(SITE_DIR)
            site_dir.mkdir(exist_ok=True)
            legacy.rename(p)
        else:
            print("error: no .site/manifest.json found", file=sys.stderr)
            print("Run: site-manager init", file=sys.stderr)
            sys.exit(1)

    manifest = json.loads(p.read_text())
    project = manifest.get("project", {})

    total = 0
    if run_manifest:
        total += _count_manifest_checks(manifest)
    if run_dns:
        total += dns_count(manifest)
    if run_e2e:
        total += e2e_count(manifest)
    if run_smoke:
        total += _count_smoke_checks()

    if total == 0:
        print("No checks to run.")
        sys.exit(0)

    suites_running = []
    if run_manifest:
        suites_running.append("manifest")
    if run_dns:
        suites_running.append("dns")
    if run_e2e:
        suites_running.append("e2e")
    if run_smoke:
        suites_running.append("smoke")

    title = "site-manager verify" if len(suites_running) == 4 else f"verify --{'+'.join(suites_running)}"
    rec = CheckRecorder(total, title=title)

    print(f"\n{BOLD}=== SITE MANAGER VERIFY ==={RESET}")
    print(f"Project: {project.get('name', '?')} ({project.get('domain', '?')})")
    print(f"Suites:  {', '.join(suites_running)}")
    print(f"Total checks: {total}")

    if run_manifest:
        _run_manifest_checks(manifest, rec)
    if run_dns:
        DNSChecker(manifest, rec).run()
    if run_e2e:
        E2ERunner(manifest, rec).run()
    if run_smoke:
        _run_smoke_checks(manifest, rec)

    # Write issues for repair
    _write_issues(rec)

    if output_json:
        print(rec.to_json())
    else:
        success = rec.summary()
        _check_tool_version(manifest)

        issues_path = Path(ISSUES_FILE)
        issues_data = json.loads(issues_path.read_text())
        issue_count = len(issues_data.get("issues", []))
        if issue_count > 0:
            print(f"\n  {issue_count} issue(s) written to {ISSUES_FILE}")
            print(f"  Run {BOLD}site-manager repair{RESET} to fix.")

        sys.exit(0 if success else 1)
