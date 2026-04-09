"""Interactive project configurator — creates deployment specs for Claude."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import questionary
from questionary import Choice

CONFIG_DIR = Path.home() / ".configurator"
TOTAL_QUESTIONS = 8

ORGS = ["mikefullerton", "agentic-cookbook"]


class UserQuit(Exception):
    pass


# ── Config I/O ──────────────────────────────────────────────────────────────


def config_path(name: str) -> Path:
    return CONFIG_DIR / f"{name}.json"


def list_configs() -> list[str]:
    if not CONFIG_DIR.exists():
        return []
    return sorted(p.stem for p in CONFIG_DIR.glob("*.json"))


def load_config(name: str) -> dict:
    path = config_path(name)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_config(name: str, cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_path(name).write_text(json.dumps(cfg, indent=2) + "\n")


def delete_config(name: str) -> None:
    path = config_path(name)
    if path.exists():
        path.unlink()


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

    # Frontend auth
    fa = cfg.get("frontend_auth", {})
    features = fa.get("features", [])
    if features:
        print(f"  Frontend auth:  {', '.join(features)}")
        strategy = fa.get("sqlite_strategy")
        if strategy:
            print(f"  SQLite:         {strategy}")

    print()


# ── Prompt helpers ──────────────────────────────────────────────────────────


QUIT_LABEL = "Quit"


def prefix(n: int) -> str:
    return f"[{n}/{TOTAL_QUESTIONS}]"


def ask_text(question_num: int, message: str, *, required: bool = False, default: str = "") -> str:
    full = f"{prefix(question_num)} {message}"
    while True:
        answer = questionary.text(full, default=default).ask()
        if answer is None:
            raise UserQuit
        answer = answer.strip()
        if answer.lower() == "q":
            raise UserQuit
        if required and not answer:
            print("  This question is required.")
            continue
        return answer


def ask_choice(question_num: int | None, message: str, choices: list[str], *, default: str | None = None, required: bool = False) -> str:
    if question_num is not None:
        full = f"{prefix(question_num)} {message}"
    else:
        full = message
    items = [Choice(c, value=c) for c in choices] + [Choice(QUIT_LABEL, value=QUIT_LABEL)]
    answer = questionary.select(full, choices=items, default=default).ask()
    if answer is None or answer == QUIT_LABEL:
        raise UserQuit
    return answer


def ask_list(question_num: int | None, message: str, choices: list[str], *, defaults: list[str] | None = None, min_required: int = 0) -> list[str]:
    if question_num is not None:
        full = f"{prefix(question_num)} {message}"
    else:
        full = message

    defaults = defaults or []
    items = [Choice(c, checked=(c in defaults)) for c in choices] + [Choice(QUIT_LABEL, checked=False)]

    while True:
        answer = questionary.checkbox(full, choices=items).ask()
        if answer is None or QUIT_LABEL in answer:
            raise UserQuit
        if len(answer) < min_required:
            print(f"  Please select at least {min_required}.")
            continue
        return answer


def ask_clarifying_text(message: str, *, default: str = "") -> str:
    answer = questionary.text(f"  {message}", default=default).ask()
    if answer is None:
        raise UserQuit
    answer = answer.strip()
    if answer.lower() == "q":
        raise UserQuit
    return answer


def ask_clarifying_choice(message: str, choices: list[str], *, default: str | None = None) -> str:
    return ask_choice(None, f"  {message}", choices, default=default)


def ask_clarifying_list(message: str, choices: list[str], *, defaults: list[str] | None = None) -> list[str]:
    return ask_list(None, f"  {message}", choices, defaults=defaults)


# ── Question flow ───────────────────────────────────────────────────────────


def run_questions(name: str | None, cfg: dict) -> str:
    """Run through all questions. Returns the config name."""

    # Q1: repo name
    default_repo = cfg.get("repo", name or "")
    repo = ask_text(1, "What is the name of the GitHub repo for this project?", required=True, default=default_repo)
    cfg["repo"] = repo

    # For a new project, set the name now and save
    if name is None:
        name = repo
    save_config(name, cfg)

    # Q2: organization
    default_org = cfg.get("org")
    org_choices = ORGS + ["other"]
    org_default = default_org if default_org in org_choices else None
    org = ask_choice(2, "What is the organization for this GitHub repo?", org_choices, default=org_default, required=True)
    if org == "other":
        org = ask_clarifying_text("What is the name of the organization?", default=default_org if default_org not in ORGS else "")
        if not org:
            org = "other"
    cfg["org"] = org
    save_config(name, cfg)

    # Q3: domain
    default_domain = cfg.get("domain", "")
    domain = ask_text(3, "What is the domain name for this family of websites and services?", default=default_domain)
    cfg["domain"] = domain
    save_config(name, cfg)

    # Q4: website type
    ws = cfg.get("website", {})
    default_ws_type = ws.get("type")
    ws_type = ask_choice(4, "What type of user-facing website do you want to deploy?", ["new", "existing"], default=default_ws_type, required=True)
    ws["type"] = ws_type

    # Q4.1: website domain
    ws_domain_default = ws.get("domain") or domain
    ws_domain = ask_clarifying_text(f"What domain name should we configure for this site? (default: {domain})", default=ws_domain_default)
    ws["domain"] = ws_domain or domain

    # Q4.2: website addons
    addon_choices = ["authentication", "sqlite database", "key-value storage", "file storage"]
    addon_defaults = ws.get("addons", [])
    addons = ask_clarifying_list(f"What addons do you want for {ws.get('domain', domain)}?", addon_choices, defaults=addon_defaults)
    ws["addons"] = addons

    cfg["website"] = ws
    save_config(name, cfg)

    # Q5: backend
    be = cfg.get("backend", {})
    be_default = "yes" if be.get("enabled", False) else "no"
    be_answer = ask_choice(5, f"Do you want a backend for {domain}?", ["yes", "no"], default=be_default)
    be["enabled"] = be_answer == "yes"

    if be["enabled"]:
        be_domain_default = be.get("domain") or f"backend.{domain}"
        be_domain = ask_clarifying_text(f"What domain name should we configure for the backend? (default: backend.{domain})", default=be_domain_default)
        be["domain"] = be_domain or f"backend.{domain}"
    else:
        be.pop("domain", None)

    cfg["backend"] = be
    save_config(name, cfg)

    # Q6: admin sites
    admin_sites = cfg.get("admin_sites", {})
    admin_choices = ["admin", "dashboard"]
    admin_defaults = [s for s in admin_choices if admin_sites.get(s, {}).get("enabled")]
    selected_admin = ask_list(6, f"What admin sites do you want for {domain}?", admin_choices, defaults=admin_defaults)

    for site_type in admin_choices:
        s = admin_sites.get(site_type, {})
        if site_type in selected_admin:
            s["enabled"] = True
            s_domain_default = s.get("domain") or f"{site_type}.{domain}"
            s_domain = ask_clarifying_text(f"What domain name should we configure for {site_type}? (default: {site_type}.{domain})", default=s_domain_default)
            s["domain"] = s_domain or f"{site_type}.{domain}"
        else:
            s["enabled"] = False
            s.pop("domain", None)
        admin_sites[site_type] = s

    cfg["admin_sites"] = admin_sites
    save_config(name, cfg)

    # Q7: auth providers
    auth_choices = ["email/password", "github", "google", "apple"]
    auth_defaults = cfg.get("auth_providers", ["email/password"])
    providers = ask_list(7, f"What types of authentication should we configure for {domain}?", auth_choices, defaults=auth_defaults)
    cfg["auth_providers"] = providers
    save_config(name, cfg)

    # Q8: frontend auth (conditional on Q4 — always true for now since Q4 is required)
    fa = cfg.get("frontend_auth", {})
    fa_choices = ["login / register button"]
    fa_defaults = fa.get("features", [])
    features = ask_list(8, f"What authentication should the front-end website for {domain} have?", fa_choices, defaults=fa_defaults)
    fa["features"] = features

    # Follow-up: if auth features selected but no backend and no sqlite addon
    has_backend = cfg.get("backend", {}).get("enabled", False)
    has_sqlite = "sqlite database" in cfg.get("website", {}).get("addons", [])
    if features and not has_backend and not has_sqlite:
        strategy_choices = ["this is already available", "deploy this", "claude should follow up during deployment"]
        strategy_default = fa.get("sqlite_strategy")
        strategy = ask_clarifying_choice(
            "Authentication requires a SQLite database on the front end.",
            strategy_choices,
            default=strategy_default,
        )
        fa["sqlite_strategy"] = strategy
    else:
        fa.pop("sqlite_strategy", None)

    cfg["frontend_auth"] = fa
    save_config(name, cfg)

    return name


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


def cmd_configure() -> None:
    configs = list_configs()
    menu = configs + ["New configuration"]

    try:
        chosen = ask_choice(None, "Choose a configuration:", menu)
    except UserQuit:
        return

    if chosen == "New configuration":
        name = None
        cfg: dict = {}
    else:
        name = chosen
        cfg = load_config(name)

    questions_started = False
    try:
        questions_started = True
        name = run_questions(name, cfg)
    except UserQuit:
        if questions_started and name:
            try:
                delete_it = ask_choice(None, f"Delete the configuration '{name}'?", ["no", "yes"], default="no")
            except UserQuit:
                delete_it = "no"
            if delete_it == "yes":
                delete_config(name)
                print(f"Configuration '{name}' deleted.")
            else:
                print(f"Configuration '{name}' saved (partial).")
        return

    # Show the completed config
    show_config(name)

    # Confirm
    try:
        ok = ask_choice(None, "Does that look ok?", ["yes", "no"], default="yes")
    except UserQuit:
        print(f"Configuration '{name}' saved.")
        return

    if ok == "no":
        # Restart with current answers pre-populated
        cfg = load_config(name)
        try:
            run_questions(name, cfg)
            show_config(name)
        except UserQuit:
            print(f"Configuration '{name}' saved.")
            return

    command = f"/configurator {name}"
    try:
        subprocess.run(["pbcopy"], input=command.encode(), check=True)
        print(f"To deploy, run '{command}' in Claude (command copied to clipboard)")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print(f"To deploy, run '{command}' in Claude")


# ── Entry point ─────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive project configurator")
    parser.add_argument("--configure", action="store_true", default=True, help="Configure a project (default)")
    parser.add_argument("--show", nargs="?", const="", metavar="NAME", help="Show a configuration")
    parser.add_argument("--version", action="store_true", help="Show version")
    args = parser.parse_args()

    if args.version:
        from configurator import __version__
        print(f"configurator {__version__}")
        return

    if args.show is not None:
        cmd_show(args.show or None)
        return

    cmd_configure()
