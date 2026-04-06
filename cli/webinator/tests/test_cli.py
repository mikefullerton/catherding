"""Tests for webinator CLI argument parsing and command routing."""

import pytest
from webinator.cli import _build_parser


class TestParser:
    def setup_method(self):
        self.parser = _build_parser()

    def test_no_args_defaults_to_none_command(self):
        args = self.parser.parse_args([])
        assert args.command is None

    def test_version_flag(self):
        with pytest.raises(SystemExit) as exc:
            self.parser.parse_args(["--version"])
        assert exc.value.code == 0

    def test_json_flag(self):
        args = self.parser.parse_args(["--json", "status"])
        assert args.output_json is True

    def test_status(self):
        args = self.parser.parse_args(["status"])
        assert args.command == "status"

    # --- domains ---
    def test_domains_list(self):
        args = self.parser.parse_args(["domains", "list"])
        assert args.command == "domains"
        assert args.domains_action == "list"

    def test_domains_list_filters(self):
        args = self.parser.parse_args([
            "domains", "list",
            "--status", "ACTIVE",
            "--expiring",
            "--privacy-off",
            "--autorenew-off",
            "--name", "example",
        ])
        assert args.status == "ACTIVE"
        assert args.expiring is True
        assert args.privacy_off is True
        assert args.autorenew_off is True
        assert args.name == "example"

    def test_domains_search(self):
        args = self.parser.parse_args(["domains", "search", "example"])
        assert args.domains_action == "search"
        assert args.query == "example"

    def test_domains_info(self):
        args = self.parser.parse_args(["domains", "info", "example.com"])
        assert args.domains_action == "info"
        assert args.domain == "example.com"

    def test_domains_privacy_check(self):
        args = self.parser.parse_args(["domains", "privacy-check"])
        assert args.domains_action == "privacy-check"

    def test_domains_chat(self):
        args = self.parser.parse_args(["domains", "chat"])
        assert args.domains_action == "chat"

    # --- dns ---
    def test_dns_list(self):
        args = self.parser.parse_args(["dns", "list", "example.com"])
        assert args.command == "dns"
        assert args.dns_action == "list"
        assert args.domain == "example.com"

    def test_dns_add(self):
        args = self.parser.parse_args(["dns", "add", "example.com"])
        assert args.dns_action == "add"

    def test_dns_update(self):
        args = self.parser.parse_args(["dns", "update", "example.com"])
        assert args.dns_action == "update"

    def test_dns_delete(self):
        args = self.parser.parse_args(["dns", "delete", "example.com"])
        assert args.dns_action == "delete"

    # --- configure ---
    def test_configure_godaddy_set(self):
        args = self.parser.parse_args(["configure", "godaddy", "set", "mykey", "mysecret"])
        assert args.configure_service == "godaddy"
        assert args.godaddy_action == "set"
        assert args.key == "mykey"
        assert args.secret == "mysecret"

    def test_configure_godaddy_get(self):
        args = self.parser.parse_args(["configure", "godaddy", "get"])
        assert args.godaddy_action == "get"

    def test_configure_godaddy_test(self):
        args = self.parser.parse_args(["configure", "godaddy", "test"])
        assert args.godaddy_action == "test"

    def test_configure_godaddy_set_env(self):
        args = self.parser.parse_args(["configure", "godaddy", "set-env", "ote"])
        assert args.godaddy_action == "set-env"
        assert args.env == "ote"

    def test_configure_godaddy_set_env_invalid(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args(["configure", "godaddy", "set-env", "staging"])

    def test_configure_cloudflare_set(self):
        args = self.parser.parse_args(["configure", "cloudflare", "set", "mytoken"])
        assert args.configure_service == "cloudflare"
        assert args.cloudflare_action == "set"
        assert args.token == "mytoken"

    def test_configure_cloudflare_get(self):
        args = self.parser.parse_args(["configure", "cloudflare", "get"])
        assert args.cloudflare_action == "get"

    def test_configure_cloudflare_test(self):
        args = self.parser.parse_args(["configure", "cloudflare", "test"])
        assert args.cloudflare_action == "test"

    # --- connect ---
    def test_connect(self):
        args = self.parser.parse_args(["connect", "example.com"])
        assert args.command == "connect"
        assert args.domain == "example.com"

    # --- deploy ---
    def test_deploy_status(self):
        args = self.parser.parse_args(["deploy", "status"])
        assert args.command == "deploy"
        assert args.deploy_action == "status"

    def test_deploy_push(self):
        args = self.parser.parse_args(["deploy", "push"])
        assert args.deploy_action == "push"

    def test_deploy_init(self):
        args = self.parser.parse_args(["deploy", "init"])
        assert args.deploy_action == "init"

    # --- setup ---
    def test_setup_no_service(self):
        args = self.parser.parse_args(["setup"])
        assert args.command == "setup"
        assert args.service is None

    def test_setup_specific_service(self):
        for svc in ("cloudflare", "railway", "godaddy", "github"):
            args = self.parser.parse_args(["setup", svc])
            assert args.service == svc
