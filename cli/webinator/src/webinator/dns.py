"""DNS record management — auto-detects GoDaddy vs Cloudflare."""

import json
import sys

from webinator.api import api_get, api_request
from webinator.config import get_godaddy_auth, get_cloudflare_auth

CF_API = "https://api.cloudflare.com/client/v4"


def _detect_provider(domain: str) -> str:
    """Detect DNS provider from nameservers. Returns 'cloudflare', 'godaddy', or 'unknown'."""
    base_url, auth = get_godaddy_auth()
    data = api_get(f"{base_url}/v1/domains/{domain}", auth)
    ns = " ".join(data.get("nameServers", [])).lower()
    if "cloudflare" in ns:
        return "cloudflare"
    if "domaincontrol" in ns:
        return "godaddy"
    return "unknown"


def _get_zone_id(domain: str, token: str) -> str:
    """Lookup Cloudflare zone ID for a domain."""
    code, data = api_request(
        f"{CF_API}/zones?name={domain}&per_page=1",
        f"Bearer {token}",
    )
    if code != 200 or not data.get("success"):
        print(f"error: failed to lookup Cloudflare zone for {domain}", file=sys.stderr)
        sys.exit(1)
    results = data.get("result", [])
    if not results:
        print(f"error: zone not found for {domain} in Cloudflare", file=sys.stderr)
        sys.exit(1)
    return results[0]["id"]


def _list_godaddy(domain: str) -> list[dict]:
    base_url, auth = get_godaddy_auth()
    records = api_get(f"{base_url}/v1/domains/{domain}/records", auth)
    return [{"type": r["type"], "name": r["name"], "value": r["data"], "ttl": r["ttl"]}
            for r in records]


def _list_cloudflare(domain: str) -> list[dict]:
    token, _ = get_cloudflare_auth()
    zone_id = _get_zone_id(domain, token)
    auth = f"Bearer {token}"

    all_records = []
    page = 1
    while True:
        code, data = api_request(
            f"{CF_API}/zones/{zone_id}/dns_records?per_page=100&page={page}",
            auth,
        )
        if code != 200 or not data.get("success"):
            print("error: failed to fetch DNS records from Cloudflare", file=sys.stderr)
            sys.exit(1)
        for r in data.get("result", []):
            all_records.append({
                "type": r["type"], "name": r["name"], "value": r["content"],
                "ttl": r["ttl"], "proxied": r.get("proxied", False),
            })
        total_pages = data.get("result_info", {}).get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1

    return all_records


DNS_COLUMNS = [
    ("TYPE", "type", 8),
    ("NAME", "name", 35),
    ("VALUE", "value", 40),
    ("TTL", lambda r: str(r.get("ttl", "")), 8),
]


def list_dns(domain: str, output_json: bool = False) -> None:
    provider = _detect_provider(domain)
    if provider == "cloudflare":
        records = _list_cloudflare(domain)
    elif provider == "godaddy":
        records = _list_godaddy(domain)
    else:
        print(f"error: cannot detect DNS provider for {domain}", file=sys.stderr)
        print("Nameservers don't match Cloudflare or GoDaddy.", file=sys.stderr)
        sys.exit(1)

    if output_json:
        print(json.dumps(records, indent=2))
        return

    print(f"\n{len(records)} DNS record(s) for {domain} (provider: {provider})\n")
    if not records:
        print("  No records found.")
        return

    header = "  ".join(h.ljust(w) for h, _, w in DNS_COLUMNS)
    print(header)
    print("-" * len(header))
    for r in records:
        parts = []
        for _, key, w in DNS_COLUMNS:
            val = key(r) if callable(key) else str(r.get(key, ""))
            parts.append(val.ljust(w))
        print("  ".join(parts))
    print()
