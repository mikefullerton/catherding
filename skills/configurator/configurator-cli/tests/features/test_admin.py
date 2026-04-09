"""Tests for AdminFeature."""

from configurator.features.admin import AdminFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestManifestToConfig:
    def test_admin_enabled(self):
        f = AdminFeature()
        cfg = f.manifest_to_config({"services": {"admin": {"domain": "admin.example.com"}}})
        assert cfg["enabled"] is True
        assert cfg["domain"] == "admin.example.com"

    def test_no_admin(self):
        f = AdminFeature()
        assert f.manifest_to_config({"services": {}}) == {"enabled": False}

    def test_admin_without_domain(self):
        f = AdminFeature()
        cfg = f.manifest_to_config({"services": {"admin": {"status": "deployed"}}})
        assert cfg["enabled"] is True
        assert "domain" not in cfg


class TestDeployedKeys:
    def test_admin_deployed(self):
        assert "admin" in AdminFeature().deployed_keys({"services": {"admin": {}}})

    def test_empty(self):
        assert AdminFeature().deployed_keys({"services": {}}) == set()


class TestMeta:
    def test_group(self):
        assert AdminFeature().meta().group == "admin_sites"

    def test_depends_on_backend(self):
        assert "backend" in AdminFeature().meta().dependencies


class TestConfigHtml:
    def test_contains_enable_checkbox(self):
        html = AdminFeature().config_html(ctx())
        assert 'id="admin-enabled"' in html

    def test_no_fieldset_wrapper(self):
        html = AdminFeature().config_html(ctx())
        assert not html.strip().startswith("<fieldset>")

    def test_deployed_badge(self):
        html = AdminFeature().config_html(ctx(deployed_keys={"admin"}))
        assert 'id="admin-deployed" style=""' in html
