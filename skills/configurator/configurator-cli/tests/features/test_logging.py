"""Tests for LoggingFeature."""

from configurator.features.logging import LoggingFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert LoggingFeature().meta().id == "logging"

    def test_depends_on_backend(self):
        assert "backend" in LoggingFeature().meta().dependencies

    def test_order(self):
        assert LoggingFeature().meta().order == 70

    def test_no_group(self):
        assert LoggingFeature().meta().group is None


class TestManifestToConfig:
    def test_enabled_with_provider(self):
        f = LoggingFeature()
        manifest = {"features": {"logging": {
            "enabled": True, "provider": "axiom", "level": "debug",
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {"enabled": True, "provider": "axiom", "level": "debug"}

    def test_enabled_minimal(self):
        f = LoggingFeature()
        manifest = {"features": {"logging": {"enabled": True}}}
        assert f.manifest_to_config(manifest) == {"enabled": True}

    def test_disabled(self):
        f = LoggingFeature()
        manifest = {"features": {"logging": {"enabled": False}}}
        assert f.manifest_to_config(manifest) == {"enabled": False}

    def test_missing(self):
        assert LoggingFeature().manifest_to_config({}) == {"enabled": False}


class TestDeployedKeys:
    def test_deployed(self):
        f = LoggingFeature()
        manifest = {"features": {"logging": {"enabled": True}}}
        assert "logging" in f.deployed_keys(manifest)

    def test_not_deployed(self):
        assert LoggingFeature().deployed_keys({}) == set()

    def test_disabled_not_deployed(self):
        f = LoggingFeature()
        manifest = {"features": {"logging": {"enabled": False}}}
        assert f.deployed_keys(manifest) == set()


class TestConfigHtml:
    def test_contains_enabled_checkbox(self):
        html = LoggingFeature().config_html(ctx())
        assert 'id="logging-enabled"' in html

    def test_contains_provider_select(self):
        html = LoggingFeature().config_html(ctx())
        assert 'id="logging-provider"' in html

    def test_contains_level_select(self):
        html = LoggingFeature().config_html(ctx())
        assert 'id="logging-level"' in html

    def test_contains_provider_options(self):
        html = LoggingFeature().config_html(ctx())
        assert 'value="axiom"' in html
        assert 'value="datadog"' in html
        assert 'value="logtail"' in html
        assert 'value="sentry"' in html

    def test_contains_level_options(self):
        html = LoggingFeature().config_html(ctx())
        assert 'value="debug"' in html
        assert 'value="info"' in html
        assert 'value="warn"' in html
        assert 'value="error"' in html

    def test_wrapped_in_fieldset(self):
        html = LoggingFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_disabled_by_default(self):
        assert LoggingFeature().default_config() == {"enabled": False}
