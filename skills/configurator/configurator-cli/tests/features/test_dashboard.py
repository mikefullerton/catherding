"""Tests for DashboardFeature."""

from configurator.features.dashboard import DashboardFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestManifestToConfig:
    def test_dashboard_enabled(self):
        f = DashboardFeature()
        cfg = f.manifest_to_config({"services": {"dashboard": {"domain": "dash.example.com"}}})
        assert cfg["enabled"] is True
        assert cfg["domain"] == "dash.example.com"

    def test_no_dashboard(self):
        f = DashboardFeature()
        assert f.manifest_to_config({"services": {}}) == {"enabled": False}


class TestDeployedKeys:
    def test_dashboard_deployed(self):
        assert "dashboard" in DashboardFeature().deployed_keys({"services": {"dashboard": {}}})

    def test_empty(self):
        assert DashboardFeature().deployed_keys({"services": {}}) == set()


class TestMeta:
    def test_group(self):
        assert DashboardFeature().meta().group == "admin_sites"

    def test_depends_on_backend(self):
        assert "backend" in DashboardFeature().meta().dependencies

    def test_order_after_admin(self):
        assert DashboardFeature().meta().order > 30


class TestConfigHtml:
    def test_contains_enable_checkbox(self):
        html = DashboardFeature().config_html(ctx())
        assert 'id="dash-enabled"' in html

    def test_deployed_badge(self):
        html = DashboardFeature().config_html(ctx(deployed_keys={"dashboard"}))
        assert 'id="dash-deployed" style=""' in html
