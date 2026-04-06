"""CLI entry point — routes subcommands to handlers."""

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="site-manager",
        description="Manage multi-site web projects — deploy, status, verify, test",
    )
    parser.add_argument("--version", action="version", version="site-manager 0.1.0")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output raw JSON")

    sub = parser.add_subparsers(dest="command")

    # --- init (Claude) ---
    init_p = sub.add_parser("init", help="Scaffold a new project (uses Claude)")
    init_p.add_argument("domain", nargs="?", help="Domain name")

    # --- deploy ---
    deploy_p = sub.add_parser("deploy", help="Deploy services")
    deploy_p.add_argument("service", nargs="?", default="all",
                          choices=["all", "backend", "main", "admin", "dashboard"],
                          help="Service to deploy (default: all)")

    # --- status ---
    sub.add_parser("status", help="Check health of all services")

    # --- manifest ---
    manifest_p = sub.add_parser("manifest", help="View or validate site-manifest.json")
    manifest_p.add_argument("action", nargs="?", default="show",
                            choices=["show", "validate"],
                            help="Action (default: show)")

    # --- seed-admin (Claude) ---
    sub.add_parser("seed-admin", help="Create initial admin account (uses Claude)")

    # --- update (Claude) ---
    sub.add_parser("update", help="Re-scaffold with latest templates (uses Claude)")

    # --- verify ---
    sub.add_parser("verify", help="Run post-deployment verification")

    # --- test ---
    test_p = sub.add_parser("test", help="Run smoke or validation tests")
    test_p.add_argument("test_type", nargs="?", default="smoke",
                        choices=["smoke", "validate"],
                        help="Test type (default: smoke)")
    test_p.add_argument("--admin-email", help="Admin email (required for validate)")
    test_p.add_argument("--admin-password", help="Admin password (required for validate)")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    json_out = args.output_json

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "init":
        from site_manager.claude import invoke_claude
        domain = args.domain or ""
        invoke_claude(f"init {domain}".strip())

    elif args.command == "deploy":
        from site_manager.deploy import deploy_all, deploy_single
        if args.service == "all":
            deploy_all(output_json=json_out)
        else:
            deploy_single(args.service, output_json=json_out)

    elif args.command == "status":
        from site_manager.status import show_status
        show_status(output_json=json_out)

    elif args.command == "manifest":
        from site_manager.manifest import show_manifest, validate_manifest
        if args.action == "validate":
            validate_manifest(output_json=json_out)
        else:
            show_manifest(output_json=json_out)

    elif args.command == "seed-admin":
        from site_manager.claude import invoke_claude
        invoke_claude("seed-admin")

    elif args.command == "update":
        from site_manager.claude import invoke_claude
        invoke_claude("update")

    elif args.command == "verify":
        from site_manager.verify import run_verify
        run_verify(output_json=json_out)

    elif args.command == "test":
        if args.test_type == "validate":
            if not args.admin_email or not args.admin_password:
                print("error: --admin-email and --admin-password required for validate", file=sys.stderr)
                sys.exit(1)
            from site_manager.test import run_validate
            run_validate(args.admin_email, args.admin_password, output_json=json_out)
        else:
            from site_manager.test import run_smoke
            run_smoke(output_json=json_out)

    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
