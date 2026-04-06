"""CLI entry point — routes subcommands to handlers."""

import argparse
import sys

from webinator import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="webinator",
        description="Web infrastructure management CLI",
        epilog="* invokes Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"webinator {__version__}")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output raw JSON")

    sub = parser.add_subparsers(dest="command")

    # --- status ---
    sub.add_parser("status", help="Show status of all services")

    # --- setup (Claude) ---
    setup_p = sub.add_parser("setup", help="* Interactive setup for services")
    setup_p.add_argument("service", nargs="?", choices=["cloudflare", "railway", "godaddy", "github"],
                         help="Specific service to setup")

    # --- domains ---
    domains_p = sub.add_parser("domains", help="Domain portfolio management")
    domains_sub = domains_p.add_subparsers(dest="domains_action")

    dl = domains_sub.add_parser("list", help="List domains with optional filters")
    dl.add_argument("--status", help="Filter by status (e.g. ACTIVE, EXPIRED)")
    dl.add_argument("--expiring", action="store_true", help="Domains expiring within 30 days")
    dl.add_argument("--privacy-off", action="store_true", help="Domains with privacy disabled")
    dl.add_argument("--autorenew-off", action="store_true", help="Domains with auto-renew disabled")
    dl.add_argument("--name", help="Filter by name substring")

    ds = domains_sub.add_parser("search", help="Search domains by name")
    ds.add_argument("query", help="Search query")

    di = domains_sub.add_parser("info", help="Show detailed domain info")
    di.add_argument("domain", help="Domain name")

    domains_sub.add_parser("privacy-check", help="Audit domain security settings")

    domains_sub.add_parser("chat", help="* Discuss your domain portfolio")

    # --- dns ---
    dns_p = sub.add_parser("dns", help="DNS record management")
    dns_sub = dns_p.add_subparsers(dest="dns_action")

    dns_list = dns_sub.add_parser("list", help="List DNS records for a domain")
    dns_list.add_argument("domain", help="Domain name")

    dns_add = dns_sub.add_parser("add", help="* Add a DNS record")
    dns_add.add_argument("domain", help="Domain name")

    dns_update = dns_sub.add_parser("update", help="* Update a DNS record")
    dns_update.add_argument("domain", help="Domain name")

    dns_delete = dns_sub.add_parser("delete", help="* Delete a DNS record")
    dns_delete.add_argument("domain", help="Domain name")

    # --- configure ---
    conf_p = sub.add_parser("configure", help="Manage API credentials")
    conf_sub = conf_p.add_subparsers(dest="configure_service")

    gd_p = conf_sub.add_parser("godaddy", help="GoDaddy API credentials")
    gd_sub = gd_p.add_subparsers(dest="godaddy_action")

    gd_sub.add_parser("get", help="Show current config (masked)")
    gd_set = gd_sub.add_parser("set", help="Set API key and secret")
    gd_set.add_argument("key", help="API key")
    gd_set.add_argument("secret", help="API secret")
    gd_sub.add_parser("test", help="Test API connectivity")
    gd_env = gd_sub.add_parser("set-env", help="Set environment (production|ote)")
    gd_env.add_argument("env", choices=["production", "ote"])

    cf_p = conf_sub.add_parser("cloudflare", help="Cloudflare API token")
    cf_sub = cf_p.add_subparsers(dest="cloudflare_action")

    cf_sub.add_parser("get", help="Show current config (masked)")
    cf_set = cf_sub.add_parser("set", help="Set API token")
    cf_set.add_argument("token", help="API token")
    cf_sub.add_parser("test", help="Test API connectivity")

    # --- connect (Claude) ---
    connect_p = sub.add_parser("connect", help="* GoDaddy → Cloudflare → Railway workflow")
    connect_p.add_argument("domain", help="Domain to connect")

    # --- deploy ---
    deploy_p = sub.add_parser("deploy", help="Deployment management")
    deploy_sub = deploy_p.add_subparsers(dest="deploy_action")

    deploy_sub.add_parser("status", help="Check deployment health")
    deploy_sub.add_parser("push", help="Deploy backend + frontend")
    deploy_sub.add_parser("init", help="* Scaffold full-stack web app")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    json_out = args.output_json

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "status":
        from webinator.status import show_status
        show_status(output_json=json_out)

    elif args.command == "setup":
        from webinator.claude import invoke_claude
        service = args.service or ""
        invoke_claude(f"setup {service}".strip())

    elif args.command == "domains":
        action = args.domains_action
        if action == "chat":
            from webinator.claude import invoke_claude
            invoke_claude("domains chat")
        else:
            from webinator.domains import list_domains, search_domains, info_domain, privacy_check
            if action is None or action == "list":
                list_domains(
                    status=getattr(args, "status", None),
                    expiring=getattr(args, "expiring", False),
                    privacy_off=getattr(args, "privacy_off", False),
                    autorenew_off=getattr(args, "autorenew_off", False),
                    name=getattr(args, "name", None),
                    output_json=json_out,
                )
            elif action == "search":
                search_domains(args.query, output_json=json_out)
            elif action == "info":
                info_domain(args.domain, output_json=json_out)
            elif action == "privacy-check":
                privacy_check(output_json=json_out)

    elif args.command == "dns":
        action = args.dns_action
        if action == "list":
            from webinator.dns import list_dns
            list_dns(args.domain, output_json=json_out)
        elif action in ("add", "update", "delete"):
            from webinator.claude import invoke_claude
            invoke_claude(f"dns {action} {args.domain}")
        else:
            print("error: dns requires an action (list, add, update, delete)", file=sys.stderr)
            sys.exit(1)

    elif args.command == "configure":
        from webinator.configure import (
            godaddy_get, godaddy_set, godaddy_set_env, godaddy_test,
            cloudflare_get, cloudflare_set, cloudflare_test,
        )
        service = args.configure_service
        if service == "godaddy":
            action = args.godaddy_action
            if action is None or action == "get":
                godaddy_get()
            elif action == "set":
                godaddy_set(args.key, args.secret)
            elif action == "set-env":
                godaddy_set_env(args.env)
            elif action == "test":
                godaddy_test()
        elif service == "cloudflare":
            action = args.cloudflare_action
            if action is None or action == "get":
                cloudflare_get()
            elif action == "set":
                cloudflare_set(args.token)
            elif action == "test":
                cloudflare_test()
        else:
            parser.parse_args(["configure", "--help"])

    elif args.command == "connect":
        from webinator.claude import invoke_claude
        invoke_claude(f"connect {args.domain}")

    elif args.command == "deploy":
        action = args.deploy_action
        if action == "init":
            from webinator.claude import invoke_claude
            invoke_claude("deploy init")
        elif action == "push":
            from webinator.deploy import deploy_push
            deploy_push(output_json=json_out)
        elif action is None or action == "status":
            from webinator.deploy import deploy_status
            deploy_status(output_json=json_out)

    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
