"""Unified status check for all services."""

import json
import os
import shutil
import subprocess
import sys

from webinator.api import api_request
from webinator.config import CONFIG_PATH


def _check_cli(name: str, version_flag: str = "--version") -> dict:
    path = shutil.which(name)
    if not path:
        return {"installed": False, "version": None}
    try:
        out = subprocess.run(
            [name, version_flag], capture_output=True, text=True, timeout=10,
        )
        version = out.stdout.strip().split("\n")[0].lstrip("v").lstrip()
        # Strip leading non-numeric text like "wrangler " or "gh version "
        for i, ch in enumerate(version):
            if ch.isdigit():
                version = version[i:]
                break
        return {"installed": True, "version": version, "path": path}
    except Exception:
        return {"installed": True, "version": "unknown", "path": path}


def _check_godaddy_auth() -> dict:
    if not CONFIG_PATH.exists():
        return {"authenticated": False, "error": "no config file"}
    cfg = json.loads(CONFIG_PATH.read_text())
    gd = cfg.get("godaddy", {})
    key, secret = gd.get("api_key", ""), gd.get("api_secret", "")
    env = gd.get("environment", "production")
    if not key or not secret:
        return {"authenticated": False, "error": "not configured"}

    base = "https://api.ote-godaddy.com" if env == "ote" else "https://api.godaddy.com"
    code, _ = api_request(f"{base}/v1/domains?limit=1", f"sso-key {key}:{secret}")
    if code == 200:
        masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
        return {"authenticated": True, "environment": env, "key": masked}
    return {"authenticated": False, "environment": env, "error": f"HTTP {code}"}


def _check_cloudflare_api() -> dict:
    if not CONFIG_PATH.exists():
        return {"authenticated": False, "error": "no config file"}
    cfg = json.loads(CONFIG_PATH.read_text())
    token = cfg.get("cloudflare", {}).get("api_token", "")
    if not token:
        return {"authenticated": False, "error": "no token configured"}

    code, data = api_request(
        "https://api.cloudflare.com/client/v4/user/tokens/verify",
        f"Bearer {token}",
    )
    if code == 200 and data.get("success"):
        masked = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "***"
        return {"authenticated": True, "token": masked}
    error = data.get("errors", [{}])[0].get("message", "invalid token") if isinstance(data, dict) else f"HTTP {code}"
    return {"authenticated": False, "error": error}


def _check_cli_auth(name: str, args: list[str]) -> dict:
    if not shutil.which(name):
        return {"authenticated": False, "error": f"{name} not installed"}
    try:
        out = subprocess.run([name] + args, capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            account = out.stdout.strip().split("\n")[0]
            return {"authenticated": True, "account": account}
        return {"authenticated": False, "error": "not logged in"}
    except Exception as e:
        return {"authenticated": False, "error": str(e)}


def show_status(output_json: bool = False) -> None:
    result = {
        "cloudflare": {
            "cli": _check_cli("wrangler"),
            "api": _check_cloudflare_api(),
        },
        "railway": {
            "cli": _check_cli("railway", "version"),
            "auth": _check_cli_auth("railway", ["whoami"]),
        },
        "godaddy": {
            "api": _check_godaddy_auth(),
        },
        "github": {
            "cli": _check_cli("gh"),
            "auth": _check_cli_auth("gh", ["auth", "status"]),
        },
    }

    if output_json:
        print(json.dumps(result, indent=2))
        return

    print("\nService Status\n")
    for service, checks in result.items():
        print(f"  {service.upper()}")
        for check_name, info in checks.items():
            if "installed" in info:
                icon = "+" if info["installed"] else "-"
                ver = info.get("version", "")
                print(f"    [{icon}] {check_name}: {ver if info['installed'] else 'not installed'}")
            elif "authenticated" in info:
                icon = "+" if info["authenticated"] else "-"
                detail = info.get("account") or info.get("key") or info.get("token") or info.get("error", "")
                print(f"    [{icon}] {check_name}: {detail}")
        print()
