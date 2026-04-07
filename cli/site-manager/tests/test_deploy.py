"""Tests for deploy manifest path resolution."""

import json
import pytest
from unittest.mock import patch
from site_manager.deploy import _read_manifest, _save_manifest


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
