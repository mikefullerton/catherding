"""Tests for draft persistence and migration."""

import json
from pathlib import Path
from unittest.mock import patch

from configurator.cli import (
    save_config,
    load_config,
    config_path,
    _migrate_draft,
    _git_author,
    cmd_snapshot,
)
from configurator import __version__


class TestDraftPersistence:
    def setup_method(self):
        self.name = "__test_draft__"
        # Clean up before test
        p = config_path(self.name)
        if p.exists():
            p.unlink()

    def teardown_method(self):
        p = config_path(self.name)
        if p.exists():
            p.unlink()

    def test_save_adds_configurator_version(self):
        save_config(self.name, {"repo": "test"})
        cfg = load_config(self.name)
        assert cfg["configurator_version"] == __version__

    def test_save_preserves_change_history(self):
        history = [{"date": "2026-01-01", "item": "backend.enabled"}]
        save_config(self.name, {"repo": "test", "_change_history": history})
        cfg = load_config(self.name)
        assert cfg["_change_history"] == history

    def test_load_missing_config_returns_empty(self):
        cfg = load_config("__nonexistent__")
        assert cfg == {}


class TestMigrateDraft:
    def test_same_version_returns_unchanged(self):
        cfg = {"repo": "test", "configurator_version": __version__}
        result = _migrate_draft(cfg)
        assert result["configurator_version"] == __version__

    def test_old_version_gets_updated(self):
        cfg = {"repo": "test", "configurator_version": "0.1.0"}
        result = _migrate_draft(cfg)
        assert result["configurator_version"] == __version__

    def test_ensures_change_history_exists(self):
        cfg = {"repo": "test", "configurator_version": "0.1.0"}
        result = _migrate_draft(cfg)
        assert "_change_history" in result
        assert isinstance(result["_change_history"], list)

    def test_preserves_existing_change_history(self):
        history = [{"item": "backend.enabled"}]
        cfg = {"repo": "test", "configurator_version": "0.1.0", "_change_history": history}
        result = _migrate_draft(cfg)
        assert result["_change_history"] == history

    def test_no_version_gets_updated(self):
        cfg = {"repo": "test"}
        result = _migrate_draft(cfg)
        assert result["configurator_version"] == __version__


class TestGitAuthor:
    def test_returns_dict(self):
        # Works on any machine with git configured
        author = _git_author(Path.cwd())
        assert isinstance(author, dict)

    def test_returns_empty_for_nonexistent_path(self):
        author = _git_author(Path("/nonexistent"))
        assert author == {}


class TestSnapshot:
    def test_snapshot_creates_file(self, tmp_path):
        # Setup: create .site/manifest.json and a draft config
        site_dir = tmp_path / ".site"
        site_dir.mkdir()
        manifest = {"project": {"name": "__test_snap__"}}
        (site_dir / "manifest.json").write_text(json.dumps(manifest))

        # Create a draft
        save_config("__test_snap__", {"repo": "test", "_change_history": []})

        try:
            with patch("configurator.cli.Path.cwd", return_value=tmp_path):
                cmd_snapshot()

            deployments = site_dir / "deployments"
            assert deployments.exists()
            files = list(deployments.glob("*-deployment.json"))
            assert len(files) == 1
            content = json.loads(files[0].read_text())
            assert content["repo"] == "test"
        finally:
            p = config_path("__test_snap__")
            if p.exists():
                p.unlink()
