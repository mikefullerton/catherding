"""Tests for ThemeFeature."""

from configurator.features.theme import ThemeFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert ThemeFeature().meta().id == "theme"

    def test_depends_on_website(self):
        assert "website" in ThemeFeature().meta().dependencies

    def test_order(self):
        assert ThemeFeature().meta().order == 11

    def test_no_group(self):
        assert ThemeFeature().meta().group is None


class TestManifestToConfig:
    def test_with_mode(self):
        f = ThemeFeature()
        manifest = {"features": {"theme": {"mode": "dark"}}}
        assert f.manifest_to_config(manifest) == {"mode": "dark"}

    def test_system_mode(self):
        f = ThemeFeature()
        manifest = {"features": {"theme": {"mode": "system"}}}
        assert f.manifest_to_config(manifest) == {"mode": "system"}

    def test_toggle_mode(self):
        f = ThemeFeature()
        manifest = {"features": {"theme": {"mode": "toggle"}}}
        assert f.manifest_to_config(manifest) == {"mode": "toggle"}

    def test_missing_defaults_to_system(self):
        assert ThemeFeature().manifest_to_config({}) == {"mode": "system"}

    def test_empty_features(self):
        assert ThemeFeature().manifest_to_config({"features": {}}) == {"mode": "system"}


class TestDeployedKeys:
    def test_deployed(self):
        f = ThemeFeature()
        manifest = {"features": {"theme": {"mode": "dark"}}}
        assert "theme" in f.deployed_keys(manifest)

    def test_not_deployed(self):
        assert ThemeFeature().deployed_keys({}) == set()


class TestConfigHtml:
    def test_contains_mode_select(self):
        html = ThemeFeature().config_html(ctx())
        assert 'id="theme-mode"' in html

    def test_contains_mode_options(self):
        html = ThemeFeature().config_html(ctx())
        assert 'value="system"' in html
        assert 'value="light"' in html
        assert 'value="dark"' in html
        assert 'value="toggle"' in html

    def test_wrapped_in_fieldset(self):
        html = ThemeFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_system_by_default(self):
        assert ThemeFeature().default_config() == {"mode": "system"}
