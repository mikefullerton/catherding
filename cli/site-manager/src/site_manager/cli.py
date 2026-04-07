"""CLI entry point — routes subcommands to handlers."""

import argparse
import os
import sys

from pathlib import Path

from site_manager import __version__, DEVELOPER_FLAG

# Commands that require a Claude Code session
CLAUDE_COMMANDS = {"init", "migrate", "go-live", "deploy", "seed-admin", "update", "verify", "repair", "add"}


def _is_inside_claude() -> bool:
    """Check if we're running inside a Claude Code session."""
    return bool(os.environ.get("CLAUDE_CODE"))


def _require_claude(command: str):
    """Exit with a helpful message if not inside Claude."""
    if _is_inside_claude():
        return
    cwd = os.getcwd()
    print(f"site-manager {command} requires a Claude Code session.\n")
    print(f"  claude \"site-manager --site {cwd} {command}\"")
    sys.exit(1)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="site-manager",
        description="Manage multi-site web projects",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Commands marked (requires Claude) must be run inside a Claude Code session.",
    )
    parser.add_argument("--version", action="version", version=f"site-manager {__version__}")
    parser.add_argument("--developer-mode", choices=["on", "off"],
                        help="Enable/disable tool developer mode")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output raw JSON")
    parser.add_argument("--site", metavar="PATH", help="Path to site directory (default: current directory)")

    sub = parser.add_subparsers(dest="command")

    # --- terminal commands ---
    sub.add_parser("status", help="Check health of all services")

    manifest_p = sub.add_parser("manifest", help="View or validate manifest")
    manifest_p.add_argument("action", nargs="?", default="show",
                            choices=["show", "validate"],
                            help="Action (default: show)")

    # --- claude commands ---
    init_p = sub.add_parser("init", help="Scaffold a new project (requires Claude)")
    init_p.add_argument("domain", nargs="?", help="Domain name")

    migrate_p = sub.add_parser("migrate", help="Set up in an existing repo (requires Claude)")
    migrate_p.add_argument("domain", nargs="?", help="Domain name")

    sub.add_parser("go-live", help="Connect custom domain to deployed project (requires Claude)")

    deploy_p = sub.add_parser("deploy", help="Deploy services (requires Claude)")
    deploy_p.add_argument("service", nargs="?", default="all",
                          choices=["all", "backend", "main", "admin", "dashboard"],
                          help="Service to deploy (default: all)")

    sub.add_parser("seed-admin", help="Create initial admin account (requires Claude)")

    sub.add_parser("update", help="Re-scaffold with latest templates (requires Claude)")

    verify_p = sub.add_parser("verify", help="Run full verification suite (requires Claude)")
    verify_p.add_argument("--manifest", action="store_true", help="Manifest integrity + API health only")
    verify_p.add_argument("--dns", action="store_true", help="DNS resolution only")
    verify_p.add_argument("--e2e", action="store_true", help="Browser-based verification only")
    verify_p.add_argument("--smoke", action="store_true", help="Functional smoke tests only")

    sub.add_parser("repair", help="Fix issues found by verify (requires Claude)")

    add_p = sub.add_parser("add", help="Add capabilities to an existing project (requires Claude)")
    add_p.add_argument("description", nargs="*", default=[], help="What to add (e.g., 'github auth', 'admin site')")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    json_out = args.output_json

    # Change to site directory if specified
    if args.site:
        site_path = Path(args.site).resolve()
        if not site_path.is_dir():
            print(f"error: {args.site} is not a directory", file=sys.stderr)
            sys.exit(1)
        os.chdir(site_path)

    # Handle --developer-mode before anything else
    if args.developer_mode:
        flag = Path(DEVELOPER_FLAG).expanduser()
        if args.developer_mode == "on":
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.touch()
            print("Developer mode enabled. Repair will report issues without fixing.")
        else:
            flag.unlink(missing_ok=True)
            print("Developer mode disabled. Repair will fix issues automatically.")
        if args.command is None:
            sys.exit(0)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # Gate Claude-only commands
    if args.command in CLAUDE_COMMANDS:
        _require_claude(args.command)

    if args.command == "status":
        from site_manager.status import show_status
        show_status(output_json=json_out)

    elif args.command == "manifest":
        from site_manager.manifest import show_manifest, validate_manifest
        if args.action == "validate":
            validate_manifest(output_json=json_out)
        else:
            show_manifest(output_json=json_out)

    elif args.command == "init":
        from site_manager.claude import invoke_claude
        domain = args.domain or ""
        invoke_claude(f"init {domain}".strip())

    elif args.command == "migrate":
        from site_manager.claude import invoke_claude
        domain = args.domain or ""
        invoke_claude(f"migrate {domain}".strip())

    elif args.command == "go-live":
        from site_manager.claude import invoke_claude
        invoke_claude("go-live")

    elif args.command == "deploy":
        from site_manager.deploy import deploy_all, deploy_single
        if args.service == "all":
            deploy_all(output_json=json_out)
        else:
            deploy_single(args.service, output_json=json_out)

    elif args.command == "seed-admin":
        from site_manager.claude import invoke_claude
        invoke_claude("seed-admin")

    elif args.command == "update":
        from site_manager.claude import invoke_claude
        invoke_claude("update")

    elif args.command == "verify":
        from site_manager.verify_all import run_verify
        has_flags = args.manifest or args.dns or args.e2e or args.smoke
        if has_flags:
            run_verify(
                run_manifest=args.manifest,
                run_dns=args.dns,
                run_e2e=args.e2e,
                run_smoke=args.smoke,
                output_json=json_out,
            )
        else:
            run_verify(output_json=json_out)

    elif args.command == "repair":
        from site_manager.repair import run_repair
        run_repair(output_json=json_out)

    elif args.command == "add":
        from site_manager.claude import invoke_claude
        desc = " ".join(args.description) if args.description else ""
        invoke_claude(f"add {desc}".strip())

    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
