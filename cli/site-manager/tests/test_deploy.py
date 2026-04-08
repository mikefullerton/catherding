"""Tests for deploy manifest path resolution and type-aware deployment."""

import json
import pytest
from unittest.mock import patch
from site_manager.deploy import _read_manifest, _save_manifest, _services_to_deploy, _site_directory


class TestReadManifest:
    def test_reads_from_site_dir(self, tmp_path, monkeypatch):
        site_dir = tmp_path / ".site"
        site_dir.mkdir()
        manifest = {"version": "1.0.0", "project": {"name": "test"}}
        (site_dir / "manifest.json").write_text(json.dumps(manifest))
        monkeypatch.chdir(tmp_path)
        result = _read_manifest()
        assert result["project"]["name"] == "test"

    def test_falls_back_to_legacy_path(self, tmp_path, monkeypatch):
        manifest = {"version": "1.0.0", "project": {"name": "legacy"}}
        (tmp_path / "site-manifest.json").write_text(json.dumps(manifest))
        monkeypatch.chdir(tmp_path)
        result = _read_manifest()
        assert result["project"]["name"] == "legacy"

    def test_prefers_site_dir_over_legacy(self, tmp_path, monkeypatch):
        site_dir = tmp_path / ".site"
        site_dir.mkdir()
        (site_dir / "manifest.json").write_text(json.dumps({"project": {"name": "new"}}))
        (tmp_path / "site-manifest.json").write_text(json.dumps({"project": {"name": "old"}}))
        monkeypatch.chdir(tmp_path)
        result = _read_manifest()
        assert result["project"]["name"] == "new"

    def test_exits_when_no_manifest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            _read_manifest()
        assert exc.value.code == 1


class TestSaveManifest:
    def test_saves_to_site_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _save_manifest({"version": "1.0.0"})
        saved = json.loads((tmp_path / ".site" / "manifest.json").read_text())
        assert saved["version"] == "1.0.0"

    def test_creates_site_dir_if_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _save_manifest({"version": "1.0.0"})
        assert (tmp_path / ".site").is_dir()


class TestServicesToDeploy:
    def test_full_deploys_all(self):
        manifest = {
            "project": {"type": "full"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
                "admin": {"status": "deployed", "platform": "cloudflare"},
                "dashboard": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["backend", "main", "admin", "dashboard"]

    def test_worker_deploys_main_only(self):
        manifest = {
            "project": {"type": "worker"},
            "services": {
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["main"]

    def test_existing_deploys_main_only(self):
        manifest = {
            "project": {"type": "existing"},
            "services": {
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["main"]

    def test_existing_with_backend_deploys_both(self):
        manifest = {
            "project": {"type": "existing"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["backend", "main"]

    def test_api_deploys_backend_and_main(self):
        manifest = {
            "project": {"type": "api"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["backend", "main"]

    def test_auth_service_deploys_backend_only(self):
        manifest = {
            "project": {"type": "auth-service"},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
            },
        }
        assert _services_to_deploy(manifest) == ["backend"]

    def test_no_type_deploys_all_present(self):
        """Missing type deploys whatever services exist in the manifest."""
        manifest = {
            "project": {},
            "services": {
                "backend": {"status": "deployed", "platform": "railway"},
                "main": {"status": "deployed", "platform": "cloudflare"},
                "admin": {"status": "deployed", "platform": "cloudflare"},
                "dashboard": {"status": "deployed", "platform": "cloudflare"},
            },
        }
        assert _services_to_deploy(manifest) == ["backend", "main", "admin", "dashboard"]


class TestSiteDirectory:
    def test_full_main_in_sites(self):
        manifest = {"project": {"type": "full"}}
        assert _site_directory("main", manifest) == "sites/main"

    def test_full_admin_in_sites(self):
        manifest = {"project": {"type": "full"}}
        assert _site_directory("admin", manifest) == "sites/admin"

    def test_worker_main_at_root(self):
        manifest = {"project": {"type": "worker"}}
        assert _site_directory("main", manifest) == "."

    def test_existing_main_at_root(self):
        manifest = {"project": {"type": "existing"}}
        assert _site_directory("main", manifest) == "."

    def test_api_main_in_sites(self):
        manifest = {"project": {"type": "api"}}
        assert _site_directory("main", manifest) == "sites/main"

    def test_custom_directory_from_manifest(self):
        manifest = {
            "project": {"type": "existing"},
            "services": {"main": {"directory": "frontend"}},
        }
        assert _site_directory("main", manifest) == "frontend"
