"""Domain portfolio management via GoDaddy API."""

import json
import sys
from datetime import datetime, timedelta, timezone

from webinator.api import api_get
from webinator.config import get_godaddy_auth


def _fetch_domains(status_filter: str | None = None) -> list[dict]:
    base_url, auth = get_godaddy_auth()
    url = f"{base_url}/v1/domains?limit=500"
    if status_filter:
        url += f"&statuses={status_filter}"
    return api_get(url, auth)


def _format_table(rows: list[dict], columns: list[tuple[str, str, int]]) -> str:
    if not rows:
        return "No results."

    lines = []
    header = "  ".join(h.ljust(w) for h, _, w in columns)
    lines.append(header)
    lines.append("-" * len(header))

    for d in rows:
        parts = []
        for _, key, w in columns:
            val = key(d) if callable(key) else str(d.get(key, ""))
            parts.append(val.ljust(w))
        lines.append("  ".join(parts))

    return "\n".join(lines)


def _expires_short(d: dict) -> str:
    exp = d.get("expires", "")
    return exp[:10] if exp else ""


def _bool_yn(key: str):
    def _inner(d: dict) -> str:
        v = d.get(key)
        if v is None:
            return "-"
        return "yes" if v else "no"
    return _inner


LIST_COLUMNS = [
    ("DOMAIN", "domain", 35),
    ("STATUS", "status", 12),
    ("EXPIRES", _expires_short, 12),
    ("PRIVACY", _bool_yn("privacy"), 8),
    ("AUTO-RENEW", _bool_yn("renewAuto"), 10),
    ("LOCKED", _bool_yn("locked"), 8),
]


def list_domains(
    status: str | None = None,
    expiring: bool = False,
    privacy_off: bool = False,
    autorenew_off: bool = False,
    name: str | None = None,
    output_json: bool = False,
) -> None:
    domains = _fetch_domains(status_filter=status)

    if expiring:
        cutoff = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        domains = [d for d in domains if d.get("expires", "") <= cutoff]
    if privacy_off:
        domains = [d for d in domains if d.get("privacy") is False]
    if autorenew_off:
        domains = [d for d in domains if d.get("renewAuto") is False]
    if name:
        name_lower = name.lower()
        domains = [d for d in domains if name_lower in d.get("domain", "").lower()]

    if output_json:
        print(json.dumps(domains, indent=2))
    else:
        print(f"\n{len(domains)} domain(s)\n")
        print(_format_table(domains, LIST_COLUMNS))


def search_domains(query: str, output_json: bool = False) -> None:
    domains = _fetch_domains()
    q = query.lower()
    matches = [d for d in domains if q in d.get("domain", "").lower()]

    if output_json:
        print(json.dumps(matches, indent=2))
    else:
        print(f"\n{len(matches)} match(es) for '{query}'\n")
        print(_format_table(matches, LIST_COLUMNS))


def info_domain(domain: str, output_json: bool = False) -> None:
    base_url, auth = get_godaddy_auth()
    data = api_get(f"{base_url}/v1/domains/{domain}", auth)

    if output_json:
        print(json.dumps(data, indent=2))
        return

    print(f"\n  Domain:      {data.get('domain', '')}")
    print(f"  Status:      {data.get('status', '')}")
    print(f"  Created:     {str(data.get('createdAt', ''))[:10]}")
    print(f"  Expires:     {str(data.get('expires', ''))[:10]}")
    print(f"  Privacy:     {'yes' if data.get('privacy') else 'no'}")
    print(f"  Auto-renew:  {'yes' if data.get('renewAuto') else 'no'}")
    print(f"  Locked:      {'yes' if data.get('locked') else 'no'}")
    ns = data.get("nameServers", [])
    print(f"  Nameservers: {', '.join(ns) if ns else 'none'}")

    # Detect provider from nameservers
    ns_str = " ".join(ns).lower()
    if "cloudflare" in ns_str:
        provider = "cloudflare"
    elif "domaincontrol" in ns_str:
        provider = "godaddy"
    else:
        provider = "unknown"
    print(f"  DNS Provider: {provider}")
    print()


def privacy_check(output_json: bool = False) -> None:
    domains = _fetch_domains(status_filter="ACTIVE")

    report = {
        "total": len(domains),
        "privacy_off": [d["domain"] for d in domains if d.get("privacy") is False],
        "autorenew_off": [d["domain"] for d in domains if d.get("renewAuto") is False],
        "unlocked": [d["domain"] for d in domains if d.get("locked") is False],
        "expiration_protection_off": [d["domain"] for d in domains if d.get("expirationProtected") is False],
        "transfer_protection_off": [d["domain"] for d in domains if d.get("transferProtected") is False],
    }

    if output_json:
        print(json.dumps(report, indent=2))
        return

    print(f"\nSecurity audit — {report['total']} active domain(s)\n")
    for label, key in [
        ("Privacy off", "privacy_off"),
        ("Auto-renew off", "autorenew_off"),
        ("Unlocked", "unlocked"),
        ("Expiration protection off", "expiration_protection_off"),
        ("Transfer protection off", "transfer_protection_off"),
    ]:
        items = report[key]
        print(f"  {label}: {len(items)}")
        for d in items[:10]:
            print(f"    - {d}")
        if len(items) > 10:
            print(f"    ... and {len(items) - 10} more")
    print()
