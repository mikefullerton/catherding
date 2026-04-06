"""Tests for webinator config management."""

import json
import os
import pytest
from webinator.config import ensure_config, save_config, load_config, get_godaddy_auth, get_cloudflare_auth


class TestEnsureConfig:
    def test_creates_dir_and_file(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".webinitor"
        config_path = config_dir / "config.json"
        monkeypatch.setattr("webinator.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("webinator.config.CONFIG_PATH", config_path)

        cfg = ensure_config()
        assert config_dir.exists()
        assert config_path.exists()
        assert "godaddy" in cfg
        assert "cloudflare" in cfg

    def test_preserves_existing_config(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".webinitor"
        config_path = config_dir / "config.json"
        config_dir.mkdir()
        existing = {"godaddy": {"api_key": "existing"}, "cloudflare": {}}
        config_path.write_text(json.dumps(existing))
        monkeypatch.setattr("webinator.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("webinator.config.CONFIG_PATH", config_path)

        cfg = ensure_config()
        assert cfg["godaddy"]["api_key"] == "existing"


class TestSaveAndLoad:
    def test_round_trip(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".webinitor"
        config_path = config_dir / "config.json"
        config_dir.mkdir()
        config_path.write_text("{}")
        monkeypatch.setattr("webinator.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("webinator.config.CONFIG_PATH", config_path)

        data = {"godaddy": {"api_key": "test123", "api_secret": "sec"}, "cloudflare": {}}
        save_config(data)
        loaded = load_config()
        assert loaded["godaddy"]["api_key"] == "test123"

    def test_load_missing_file_exits(self, tmp_path, monkeypatch):
        config_path = tmp_path / "nonexistent.json"
        monkeypatch.setattr("webinator.config.CONFIG_PATH", config_path)
        with pytest.raises(SystemExit) as exc:
            load_config()
        assert exc.value.code == 1


class TestGetGodaddyAuth:
    def test_returns_production_url_and_header(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".webinitor"
        config_path = config_dir / "config.json"
        config_dir.mkdir()
        cfg = {"godaddy": {"api_key": "k", "api_secret": "s", "environment": "production"}}
        config_path.write_text(json.dumps(cfg))
        monkeypatch.setattr("webinator.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("webinator.config.CONFIG_PATH", config_path)

        base_url, auth = get_godaddy_auth()
        assert base_url == "https://api.godaddy.com"
        assert auth == "sso-key k:s"

    def test_returns_ote_url(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".webinitor"
        config_path = config_dir / "config.json"
        config_dir.mkdir()
        cfg = {"godaddy": {"api_key": "k", "api_secret": "s", "environment": "ote"}}
        config_path.write_text(json.dumps(cfg))
        monkeypatch.setattr("webinator.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("webinator.config.CONFIG_PATH", config_path)

        base_url, _ = get_godaddy_auth()
        assert base_url == "https://api.ote-godaddy.com"

    def test_exits_when_not_configured(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".webinitor"
        config_path = config_dir / "config.json"
        config_dir.mkdir()
        config_path.write_text(json.dumps({"godaddy": {"api_key": "", "api_secret": ""}}))
        monkeypatch.setattr("webinator.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("webinator.config.CONFIG_PATH", config_path)

        with pytest.raises(SystemExit) as exc:
            get_godaddy_auth()
        assert exc.value.code == 1


class TestGetCloudflareAuth:
    def test_returns_token_and_account_id(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".webinitor"
        config_path = config_dir / "config.json"
        config_dir.mkdir()
        cfg = {"cloudflare": {"api_token": "tok123", "account_id": "acc456"}}
        config_path.write_text(json.dumps(cfg))
        monkeypatch.setattr("webinator.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("webinator.config.CONFIG_PATH", config_path)

        token, account_id = get_cloudflare_auth()
        assert token == "tok123"
        assert account_id == "acc456"

    def test_exits_when_no_token(self, tmp_path, monkeypatch):
        config_dir = tmp_path / ".webinitor"
        config_path = config_dir / "config.json"
        config_dir.mkdir()
        config_path.write_text(json.dumps({"cloudflare": {"api_token": ""}}))
        monkeypatch.setattr("webinator.config.CONFIG_DIR", config_dir)
        monkeypatch.setattr("webinator.config.CONFIG_PATH", config_path)

        with pytest.raises(SystemExit) as exc:
            get_cloudflare_auth()
        assert exc.value.code == 1
