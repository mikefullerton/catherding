"""Tests for AbTestingFeature."""

from configurator.features.ab_testing import AbTestingFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert AbTestingFeature().meta().id == "ab_testing"

    def test_depends_on_website(self):
        assert "website" in AbTestingFeature().meta().dependencies

    def test_order(self):
        assert AbTestingFeature().meta().order == 61

    def test_no_group(self):
        assert AbTestingFeature().meta().group is None


class TestManifestToConfig:
    def test_enabled_with_provider(self):
        f = AbTestingFeature()
        manifest = {"features": {"ab_testing": {
            "enabled": True, "provider": "growthbook", "client_key": "sdk-abc123",
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {"enabled": True, "provider": "growthbook", "client_key": "sdk-abc123"}

    def test_enabled_minimal(self):
        f = AbTestingFeature()
        manifest = {"features": {"ab_testing": {"enabled": True}}}
        assert f.manifest_to_config(manifest) == {"enabled": True}

    def test_disabled(self):
        f = AbTestingFeature()
        manifest = {"features": {"ab_testing": {"enabled": False}}}
        assert f.manifest_to_config(manifest) == {"enabled": False}

    def test_missing(self):
        assert AbTestingFeature().manifest_to_config({}) == {"enabled": False}


class TestDeployedKeys:
    def test_deployed(self):
        f = AbTestingFeature()
        manifest = {"features": {"ab_testing": {"enabled": True}}}
        assert "ab_testing" in f.deployed_keys(manifest)

    def test_not_deployed(self):
        assert AbTestingFeature().deployed_keys({}) == set()

    def test_disabled_not_deployed(self):
        f = AbTestingFeature()
        manifest = {"features": {"ab_testing": {"enabled": False}}}
        assert f.deployed_keys(manifest) == set()


class TestConfigHtml:
    def test_contains_enabled_checkbox(self):
        html = AbTestingFeature().config_html(ctx())
        assert 'id="ab-testing-enabled"' in html

    def test_contains_provider_select(self):
        html = AbTestingFeature().config_html(ctx())
        assert 'id="ab-testing-provider"' in html

    def test_contains_client_key(self):
        html = AbTestingFeature().config_html(ctx())
        assert 'id="ab-testing-client-key"' in html

    def test_contains_provider_options(self):
        html = AbTestingFeature().config_html(ctx())
        assert 'value="growthbook"' in html
        assert 'value="launchdarkly"' in html
        assert 'value="statsig"' in html
        assert 'value="custom"' in html

    def test_wrapped_in_fieldset(self):
        html = AbTestingFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_disabled_by_default(self):
        assert AbTestingFeature().default_config() == {"enabled": False}
