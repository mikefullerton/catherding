"""Interactive project configurator — creates deployment specs for Claude."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from configurator import __version__

CONFIG_DIR = Path.home() / ".configurator"
GLOBAL_CONFIG = CONFIG_DIR / "configurator-config.json"
ORGS = ["mikefullerton", "agentic-cookbook"]

# Locate CHANGES.md relative to this source file (editable install)
CHANGES_PATH = Path(__file__).resolve().parents[3] / "CHANGES.md"


# ── Config I/O ──────────────────────────────────────────────────────────────


def config_path(name: str) -> Path:
    return CONFIG_DIR / f"{name}.json"


def list_configs() -> list[str]:
    if not CONFIG_DIR.exists():
        return []
    return sorted(p.stem for p in CONFIG_DIR.glob("*.json") if p != GLOBAL_CONFIG)


def load_config(name: str) -> dict:
    path = config_path(name)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_config(name: str, cfg: dict) -> None:
    cfg["configurator_version"] = __version__
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_path(name).write_text(json.dumps(cfg, indent=2) + "\n")


def delete_config(name: str) -> None:
    path = config_path(name)
    if path.exists():
        path.unlink()


def load_global_config() -> dict:
    if GLOBAL_CONFIG.exists():
        return json.loads(GLOBAL_CONFIG.read_text())
    return {}


def save_global_config(gcfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    GLOBAL_CONFIG.write_text(json.dumps(gcfg, indent=2) + "\n")


def _find_repo(projects_path: str, repo_name: str) -> Path | None:
    """Search for a repo directory under projects_path (up to 2 levels deep)."""
    base = Path(projects_path)
    # Direct child
    candidate = base / repo_name
    if candidate.is_dir():
        return candidate.resolve()
    # One level deeper (e.g., projects/active/repo-name)
    for sub in base.iterdir():
        if sub.is_dir() and not sub.name.startswith("."):
            candidate = sub / repo_name
            if candidate.is_dir():
                return candidate.resolve()
    return None


def _load_manifest(path: Path) -> dict | None:
    """Load .site/manifest.json from a project path."""
    manifest_path = path / ".site" / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Merge overlay into base. Overlay values win at leaf level; base fills gaps."""
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _manifest_to_config(manifest: dict, *, saved: dict | None = None) -> dict:
    """Map a .site/manifest.json to a configurator config structure.

    If *saved* is provided, the saved config is used as a base and
    manifest-derived values are deep-merged on top — but only for features
    that actually had data in the manifest (not just defaults).  This
    preserves user preferences (environments, theme, etc.) that were
    configured but not yet deployed.
    """
    from configurator.features import discover_features
    cfg: dict = {}
    for feature in discover_features():
        from_manifest = feature.manifest_to_config(manifest)
        if saved and from_manifest == feature.default_config():
            # Manifest had no data for this feature — keep saved config
            continue
        _apply_feature_config(cfg, feature, from_manifest)
    if saved:
        cfg = _deep_merge(saved, cfg)
    return cfg


def _deployed_keys_from_manifest(manifest: dict) -> set[str]:
    """Extract which features are deployed from a manifest."""
    from configurator.features import discover_features
    keys: set[str] = set()
    for feature in discover_features():
        keys.update(feature.deployed_keys(manifest))
    return keys


def _apply_feature_config(cfg: dict, feature, feature_cfg) -> None:
    """Write a feature's config into the full config dict, maintaining backward compat."""
    fid = feature.meta().id
    if fid == "project":
        cfg.update(feature_cfg)
    elif fid == "admin":
        cfg.setdefault("admin_sites", {})["admin"] = feature_cfg
    elif fid == "dashboard":
        cfg.setdefault("admin_sites", {})["dashboard"] = feature_cfg
    elif fid == "auth":
        if feature_cfg:
            cfg["auth_providers"] = feature_cfg
    else:
        cfg[fid] = feature_cfg


def _detect_org_from_git(path: Path) -> str | None:
    """Detect GitHub org from git remote URL."""
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        # Handle both SSH and HTTPS URLs
        # git@github.com:org/repo.git or https://github.com/org/repo.git
        m = re.search(r"github\.com[:/]([^/]+)/", url)
        return m.group(1) if m else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _extract_urls_from_manifest(manifest: dict) -> dict[str, str]:
    """Extract deployed URLs from manifest services."""
    urls: dict[str, str] = {}
    services = manifest.get("services", {})
    for key in ("main", "backend", "admin", "dashboard"):
        svc = services.get(key, {})
        if svc.get("url"):
            urls[key] = svc["url"]
        elif svc.get("domain"):
            urls[key] = f"https://{svc['domain']}"
    return urls


def _check_live_domains(manifest: dict) -> set[str]:
    """Check which domains from the manifest resolve via DNS."""
    import socket
    services = manifest.get("services", {})
    domains: dict[str, str] = {}
    for key in ("main", "backend", "admin", "dashboard"):
        domain = services.get(key, {}).get("domain")
        if domain:
            domains[key] = domain
    live: set[str] = set()
    for key, domain in domains.items():
        try:
            socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM)
            live.add(key)
        except socket.gaierror:
            pass
    return live


# ── Change history ─────────────────────────────────────────────────────────


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse a version string like '0.2.0' into a comparable tuple."""
    return tuple(int(x) for x in v.split("."))


def _load_changes_since(since_version: str | None) -> dict[str, list[str]]:
    """Parse CHANGES.md and return changes grouped by version, for versions > since_version."""
    if not CHANGES_PATH.exists():
        return {}

    text = CHANGES_PATH.read_text()
    since = _parse_version(since_version) if since_version else (0, 0, 0)

    changes: dict[str, list[str]] = {}
    current_version: str | None = None

    for line in text.splitlines():
        # Match version headings like "## 0.3.0"
        m = re.match(r"^## (\d+\.\d+\.\d+)", line)
        if m:
            current_version = m.group(1)
            continue

        if current_version and _parse_version(current_version) > since:
            stripped = line.strip()
            if stripped.startswith("- "):
                changes.setdefault(current_version, []).append(stripped)

    return changes


def _show_new_options(manifest_version: str | None) -> None:
    """Show new deployment options available since manifest_version."""
    changes = _load_changes_since(manifest_version)
    if not changes:
        return

    print()
    print("  New deployment options available:")
    print()
    for version in sorted(changes.keys(), key=_parse_version):
        print(f"    v{version}:")
        for entry in changes[version]:
            print(f"      {entry}")
        print()


# ── Display ─────────────────────────────────────────────────────────────────


def show_config(name: str) -> None:
    cfg = load_config(name)
    if not cfg:
        print(f"No configuration found for '{name}'.")
        return

    domain = cfg.get("domain", "—")
    print()
    print(f"  Project:        {cfg.get('repo', '—')}")
    print(f"  Organization:   {cfg.get('org', '—')}")
    local_path = cfg.get("local_path")
    if local_path:
        print(f"  Local path:     {local_path}")
    print(f"  Domain:         {domain}")
    print()

    # Website
    ws = cfg.get("website", {})
    if ws:
        ws_type = ws.get("type", "—")
        ws_domain = ws.get("domain") or domain
        print(f"  Website:        {ws_type} ({ws_domain})")
        addons = ws.get("addons", [])
        if addons:
            print(f"  Website addons: {', '.join(addons)}")
    else:
        print("  Website:        —")

    # Backend
    be = cfg.get("backend", {})
    if be.get("enabled"):
        print(f"  Backend:        yes ({be.get('domain', f'backend.{domain}')})")
        if be.get("docs_domain"):
            print(f"  API docs:       {be['docs_domain']}")
        envs = be.get("environments", {})
        active_envs = [e for e in ("staging", "testing") if envs.get(e)]
        if active_envs:
            print(f"  Environments:   {', '.join(active_envs)}")
    else:
        print("  Backend:        no")

    # Admin sites
    admin_sites = cfg.get("admin_sites", {})
    for site_type in ("admin", "dashboard"):
        s = admin_sites.get(site_type, {})
        if s.get("enabled"):
            print(f"  {site_type.title():14s}  yes ({s.get('domain', f'{site_type}.{domain}')})")
        else:
            print(f"  {site_type.title():14s}  no")

    # Auth
    providers = cfg.get("auth_providers", [])
    if providers:
        print(f"  Auth:           {', '.join(providers)}")
    else:
        print("  Auth:           —")

    print()



# ── Commands ────────────────────────────────────────────────────────────────


def cmd_show(config_name: str | None) -> None:
    configs = list_configs()
    if not configs:
        print("No configurations found.")
        return

    if config_name and config_name in configs:
        show_config(config_name)
        return

    if config_name and config_name not in configs:
        print(f"Configuration '{config_name}' not found.")
        return

    try:
        chosen = ask_choice(None, "Which configuration do you want to view?", configs)
    except UserQuit:
        return
    show_config(chosen)


def cmd_delete(config_name: str | None) -> None:
    configs = list_configs()
    if not configs:
        print("No configurations found.")
        return

    if config_name and config_name not in configs:
        print(f"Configuration '{config_name}' not found.")
        return

    if not config_name:
        print("Available configurations:")
        for c in configs:
            print(f"  {c}")
        print("Usage: configurator --delete <name>")
        return

    delete_config(config_name)
    print(f"Configuration '{config_name}' deleted.")


def _git_author(path: Path) -> dict[str, str]:
    """Read git user.name and user.email from the given repo path."""
    author: dict[str, str] = {}
    for field in ("name", "email"):
        try:
            result = subprocess.run(
                ["git", "-C", str(path), "config", f"user.{field}"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                author[field] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return author


def _migrate_draft(cfg: dict) -> dict:
    """Migrate a draft config from an older configurator version to the current one.

    Updates the configurator_version field and applies any schema changes.
    """
    draft_version = cfg.get("configurator_version", "0.0.0")
    if draft_version == __version__:
        return cfg

    # Ensure change_history list exists
    if "_change_history" not in cfg:
        cfg["_change_history"] = []

    cfg["configurator_version"] = __version__
    return cfg


def cmd_configure() -> None:
    from configurator.web import serve_editor

    cwd = Path.cwd()
    manifest = _load_manifest(cwd)
    author = _git_author(cwd)

    if manifest:
        project_name = manifest.get("project", {}).get("name", cwd.name)
        manifest_version = manifest.get("configurator_version")

        print(f"  Found deployed project: {project_name}")
        if manifest_version:
            print(f"  Deployed with configurator v{manifest_version}")

        if manifest_version and _parse_version(manifest_version) < _parse_version(__version__):
            _show_new_options(manifest_version)

        name = project_name
        saved = load_config(name)

        if saved and saved.get("configurator_version"):
            # Existing draft — migrate if needed, reuse as-is
            cfg = _migrate_draft(saved)
            cfg["local_path"] = str(cwd.resolve())
            print(f"  Resuming draft (v{saved.get('configurator_version', '?')})")
        else:
            # No draft — create from manifest
            cfg = _manifest_to_config(manifest, saved=saved or None)
            cfg["local_path"] = str(cwd.resolve())
            cfg["_change_history"] = []

        if "org" not in cfg:
            org = _detect_org_from_git(cwd)
            if org:
                cfg["org"] = org

        save_config(name, cfg)

        deployed = _deployed_keys_from_manifest(manifest)
        if cfg.get("org"):
            deployed.add("org")
        urls = _extract_urls_from_manifest(manifest)
        live = _check_live_domains(manifest)
        action = serve_editor(name, cfg, deployed_keys=deployed, urls=urls, live_domains=live, author=author)
        print(f"ACTION:{action}")
        return

    # No manifest — use cwd name or first saved config
    name = cwd.name
    saved = load_config(name)

    if saved and saved.get("configurator_version"):
        # Existing draft — migrate if needed
        cfg = _migrate_draft(saved)
        cfg["local_path"] = str(cwd.resolve())
        print(f"  Resuming draft (v{saved.get('configurator_version', '?')})")
    else:
        cfg = saved or {}
        cfg["_change_history"] = cfg.get("_change_history", [])

    save_config(name, cfg)
    action = serve_editor(name, cfg, deployed_keys=set(), author=author)
    print(f"ACTION:{action}")


# ── Keychain credentials ───────────────────────────────────────────────────


def _keychain_get(key: str) -> str | None:
    """Read a credential from macOS keychain. Returns None if not found."""
    from configurator.features.credentials import KEYCHAIN_SERVICE
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", key, "-w"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def _keychain_set(key: str, value: str) -> None:
    """Store a credential in macOS keychain (add or update)."""
    from configurator.features.credentials import KEYCHAIN_SERVICE
    subprocess.run(
        ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", key],
        capture_output=True,
    )
    subprocess.run(
        ["security", "add-generic-password", "-s", KEYCHAIN_SERVICE, "-a", key, "-w", value],
        check=True, capture_output=True,
    )


def cmd_set_credentials() -> None:
    """Prompt for each credential and store in macOS keychain."""
    import getpass
    from configurator.features.credentials import KEYCHAIN_SERVICE, CREDENTIAL_DEFS

    print(f"\n  Set credentials (stored in macOS Keychain as service '{KEYCHAIN_SERVICE}')\n")

    for key, label, reason in CREDENTIAL_DEFS:
        existing = _keychain_get(key)
        if existing:
            masked = existing[:4] + "..." + existing[-4:] if len(existing) > 12 else "****"
            prompt = f"  {label} [{masked}]: "
        else:
            prompt = f"  {label} ({reason}): "

        value = getpass.getpass(prompt=prompt)
        if value:
            _keychain_set(key, value)
            print(f"    saved")
        elif existing:
            print(f"    (kept existing)")
        else:
            print(f"    (skipped)")

    print("\n  Done.\n")


# ── Entry point ─────────────────────────────────────────────────────────────


def cmd_deploy_plan() -> None:
    """Output a JSON deploy plan showing what to skip/update/add."""
    from configurator.deploy import deploy_plan

    cwd = Path.cwd()
    manifest = _load_manifest(cwd)
    if not manifest:
        print(json.dumps({"error": "no manifest found at .site/manifest.json"}))
        return

    project_name = manifest.get("project", {}).get("name", cwd.name)
    cfg = load_config(project_name)
    if not cfg:
        print(json.dumps({"error": f"no config found for '{project_name}'"}))
        return

    plan = deploy_plan(cfg, manifest)
    print(json.dumps(plan, indent=2))


def cmd_snapshot() -> None:
    """Copy the current config draft into .site/deployments/ as a timestamped file."""
    cwd = Path.cwd()
    site_dir = cwd / ".site"
    if not site_dir.exists():
        print("No .site directory found.")
        return

    manifest = _load_manifest(cwd)
    if not manifest:
        print("No manifest found.")
        return

    project_name = manifest.get("project", {}).get("name", cwd.name)
    draft_path = config_path(project_name)
    if not draft_path.exists():
        print(f"No draft found for '{project_name}'.")
        return

    deployments_dir = site_dir / "deployments"
    deployments_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M-%S")
    snapshot_path = deployments_dir / f"{ts}-deployment.json"
    shutil.copy2(str(draft_path), str(snapshot_path))
    print(f"  Snapshot: {snapshot_path.name}")


def cmd_schema() -> None:
    """Dump all config identifiers from all features."""
    from configurator.features import discover_features

    features = discover_features()
    all_ids: dict[str, str] = {}
    for feature in features:
        all_ids.update(feature.config_identifiers())

    if not all_ids:
        print("No identifiers registered.")
        return

    max_id = max(len(k) for k in all_ids)
    print()
    print(f"  {'Identifier':<{max_id}}  Type")
    print(f"  {'-' * max_id}  ------")
    for ident, vtype in sorted(all_ids.items()):
        print(f"  {ident:<{max_id}}  {vtype}")
    print()
    print(f"  {len(all_ids)} identifiers across {sum(1 for f in features if f.config_identifiers())} features")
    print()


def cmd_repair() -> None:
    """Check each deployed feature and report status."""
    from configurator.deploy import feature_versions
    from configurator.features import discover_features

    cwd = Path.cwd()
    manifest = _load_manifest(cwd)
    if not manifest:
        print("No manifest found at .site/manifest.json")
        print("Run this from a project directory with an existing deployment.")
        return

    project_name = manifest.get("project", {}).get("name", cwd.name)
    manifest_versions = manifest.get("feature_versions", {})
    current_versions = feature_versions()
    features = discover_features()

    print()
    print(f"  Repair check: {project_name}")
    print()

    issues: list[dict] = []

    for feature in features:
        meta = feature.meta()
        deployed = feature.deployed_keys(manifest)

        if not deployed:
            continue

        mv = manifest_versions.get(meta.id)
        cv = current_versions[meta.id]

        if mv == cv:
            print(f"  [ok]     {meta.label:20s} v{cv}")
        elif mv:
            print(f"  [update] {meta.label:20s} v{mv} -> v{cv}")
            issues.append({"id": meta.id, "action": "update", "from": mv, "to": cv})
        else:
            print(f"  [check]  {meta.label:20s} v{cv} (no version in manifest)")
            issues.append({"id": meta.id, "action": "verify", "version": cv})

    print()
    if issues:
        print(f"  {len(issues)} feature(s) need attention.")
        print(json.dumps(issues, indent=2))
    else:
        print("  All deployed features are up to date.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive project configurator")
    parser.add_argument("--configure", action="store_true", default=True, help="Configure a project (default)")
    parser.add_argument("--show", nargs="?", const="", metavar="NAME", help="Show a configuration")
    parser.add_argument("--delete", nargs="?", const="", metavar="NAME", help="Delete a configuration")
    parser.add_argument("--deploy-plan", action="store_true", help="Output deploy plan as JSON")
    parser.add_argument("--repair", action="store_true", help="Check deployed features and report status")
    parser.add_argument("--schema", action="store_true", help="Show all config identifiers")
    parser.add_argument("--snapshot", action="store_true", help="Save current draft to .site/deployments/")
    parser.add_argument("--set-credentials", action="store_true", help="Set deployment credentials in macOS Keychain")
    parser.add_argument("--version", action="store_true", help="Show version")
    args = parser.parse_args()

    if args.version:
        print(f"configurator {__version__}")
        return

    if args.set_credentials:
        cmd_set_credentials()
        return

    if args.deploy_plan:
        cmd_deploy_plan()
        return

    if args.repair:
        cmd_repair()
        return

    if args.schema:
        cmd_schema()
        return

    if args.snapshot:
        cmd_snapshot()
        return

    if args.show is not None:
        cmd_show(args.show or None)
        return

    if args.delete is not None:
        cmd_delete(args.delete or None)
        return

    cmd_configure()
