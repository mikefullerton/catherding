"""Tests for WebsiteFeature."""

from configurator.features.website import WebsiteFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestManifestToConfig:
    def test_main_service_creates_existing(self):
        f = WebsiteFeature()
        cfg = f.manifest_to_config({"services": {"main": {"domain": "example.com"}}})
        assert cfg["type"] == "existing"
        assert cfg["domain"] == "example.com"

    def test_no_main_service(self):
        f = WebsiteFeature()
        assert f.manifest_to_config({"services": {}}) == {"type": "none"}

    def test_d1_addon(self):
        f = WebsiteFeature()
        cfg = f.manifest_to_config({"services": {"main": {"d1": True}}})
        assert "sqlite database" in cfg["addons"]

    def test_database_field_as_d1(self):
        f = WebsiteFeature()
        cfg = f.manifest_to_config({"services": {"main": {"database": "db"}}})
        assert "sqlite database" in cfg["addons"]

    def test_kv_addon(self):
        f = WebsiteFeature()
        cfg = f.manifest_to_config({"services": {"main": {"kv": True}}})
        assert "key-value storage" in cfg["addons"]

    def test_r2_addon(self):
        f = WebsiteFeature()
        cfg = f.manifest_to_config({"services": {"main": {"r2": True}}})
        assert "file storage" in cfg["addons"]

    def test_multiple_addons(self):
        f = WebsiteFeature()
        cfg = f.manifest_to_config({"services": {"main": {"d1": True, "kv": True, "r2": True}}})
        assert cfg["addons"] == ["sqlite database", "key-value storage", "file storage"]

    def test_no_addons(self):
        f = WebsiteFeature()
        cfg = f.manifest_to_config({"services": {"main": {"domain": "example.com"}}})
        assert "addons" not in cfg


class TestDeployedKeys:
    def test_main_deployed(self):
        f = WebsiteFeature()
        assert "website" in f.deployed_keys({"services": {"main": {}}})

    def test_no_main(self):
        f = WebsiteFeature()
        assert f.deployed_keys({"services": {}}) == set()


class TestConfigHtml:
    def test_contains_radio_buttons(self):
        html = WebsiteFeature().config_html(ctx())
        assert 'name="ws-type"' in html

    def test_deployed_badge_hidden_by_default(self):
        html = WebsiteFeature().config_html(ctx())
        assert 'display:none' in html

    def test_deployed_badge_visible_when_deployed(self):
        html = WebsiteFeature().config_html(ctx(deployed_keys={"website"}))
        assert 'id="ws-deployed" style=""' in html

    def test_live_badge_visible_when_live(self):
        html = WebsiteFeature().config_html(ctx(live_domains={"main"}))
        assert 'id="ws-live" style=""' in html
