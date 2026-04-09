"""Tests for AnalyticsFeature."""

from configurator.features.analytics import AnalyticsFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert AnalyticsFeature().meta().id == "analytics"

    def test_depends_on_website(self):
        assert "website" in AnalyticsFeature().meta().dependencies

    def test_order(self):
        assert AnalyticsFeature().meta().order == 60

    def test_no_group(self):
        assert AnalyticsFeature().meta().group is None


class TestManifestToConfig:
    def test_enabled_with_provider(self):
        f = AnalyticsFeature()
        manifest = {"features": {"analytics": {
            "enabled": True, "provider": "plausible", "site_id": "example.com",
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {"enabled": True, "provider": "plausible", "site_id": "example.com"}

    def test_enabled_minimal(self):
        f = AnalyticsFeature()
        manifest = {"features": {"analytics": {"enabled": True}}}
        assert f.manifest_to_config(manifest) == {"enabled": True}

    def test_disabled(self):
        f = AnalyticsFeature()
        manifest = {"features": {"analytics": {"enabled": False}}}
        assert f.manifest_to_config(manifest) == {"enabled": False}

    def test_missing(self):
        assert AnalyticsFeature().manifest_to_config({}) == {"enabled": False}


class TestDeployedKeys:
    def test_analytics_deployed(self):
        f = AnalyticsFeature()
        manifest = {"features": {"analytics": {"enabled": True}}}
        assert "analytics" in f.deployed_keys(manifest)

    def test_not_deployed(self):
        assert AnalyticsFeature().deployed_keys({}) == set()

    def test_disabled_not_deployed(self):
        f = AnalyticsFeature()
        manifest = {"features": {"analytics": {"enabled": False}}}
        assert f.deployed_keys(manifest) == set()


class TestConfigHtml:
    def test_contains_enabled_checkbox(self):
        html = AnalyticsFeature().config_html(ctx())
        assert 'id="analytics-enabled"' in html

    def test_contains_provider_select(self):
        html = AnalyticsFeature().config_html(ctx())
        assert 'id="analytics-provider"' in html

    def test_contains_site_id(self):
        html = AnalyticsFeature().config_html(ctx())
        assert 'id="analytics-site-id"' in html

    def test_contains_provider_options(self):
        html = AnalyticsFeature().config_html(ctx())
        assert 'value="plausible"' in html
        assert 'value="posthog"' in html
        assert 'value="cloudflare"' in html
        assert 'value="google"' in html

    def test_wrapped_in_fieldset(self):
        html = AnalyticsFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_disabled_by_default(self):
        assert AnalyticsFeature().default_config() == {"enabled": False}
