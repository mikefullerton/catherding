"""Tests for Config I/O — save, load, delete, list configs."""

import json

from configurator.cli import (
    config_path,
    delete_config,
    list_configs,
    load_config,
    save_config,
)


class TestConfigPath:
    def test_returns_json_in_config_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        assert config_path("myproject") == tmp_path / "myproject.json"


class TestSaveAndLoadConfig:
    def test_round_trip(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        save_config("proj", {"repo": "proj", "domain": "proj.com"})
        loaded = load_config("proj")
        assert loaded["repo"] == "proj"
        assert loaded["domain"] == "proj.com"

    def test_stamps_configurator_version(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        save_config("proj", {"repo": "proj"})
        loaded = load_config("proj")
        assert "configurator_version" in loaded

    def test_creates_dir_if_missing(self, monkeypatch, tmp_path):
        cfg_dir = tmp_path / "subdir" / "configs"
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", cfg_dir)
        save_config("proj", {"repo": "proj"})
        assert cfg_dir.exists()
        assert (cfg_dir / "proj.json").exists()

    def test_overwrites_existing(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        save_config("proj", {"repo": "old"})
        save_config("proj", {"repo": "new"})
        loaded = load_config("proj")
        assert loaded["repo"] == "new"

    def test_file_is_pretty_printed(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        save_config("proj", {"repo": "proj"})
        raw = (tmp_path / "proj.json").read_text()
        assert "\n" in raw
        assert raw.endswith("\n")

    def test_load_missing_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        assert load_config("nonexistent") == {}


class TestDeleteConfig:
    def test_deletes_existing(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        save_config("proj", {"repo": "proj"})
        assert (tmp_path / "proj.json").exists()
        delete_config("proj")
        assert not (tmp_path / "proj.json").exists()

    def test_noop_for_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        delete_config("nonexistent")  # should not raise


class TestListConfigs:
    def test_lists_saved_configs(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        save_config("alpha", {"repo": "alpha"})
        save_config("beta", {"repo": "beta"})
        assert list_configs() == ["alpha", "beta"]

    def test_empty_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        assert list_configs() == []

    def test_missing_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path / "nope")
        assert list_configs() == []

    def test_excludes_global_config(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("configurator.cli.GLOBAL_CONFIG", tmp_path / "configurator-config.json")
        save_config("proj", {"repo": "proj"})
        # Write a fake global config
        (tmp_path / "configurator-config.json").write_text("{}")
        configs = list_configs()
        assert "configurator-config" not in configs
        assert "proj" in configs
