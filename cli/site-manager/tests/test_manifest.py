"""Tests for site-manager manifest validation logic."""

import json
import pytest
from site_manager.manifest import validate_manifest, show_manifest


VALID_MANIFEST = {
    "version": "1.0.0",
    "project": {"name": "test-project", "domain": "example.com", "created": "2026-01-01"},
    "services": {
        "backend": {"status": "deployed", "platform": "railway"},
        "main": {"status": "deployed", "platform": "cloudflare"},
        "admin": {"status": "scaffolded", "platform": "cloudflare"},
        "dashboard": {"status": "scaffolded", "platform": "cloudflare"},
    },
    "features": {
        "auth": {"enabled": True, "providers": ["email"]},
    },
}


def _write_manifest(tmp_path, data):
    p = tmp_path / "site-manifest.json"
    p.write_text(json.dumps(data))
    return p


class TestValidateManifest:
    def test_valid_manifest(self, tmp_path, monkeypatch, capsys):
        _write_manifest(tmp_path, VALID_MANIFEST)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_missing_version(self, tmp_path, monkeypatch, capsys):
        data = {**VALID_MANIFEST, "version": ""}
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["valid"] is False
        assert any("version" in e for e in result["errors"])

    def test_missing_project_name(self, tmp_path, monkeypatch, capsys):
        data = {**VALID_MANIFEST, "project": {"domain": "example.com", "created": "2026-01-01"}}
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert any("project.name" in e for e in result["errors"])

    def test_missing_service(self, tmp_path, monkeypatch, capsys):
        data = {**VALID_MANIFEST}
        data["services"] = {k: v for k, v in VALID_MANIFEST["services"].items() if k != "admin"}
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert any("services.admin" in e for e in result["errors"])

    def test_invalid_service_status(self, tmp_path, monkeypatch, capsys):
        data = json.loads(json.dumps(VALID_MANIFEST))
        data["services"]["backend"]["status"] = "bogus"
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert any("services.backend.status" in e for e in result["errors"])

    def test_missing_auth_providers(self, tmp_path, monkeypatch, capsys):
        data = json.loads(json.dumps(VALID_MANIFEST))
        data["features"]["auth"]["providers"] = []
        _write_manifest(tmp_path, data)
        monkeypatch.chdir(tmp_path)
        validate_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert any("providers" in e for e in result["errors"])

    def test_no_manifest_exits(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            validate_manifest()
        assert exc.value.code == 1


class TestShowManifest:
    def test_show_json(self, tmp_path, monkeypatch, capsys):
        _write_manifest(tmp_path, VALID_MANIFEST)
        monkeypatch.chdir(tmp_path)
        show_manifest(output_json=True)
        result = json.loads(capsys.readouterr().out)
        assert result["project"]["name"] == "test-project"

    def test_show_text(self, tmp_path, monkeypatch, capsys):
        _write_manifest(tmp_path, VALID_MANIFEST)
        monkeypatch.chdir(tmp_path)
        show_manifest()
        out = capsys.readouterr().out
        assert "test-project" in out
        assert "example.com" in out
