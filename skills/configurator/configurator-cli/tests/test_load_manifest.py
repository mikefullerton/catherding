"""Tests for _load_manifest — loading .site/manifest.json from a project path."""

import json

from configurator.cli import _load_manifest


class TestLoadManifest:
    def test_loads_valid_manifest(self, tmp_path):
        site_dir = tmp_path / ".site"
        site_dir.mkdir()
        manifest = {"project": {"name": "test"}, "version": "1.0.0"}
        (site_dir / "manifest.json").write_text(json.dumps(manifest))
        result = _load_manifest(tmp_path)
        assert result == manifest

    def test_no_site_dir(self, tmp_path):
        assert _load_manifest(tmp_path) is None

    def test_no_manifest_file(self, tmp_path):
        (tmp_path / ".site").mkdir()
        assert _load_manifest(tmp_path) is None

    def test_invalid_json(self, tmp_path):
        site_dir = tmp_path / ".site"
        site_dir.mkdir()
        (site_dir / "manifest.json").write_text("not valid json {{{")
        assert _load_manifest(tmp_path) is None

    def test_empty_file(self, tmp_path):
        site_dir = tmp_path / ".site"
        site_dir.mkdir()
        (site_dir / "manifest.json").write_text("")
        assert _load_manifest(tmp_path) is None

    def test_returns_full_structure(self, tmp_path):
        site_dir = tmp_path / ".site"
        site_dir.mkdir()
        manifest = {
            "version": "1.0.0",
            "project": {"name": "test", "domain": "test.com"},
            "services": {"main": {"domain": "test.com"}},
            "features": {"auth": {"providers": ["email"]}},
        }
        (site_dir / "manifest.json").write_text(json.dumps(manifest))
        result = _load_manifest(tmp_path)
        assert result["project"]["name"] == "test"
        assert result["services"]["main"]["domain"] == "test.com"
        assert result["features"]["auth"]["providers"] == ["email"]
