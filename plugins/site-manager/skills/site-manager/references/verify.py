#!/usr/bin/env python3
"""Site Manager deployment verification script.

Usage:
    python3 verify.py --manifest path/to/site-manifest.json
    python3 verify.py --manifest path/to/site-manifest.json --check-oauth github,google
    python3 verify.py --manifest path/to/site-manifest.json --domain example.com
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path


# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"

UA = "site-manager-verify/1.0"


@dataclass
class CheckResult:
    name: str
    passed: bool
    warning: bool = False  # True = non-blocking (WARN)
    detail: str = ""


class VerifyRunner:
    def __init__(self, manifest: dict, check_oauth: list[str], domain: str):
        self.manifest = manifest
        self.check_oauth = check_oauth  # list of provider names, e.g. ["github", "google"]
        self.domain = domain

        self.results: list[CheckResult] = []
        self._total = 0

        # Derived from manifest
        project = manifest.get("project", {})
        services = manifest.get("services", {})
        self.project_name = project.get("name", "")
        self.project_domain = project.get("domain", "")
        self.display_name = project.get("displayName", "")

        self.backend_url = (services.get("backend") or {}).get("url", "").rstrip("/")
        self.main_url = (services.get("main") or {}).get("url", "").rstrip("/")
        self.admin_url = (services.get("admin") or {}).get("url", "").rstrip("/")
        self.dashboard_url = (services.get("dashboard") or {}).get("url", "").rstrip("/")

    # --- HTTP helpers ---

    def _get(self, url: str, timeout: int = 10) -> tuple[int, str]:
        """GET a URL, return (status, body). Never raises."""
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as e:
            return 0, str(e)

    def _options(self, url: str) -> tuple[int, dict[str, str]]:
        """OPTIONS request, return (status, headers). Never raises."""
        req = urllib.request.Request(
            url,
            method="OPTIONS",
            headers={"User-Agent": UA, "Origin": "https://example.com"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, dict(resp.headers)
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers)
        except Exception as e:
            return 0, {}

    def _get_no_redirect(self, url: str) -> tuple[int, dict[str, str]]:
        """GET without following redirects. Returns (status, headers)."""

        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirectHandler())
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with opener.open(req, timeout=10) as resp:
                return resp.status, dict(resp.headers)
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers)
        except Exception as e:
            return 0, {}

    def _fetch_page_and_assets(self, url: str) -> str:
        """Fetch a URL plus all referenced script/link assets. Returns combined text."""
        status, html = self._get(url)
        if status != 200:
            return html

        combined = html

        # Extract script src and link href values
        script_srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html)
        link_hrefs = re.findall(r'<link[^>]+href=["\']([^"\']+)["\']', html)
        asset_refs = script_srcs + link_hrefs

        base = url.rstrip("/")
        for ref in asset_refs:
            if ref.startswith("http://") or ref.startswith("https://"):
                asset_url = ref
            elif ref.startswith("//"):
                asset_url = "https:" + ref
            elif ref.startswith("/"):
                # Reconstruct base origin
                from urllib.parse import urlparse
                parsed = urlparse(base)
                asset_url = f"{parsed.scheme}://{parsed.netloc}{ref}"
            else:
                asset_url = f"{base}/{ref}"

            _, asset_body = self._get(asset_url)
            combined += asset_body

        return combined

    # --- Result recording ---

    def _record(self, name: str, passed: bool, warning: bool = False, detail: str = ""):
        self.results.append(CheckResult(name=name, passed=passed, warning=warning, detail=detail))
        n = len(self.results)
        total = self._total
        if warning and not passed:
            status_str = "WARN"
            color = YELLOW
        elif passed:
            status_str = "PASS"
            color = GREEN
        else:
            status_str = "FAIL"
            color = RED
        print(f"  {n:>2}/{total}  {color}{status_str}{RESET}  {name}")
        if detail and (not passed or warning):
            for line in detail.splitlines():
                print(f"             {line}")

    def _skip(self, name: str, reason: str = ""):
        self.results.append(CheckResult(name=name, passed=True, warning=False, detail=reason))
        n = len(self.results)
        total = self._total
        print(f"  {n:>2}/{total}  {YELLOW}SKIP{RESET}  {name}")
        if reason:
            print(f"             {reason}")

    # --- Check categories ---

    def check_manifest_integrity(self) -> list[CheckResult]:
        start = len(self.results)

        # 1. Required fields present
        project = self.manifest.get("project", {})
        services = self.manifest.get("services", {})
        missing = []
        for field_name in ("name", "domain", "created"):
            if not project.get(field_name):
                missing.append(f"project.{field_name}")
        for svc_name in ("backend", "main", "admin", "dashboard"):
            svc = services.get(svc_name) or {}
            if not svc.get("status"):
                missing.append(f"services.{svc_name}.status")
            if not svc.get("platform"):
                missing.append(f"services.{svc_name}.platform")
        ok = len(missing) == 0
        detail = ("Missing: " + ", ".join(missing)) if missing else ""
        self._record("Required fields present", ok, detail=detail)

        # 2. Display name
        ok = bool(self.display_name)
        self._record("Display name",
                     ok,
                     detail="" if ok else "project.displayName is missing")

        # 3. Service URLs — deployed services must have a URL
        bad = []
        for svc_name in ("backend", "main", "admin", "dashboard"):
            svc = services.get(svc_name) or {}
            if svc.get("status") == "deployed":
                url = svc.get("url") or svc.get("domain")
                if not url:
                    bad.append(svc_name)
        ok = len(bad) == 0
        detail = ("Deployed services missing URLs: " + ", ".join(bad)) if bad else ""
        self._record("Service URLs", ok, detail=detail)

        # 4. OAuth providers match (only if --check-oauth specified)
        if self.check_oauth:
            providers = (
                self.manifest.get("features", {})
                .get("auth", {})
                .get("providers", [])
            )
            missing_providers = [p for p in self.check_oauth if p not in providers]
            ok = len(missing_providers) == 0
            detail = ("Providers not in manifest: " + ", ".join(missing_providers)) if missing_providers else ""
            self._record("OAuth providers match", ok, detail=detail)
        else:
            self._skip("OAuth providers match", "--check-oauth not specified")

        return self.results[start:]

    def check_api_health(self) -> list[CheckResult]:
        start = len(self.results)

        if not self.backend_url:
            for name in ("Backend health", "Backend readiness", "CORS headers", "Error format (RFC 9457)"):
                self._skip(name, "No backend URL in manifest")
            return self.results[start:]

        # 1. Backend health
        status, body = self._get(f"{self.backend_url}/api/health")
        try:
            parsed = json.loads(body)
            ok = status == 200 and parsed.get("status") == "ok"
        except (json.JSONDecodeError, AttributeError):
            ok = False
        self._record("Backend health",
                     ok,
                     detail="" if ok else f"Expected 200 {{status:ok}}, got {status} {body[:200]}")

        # 2. Backend readiness
        status, body = self._get(f"{self.backend_url}/api/health/ready")
        ok = status == 200
        self._record("Backend readiness",
                     ok,
                     detail="" if ok else f"Expected 200, got {status} {body[:200]}")

        # 3. CORS headers
        status, headers = self._options(f"{self.backend_url}/api/health")
        has_cors = any("access-control" in k.lower() for k in headers)
        self._record("CORS headers",
                     has_cors,
                     detail="" if has_cors else f"No Access-Control-* headers. Got: {list(headers.keys())}")

        # 4. Error format (RFC 9457)
        status, body = self._get(f"{self.backend_url}/api/nonexistent")
        try:
            parsed = json.loads(body)
            ok = status == 404 and "type" in parsed and "title" in parsed
        except (json.JSONDecodeError, AttributeError):
            ok = False
        self._record("Error format (RFC 9457)",
                     ok,
                     detail="" if ok else f"Expected 404 + Problem Details, got {status} {body[:200]}")

        return self.results[start:]

    def check_oauth_wiring(self) -> list[CheckResult]:
        start = len(self.results)

        if not self.check_oauth:
            return self.results[start:]

        if not self.backend_url:
            for provider in self.check_oauth:
                self._skip(f"{provider.capitalize()} OAuth route", "No backend URL in manifest")
            if "github" in self.check_oauth:
                self._skip("Main login has GitHub button", "No backend URL in manifest")
                self._skip("Admin login has GitHub button", "No backend URL in manifest")
            return self.results[start:]

        oauth_domains = {
            "github": "github.com",
            "google": "accounts.google.com",
        }

        for provider in self.check_oauth:
            url = f"{self.backend_url}/api/auth/{provider}"
            status, headers = self._get_no_redirect(url)
            location = headers.get("Location", headers.get("location", ""))
            expected_domain = oauth_domains.get(provider, provider)
            ok = status == 302 and expected_domain in location
            detail = ""
            if not ok:
                if status == 404:
                    detail = f"Route not found (404). Expected 302 → {expected_domain}"
                else:
                    detail = f"Expected 302 with Location containing {expected_domain}, got {status} Location={location!r}"
            self._record(f"{provider.capitalize()} OAuth route", ok, detail=detail)

        # Check login pages for provider buttons (SPA bundles)
        button_checks = []
        if "github" in self.check_oauth:
            button_checks.append(("Main login has GitHub button", self.main_url, "GitHub"))
            button_checks.append(("Admin login has GitHub button", self.admin_url, "GitHub"))
        if "google" in self.check_oauth:
            button_checks.append(("Main login has Google button", self.main_url, "Google"))
            button_checks.append(("Admin login has Google button", self.admin_url, "Google"))

        for check_name, site_url, marker in button_checks:
            if not site_url:
                self._skip(check_name, "No URL in manifest")
                continue
            content = self._fetch_page_and_assets(site_url)
            ok = marker.lower() in content.lower()
            self._record(check_name, ok,
                         detail="" if ok else f'"{marker}" not found in page or JS/CSS assets')

        return self.results[start:]

    def check_frontend_content(self) -> list[CheckResult]:
        start = len(self.results)

        dark_bg = "#0c0c0f"

        # Main site
        if self.main_url:
            status, body = self._get(self.main_url)
            ok = status == 200
            self._record("Main site responds", ok,
                         detail="" if ok else f"Expected 200, got {status}")

            content = self._fetch_page_and_assets(self.main_url) if ok else body
            ok_dark = dark_bg in content
            self._record("Main site dark theme", ok_dark,
                         detail="" if ok_dark else f'"{dark_bg}" not found in page or JS/CSS assets')

            ok_name = bool(self.display_name) and self.display_name in content
            detail = ""
            if not ok_name:
                if not self.display_name:
                    detail = "displayName not set in manifest — skipped content check"
                else:
                    detail = f'"{self.display_name}" not found in page or JS/CSS assets'
            self._record("Main site display name", ok_name, detail=detail)
        else:
            self._skip("Main site responds", "No main URL in manifest")
            self._skip("Main site dark theme", "No main URL in manifest")
            self._skip("Main site display name", "No main URL in manifest")

        # Admin site
        if self.admin_url:
            status, body = self._get(self.admin_url)
            ok = status == 200
            self._record("Admin site responds", ok,
                         detail="" if ok else f"Expected 200, got {status}")

            content = self._fetch_page_and_assets(self.admin_url) if ok else body
            ok_dark = dark_bg in content
            self._record("Admin site dark theme", ok_dark,
                         detail="" if ok_dark else f'"{dark_bg}" not found in page or JS/CSS assets')

            ok_name = bool(self.display_name) and self.display_name in content
            detail = ""
            if not ok_name:
                if not self.display_name:
                    detail = "displayName not set in manifest — skipped content check"
                else:
                    detail = f'"{self.display_name}" not found in page or JS/CSS assets'
            self._record("Admin site display name", ok_name, detail=detail)
        else:
            self._skip("Admin site responds", "No admin URL in manifest")
            self._skip("Admin site dark theme", "No admin URL in manifest")
            self._skip("Admin site display name", "No admin URL in manifest")

        # Dashboard
        if self.dashboard_url:
            status, _ = self._get(self.dashboard_url)
            ok = status == 200
            self._record("Dashboard responds", ok,
                         detail="" if ok else f"Expected 200, got {status}")
        else:
            self._skip("Dashboard responds", "No dashboard URL in manifest")

        return self.results[start:]

    def check_dns_resolution(self) -> list[CheckResult]:
        start = len(self.results)

        domain = self.domain or self.project_domain
        if not domain:
            return self.results[start:]

        # Skip DNS checks for workers.dev domains
        if domain.endswith(".workers.dev"):
            for name in ("A record resolves", "Admin CNAME resolves",
                         "Dashboard CNAME resolves", "Cloudflare nameservers"):
                self._skip(name, "workers.dev domain — DNS checks skipped")
            return self.results[start:]

        # A record
        result = subprocess.run(
            ["dig", "+short", "A", domain],
            capture_output=True, text=True
        )
        ok = bool(result.stdout.strip())
        self._record("A record resolves", ok, warning=True,
                     detail="" if ok else f"dig +short A {domain} returned no output")

        # Admin CNAME
        result_cname = subprocess.run(
            ["dig", "+short", "CNAME", f"admin.{domain}"],
            capture_output=True, text=True
        )
        result_a = subprocess.run(
            ["dig", "+short", "A", f"admin.{domain}"],
            capture_output=True, text=True
        )
        ok = bool(result_cname.stdout.strip()) or bool(result_a.stdout.strip())
        self._record("Admin CNAME resolves", ok, warning=True,
                     detail="" if ok else f"dig returned no output for admin.{domain}")

        # Dashboard CNAME
        result_cname = subprocess.run(
            ["dig", "+short", "CNAME", f"dashboard.{domain}"],
            capture_output=True, text=True
        )
        result_a = subprocess.run(
            ["dig", "+short", "A", f"dashboard.{domain}"],
            capture_output=True, text=True
        )
        ok = bool(result_cname.stdout.strip()) or bool(result_a.stdout.strip())
        self._record("Dashboard CNAME resolves", ok, warning=True,
                     detail="" if ok else f"dig returned no output for dashboard.{domain}")

        # Cloudflare nameservers
        result = subprocess.run(
            ["dig", "NS", domain],
            capture_output=True, text=True
        )
        ok = "cloudflare" in result.stdout.lower()
        self._record("Cloudflare nameservers", ok, warning=True,
                     detail="" if ok else f"'cloudflare' not found in NS output for {domain}")

        return self.results[start:]

    def check_ssl(self) -> list[CheckResult]:
        start = len(self.results)

        domain = self.domain or self.project_domain
        if not domain:
            return self.results[start:]

        ssl_checks = [
            ("Main SSL", f"https://{domain}"),
            ("Admin SSL", f"https://admin.{domain}"),
            ("Dashboard SSL", f"https://dashboard.{domain}"),
        ]

        for name, url in ssl_checks:
            result = subprocess.run(
                ["curl", "-sI", "--max-time", "5", url],
                capture_output=True, text=True
            )
            ok = result.returncode == 0
            self._record(name, ok, warning=True,
                         detail="" if ok else f"curl -sI {url} exited {result.returncode}: {result.stderr.strip()}")

        return self.results[start:]

    def run(self) -> bool:
        """Run all checks. Returns True if all blocking checks pass."""
        # Determine which categories to include and pre-count total checks
        # We need to pre-compute _total. Use a dry-run count approach:
        # Count based on known checks + conditional checks.
        # Easier: collect in categories, then set _total before printing each category.

        project = self.manifest.get("project", {})
        domain = self.domain or self.project_domain
        display = self.display_name or project.get("name", "unknown")

        print(f"\n=== SITE MANAGER VERIFICATION ===")
        proj_label = f"{self.project_name}" if self.project_name else "(no name)"
        dom_label = f" ({self.project_domain})" if self.project_domain else ""
        print(f"Project: {proj_label}{dom_label}\n")

        categories: list[tuple[str, list[CheckResult]]] = []

        # --- Manifest Integrity ---
        integrity_total = 4  # always 4 (4th is skip if no --check-oauth)
        self._total = integrity_total
        print("Manifest Integrity")
        results = self.check_manifest_integrity()
        categories.append(("Manifest Integrity", results))
        print()

        # --- API Health ---
        api_total = 4
        self._total = api_total
        print("API Health")
        results = self.check_api_health()
        categories.append(("API Health", results))
        print()

        # --- OAuth Wiring ---
        if self.check_oauth:
            # provider routes + login page buttons (2 per provider for main+admin)
            oauth_total = len(self.check_oauth) + len(self.check_oauth) * 2
            self._total = oauth_total
            print("OAuth Wiring")
            results = self.check_oauth_wiring()
            categories.append(("OAuth Wiring", results))
            print()

        # --- Frontend Content ---
        frontend_total = 7  # 3 main + 3 admin + 1 dashboard
        self._total = frontend_total
        print("Frontend Content")
        results = self.check_frontend_content()
        categories.append(("Frontend Content", results))
        print()

        # --- DNS Resolution ---
        if domain:
            dns_total = 4
            self._total = dns_total
            print("DNS Resolution")
            results = self.check_dns_resolution()
            categories.append(("DNS Resolution", results))
            print()

        # --- SSL/TLS ---
        if domain:
            ssl_total = 3
            self._total = ssl_total
            print("SSL/TLS")
            results = self.check_ssl()
            categories.append(("SSL/TLS", results))
            print()

        # Summary
        all_results = self.results
        total = len(all_results)
        passed = sum(1 for r in all_results if r.passed)
        failed = sum(1 for r in all_results if not r.passed and not r.warning)
        warnings = sum(1 for r in all_results if not r.passed and r.warning)
        # skips count as passed
        skipped = sum(1 for r in all_results if r.passed and r.detail and not r.warning)

        print(f"Results: {passed}/{total} passed", end="")
        if failed:
            print(f", {RED}{failed} failed{RESET}", end="")
        if warnings:
            print(f", {YELLOW}{warnings} warnings{RESET}", end="")
        print()

        # All blocking checks pass = no non-warning failures
        blocking_failures = [r for r in all_results if not r.passed and not r.warning]
        return len(blocking_failures) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Verify a deployed site-manager project against its manifest"
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to the site-manifest.json file",
    )
    parser.add_argument(
        "--check-oauth",
        default="",
        help="Comma-separated OAuth providers to verify (e.g. github,google)",
    )
    parser.add_argument(
        "--domain",
        default="",
        help="Custom domain to use for DNS/SSL checks (overrides manifest domain)",
    )

    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"{RED}ERROR{RESET}: Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        print(f"{RED}ERROR{RESET}: Failed to parse manifest JSON: {e}", file=sys.stderr)
        sys.exit(1)

    check_oauth = [p.strip().lower() for p in args.check_oauth.split(",") if p.strip()]

    runner = VerifyRunner(
        manifest=manifest,
        check_oauth=check_oauth,
        domain=args.domain,
    )

    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
