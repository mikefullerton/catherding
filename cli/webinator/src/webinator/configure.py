"""Configure API credentials for GoDaddy and Cloudflare."""

import json
import sys

from webinator.api import api_request
from webinator.config import ensure_config, save_config, load_config, CONFIG_PATH


def godaddy_get() -> None:
    if not CONFIG_PATH.exists():
        print("Not configured.")
        return
    cfg = load_config()
    gd = cfg.get("godaddy", {})
    key = gd.get("api_key", "")
    env = gd.get("environment", "production")
    if key:
        masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
        print(f"\n  API Key:     {masked}")
        print(f"  API Secret:  ****")
        print(f"  Environment: {env}\n")
    else:
        print(f"\n  Not configured (environment: {env})\n")


def godaddy_set(key: str, secret: str) -> None:
    cfg = ensure_config()
    cfg.setdefault("godaddy", {})
    cfg["godaddy"]["api_key"] = key
    cfg["godaddy"]["api_secret"] = secret
    save_config(cfg)
    print("GoDaddy credentials saved.")


def godaddy_set_env(env: str) -> None:
    if env not in ("production", "ote"):
        print("error: environment must be 'production' or 'ote'", file=sys.stderr)
        sys.exit(1)
    cfg = ensure_config()
    cfg.setdefault("godaddy", {})
    cfg["godaddy"]["environment"] = env
    save_config(cfg)
    print(f"GoDaddy environment set to: {env}")


def godaddy_test() -> None:
    cfg = load_config()
    gd = cfg.get("godaddy", {})
    key, secret = gd.get("api_key", ""), gd.get("api_secret", "")
    env = gd.get("environment", "production")
    if not key or not secret:
        print("error: not configured", file=sys.stderr)
        sys.exit(1)

    base = "https://api.ote-godaddy.com" if env == "ote" else "https://api.godaddy.com"
    code, data = api_request(f"{base}/v1/domains?limit=1", f"sso-key {key}:{secret}")
    if code == 200:
        print(f"OK — connected to GoDaddy ({env})")
    else:
        print(f"FAILED — HTTP {code}", file=sys.stderr)
        sys.exit(1)


def cloudflare_get() -> None:
    if not CONFIG_PATH.exists():
        print("Not configured.")
        return
    cfg = load_config()
    cf = cfg.get("cloudflare", {})
    token = cf.get("api_token", "")
    account_id = cf.get("account_id", "")
    if token:
        masked = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "***"
        print(f"\n  API Token:   {masked}")
        print(f"  Account ID:  {account_id or '(not set)'}\n")
    else:
        print("\n  Not configured.\n")


def cloudflare_set(token: str) -> None:
    # Verify token first
    code, data = api_request(
        "https://api.cloudflare.com/client/v4/zones?per_page=1",
        f"Bearer {token}",
    )
    if code != 200 or not data.get("success"):
        error = data.get("errors", [{}])[0].get("message", "unknown") if isinstance(data, dict) else f"HTTP {code}"
        print(f"error: token verification failed — {error}", file=sys.stderr)
        sys.exit(1)

    # Fetch account ID
    _, acct_data = api_request(
        "https://api.cloudflare.com/client/v4/accounts?per_page=1",
        f"Bearer {token}",
    )
    account_id = ""
    account_name = ""
    if isinstance(acct_data, dict) and acct_data.get("result"):
        account_id = acct_data["result"][0].get("id", "")
        account_name = acct_data["result"][0].get("name", "")

    cfg = ensure_config()
    cfg.setdefault("cloudflare", {})
    cfg["cloudflare"]["api_token"] = token
    cfg["cloudflare"]["account_id"] = account_id
    save_config(cfg)

    zone_count = data.get("result_info", {}).get("total_count", 0)
    print(f"Cloudflare token saved.")
    if account_name:
        print(f"  Account: {account_name}")
    print(f"  Zones:   {zone_count}")


def cloudflare_test() -> None:
    cfg = load_config()
    token = cfg.get("cloudflare", {}).get("api_token", "")
    if not token:
        print("error: not configured", file=sys.stderr)
        sys.exit(1)

    code, data = api_request(
        "https://api.cloudflare.com/client/v4/zones?per_page=1",
        f"Bearer {token}",
    )
    if code == 200 and data.get("success"):
        zones = data.get("result_info", {}).get("total_count", 0)
        print(f"OK — connected to Cloudflare ({zones} zones)")
    else:
        error = data.get("errors", [{}])[0].get("message", "unknown") if isinstance(data, dict) else f"HTTP {code}"
        print(f"FAILED — {error}", file=sys.stderr)
        sys.exit(1)
