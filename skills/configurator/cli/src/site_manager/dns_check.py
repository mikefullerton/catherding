"""DNS resolution verification for deployed sites.

Best-effort checks with retries for propagation delays.
Uses stdlib socket — no external DNS libraries needed.
"""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

from site_manager.check import CheckRecorder


SUITE = "dns"


def count_checks(manifest: dict) -> int:
    """Return the number of checks for this manifest."""
    domain = manifest.get("project", {}).get("domain", "")
    if not domain or domain.endswith(".workers.dev"):
        return 0
    return 7  # root resolves, root:443, NS records, is cloudflare, + 2 subdomains x (resolves, routes)


class DNSChecker:
    def __init__(self, manifest: dict, recorder: CheckRecorder,
                 retries: int = 3, delay: float = 2.0):
        self.manifest = manifest
        self.rec = recorder
        self.retries = retries
        self.delay = delay

        project = manifest.get("project", {})
        self.domain = project.get("domain", "")

    def _resolve_with_retry(self, hostname: str) -> list[str]:
        for attempt in range(self.retries):
            try:
                results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                ips = list(set(r[4][0] for r in results))
                if ips:
                    return ips
            except socket.gaierror:
                pass
            if attempt < self.retries - 1:
                time.sleep(self.delay)
        return []

    def _get_nameservers(self, domain: str) -> list[str]:
        try:
            result = subprocess.run(
                ["dig", "+short", "NS", domain],
                capture_output=True, text=True, timeout=10,
            )
            return [ns.strip().rstrip(".") for ns in result.stdout.strip().split("\n") if ns.strip()]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _get_cname(self, hostname: str) -> str:
        try:
            result = subprocess.run(
                ["dig", "+short", "CNAME", hostname],
                capture_output=True, text=True, timeout=10,
            )
            return result.stdout.strip().rstrip(".")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def run(self):
        if not self.domain or self.domain.endswith(".workers.dev"):
            return

        self.rec.section("DNS Resolution")

        # 1. Root domain resolves
        root_ips = self._resolve_with_retry(self.domain)
        self.rec.record(f"{self.domain} resolves", bool(root_ips), suite=SUITE,
                        detail="" if root_ips else f"Could not resolve after {self.retries} attempts")

        # 2. Root domain serves HTTPS
        if root_ips:
            try:
                sock = socket.create_connection((self.domain, 443), timeout=5)
                sock.close()
                self.rec.record(f"{self.domain}:443 reachable", True, suite=SUITE)
            except (socket.timeout, socket.error, OSError) as e:
                self.rec.record(f"{self.domain}:443 reachable", False, detail=str(e), suite=SUITE)
        else:
            self.rec.record(f"{self.domain}:443 reachable", False, warning=True, suite=SUITE,
                            detail="Cannot test — domain did not resolve")

        # 3. NS records
        nameservers = self._get_nameservers(self.domain)
        self.rec.record(f"{self.domain} has NS records", bool(nameservers), suite=SUITE,
                        detail="" if nameservers else f"No NS records found")

        # 4. Cloudflare nameservers
        if nameservers:
            is_cf = any("cloudflare" in ns.lower() for ns in nameservers)
            self.rec.record("Nameservers are Cloudflare", is_cf, warning=True, suite=SUITE,
                            detail="" if is_cf else f"NS records: {', '.join(nameservers)}")
        else:
            self.rec.record("Nameservers are Cloudflare", False, warning=True, suite=SUITE,
                            detail="No NS records to check")

        # 5-6. Subdomain checks
        for sub in ("admin", "dashboard"):
            hostname = f"{sub}.{self.domain}"
            sub_ips = self._resolve_with_retry(hostname)

            self.rec.record(f"{hostname} resolves", bool(sub_ips), suite=SUITE,
                            detail="" if sub_ips else f"Could not resolve after {self.retries} attempts")

            if sub_ips and root_ips:
                same = bool(set(sub_ips) & set(root_ips))
                cname = self._get_cname(hostname)
                if same:
                    self.rec.record(f"{hostname} routes to same origin", True, suite=SUITE)
                elif cname:
                    self.rec.record(f"{hostname} routes to same origin", True, suite=SUITE,
                                    detail=f"Via CNAME → {cname}")
                else:
                    self.rec.record(f"{hostname} routes to same origin", True, warning=True, suite=SUITE,
                                    detail="Different IPs (may be correct if using separate workers)")
            elif sub_ips:
                self.rec.record(f"{hostname} routes to same origin", True, warning=True, suite=SUITE,
                                detail="Root domain didn't resolve — can't compare")
            else:
                self.rec.record(f"{hostname} routes to same origin", False, suite=SUITE,
                                detail="Subdomain did not resolve")


def run_dns_check(output_json: bool = False) -> None:
    p = Path("site-manifest.json")
    if not p.exists():
        print("error: no site-manifest.json found", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(p.read_text())
    project = manifest.get("project", {})
    total = count_checks(manifest)

    if total == 0:
        domain = project.get("domain", "")
        if domain.endswith(".workers.dev"):
            print(f"Skipping DNS checks — {domain} is a workers.dev domain")
        else:
            print("error: no domain in manifest", file=sys.stderr)
        sys.exit(0 if domain else 1)

    rec = CheckRecorder(total)
    print(f"\n=== DNS VERIFICATION ===")
    print(f"Project: {project.get('name', '?')} ({project.get('domain', '?')})")

    checker = DNSChecker(manifest, rec)
    checker.run()

    if output_json:
        print(rec.to_json())
    else:
        rec.summary()
    sys.exit(0 if rec.summary() else 1)
