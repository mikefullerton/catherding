"""Load and manage ~/.webinitor/config.json credentials."""

import json
import os
import sys
from pathlib import Path

CONFIG_DIR = Path.home() / ".webinitor"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "godaddy": {"api_key": "", "api_secret": "", "environment": "production"},
    "cloudflare": {"api_token": "", "account_id": ""},
    "preferences": {"install_method": "brew"},
}


def ensure_config() -> dict:
    """Create config dir/file if missing, return config."""
    if not CONFIG_DIR.exists():
        CONFIG_DIR.mkdir(mode=0o700, parents=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
        os.chmod(CONFIG_PATH, 0o600)
    return json.loads(CONFIG_PATH.read_text())


def save_config(cfg: dict) -> None:
    ensure_config()
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    os.chmod(CONFIG_PATH, 0o600)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"error: no config file at {CONFIG_PATH}", file=sys.stderr)
        print("Run: webinator configure godaddy set <key> <secret>", file=sys.stderr)
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text())


def get_godaddy_auth() -> tuple[str, str]:
    """Return (base_url, authorization_header) for GoDaddy API."""
    cfg = load_config()
    gd = cfg.get("godaddy", {})
    key = gd.get("api_key", "")
    secret = gd.get("api_secret", "")
    env = gd.get("environment", "production")

    if not key or not secret:
        print("error: GoDaddy API not configured", file=sys.stderr)
        print("Run: webinator configure godaddy set <key> <secret>", file=sys.stderr)
        sys.exit(1)

    base_url = (
        "https://api.ote-godaddy.com"
        if env == "ote"
        else "https://api.godaddy.com"
    )
    auth_header = f"sso-key {key}:{secret}"
    return base_url, auth_header


def get_cloudflare_auth() -> tuple[str, str | None]:
    """Return (bearer_token, account_id_or_none) for Cloudflare API."""
    cfg = load_config()
    cf = cfg.get("cloudflare", {})
    token = cf.get("api_token", "")
    account_id = cf.get("account_id", "") or None

    if not token:
        print("error: Cloudflare API token not configured", file=sys.stderr)
        print("Run: webinator configure cloudflare set <token>", file=sys.stderr)
        sys.exit(1)

    return token, account_id
