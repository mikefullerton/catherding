"""Tests for site-manager CLI argument parsing and command routing."""

import pytest
from site_manager.cli import _build_parser, CLAUDE_COMMANDS


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

    # --- terminal commands ---
    def test_status(self):
        args = self.parser.parse_args(["status"])
        assert args.command == "status"
        assert args.command not in CLAUDE_COMMANDS

    def test_manifest_defaults_to_show(self):
        args = self.parser.parse_args(["manifest"])
        assert args.command == "manifest"
        assert args.action == "show"
        assert args.command not in CLAUDE_COMMANDS

    def test_manifest_validate(self):
        args = self.parser.parse_args(["manifest", "validate"])
        assert args.action == "validate"

    # --- claude commands ---
    def test_init_requires_claude(self):
        args = self.parser.parse_args(["init"])
        assert args.command in CLAUDE_COMMANDS

    def test_init_with_domain(self):
        args = self.parser.parse_args(["init", "example.com"])
        assert args.domain == "example.com"

    def test_migrate_requires_claude(self):
        args = self.parser.parse_args(["migrate"])
        assert args.command in CLAUDE_COMMANDS

    def test_migrate_with_domain(self):
        args = self.parser.parse_args(["migrate", "example.com"])
        assert args.domain == "example.com"

    def test_go_live_requires_claude(self):
        args = self.parser.parse_args(["go-live"])
        assert args.command in CLAUDE_COMMANDS

    def test_deploy_requires_claude(self):
        args = self.parser.parse_args(["deploy"])
        assert args.command in CLAUDE_COMMANDS
        assert args.service == "all"

    def test_deploy_specific_service(self):
        for svc in ("backend", "main", "admin", "dashboard"):
            args = self.parser.parse_args(["deploy", svc])
            assert args.service == svc

    def test_deploy_invalid_service(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args(["deploy", "bogus"])

    def test_seed_admin_requires_claude(self):
        args = self.parser.parse_args(["seed-admin"])
        assert args.command in CLAUDE_COMMANDS

    def test_update_requires_claude(self):
        args = self.parser.parse_args(["update"])
        assert args.command in CLAUDE_COMMANDS

    def test_verify_requires_claude(self):
        args = self.parser.parse_args(["verify"])
        assert args.command in CLAUDE_COMMANDS

    def test_verify_no_flags_runs_all(self):
        args = self.parser.parse_args(["verify"])
        assert not args.manifest
        assert not args.dns
        assert not args.e2e
        assert not args.smoke

    def test_verify_individual_flags(self):
        for flag in ("--manifest", "--dns", "--e2e", "--smoke"):
            args = self.parser.parse_args(["verify", flag])
            assert getattr(args, flag.lstrip("-")) is True

    def test_verify_multiple_flags(self):
        args = self.parser.parse_args(["verify", "--dns", "--e2e"])
        assert args.dns is True
        assert args.e2e is True
        assert not args.manifest
        assert not args.smoke

    def test_repair_requires_claude(self):
        args = self.parser.parse_args(["repair"])
        assert args.command in CLAUDE_COMMANDS


class TestClaudeGating:
    def test_claude_commands_set(self):
        assert CLAUDE_COMMANDS == {"init", "migrate", "go-live", "deploy", "seed-admin", "update", "verify", "repair"}

    def test_terminal_commands_not_gated(self):
        assert "status" not in CLAUDE_COMMANDS
        assert "manifest" not in CLAUDE_COMMANDS
