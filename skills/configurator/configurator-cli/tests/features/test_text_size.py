"""Tests for TextSizeFeature."""

from configurator.features.text_size import TextSizeFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert TextSizeFeature().meta().id == "text_size"

    def test_depends_on_website(self):
        assert "website" in TextSizeFeature().meta().dependencies

    def test_order(self):
        assert TextSizeFeature().meta().order == 12

    def test_no_group(self):
        assert TextSizeFeature().meta().group is None


class TestManifestToConfig:
    def test_system_mode(self):
        f = TextSizeFeature()
        manifest = {"features": {"text_size": {"mode": "system"}}}
        assert f.manifest_to_config(manifest) == {"mode": "system"}

    def test_custom_mode_with_px(self):
        f = TextSizeFeature()
        manifest = {"features": {"text_size": {"mode": "custom", "custom_px": 20}}}
        assert f.manifest_to_config(manifest) == {"mode": "custom", "custom_px": 20}

    def test_preset_mode(self):
        f = TextSizeFeature()
        manifest = {"features": {"text_size": {"mode": "large"}}}
        assert f.manifest_to_config(manifest) == {"mode": "large"}

    def test_missing_defaults_to_system(self):
        assert TextSizeFeature().manifest_to_config({}) == {"mode": "system"}


class TestDeployedKeys:
    def test_deployed(self):
        f = TextSizeFeature()
        manifest = {"features": {"text_size": {"mode": "large"}}}
        assert "text_size" in f.deployed_keys(manifest)

    def test_not_deployed(self):
        assert TextSizeFeature().deployed_keys({}) == set()


class TestConfigHtml:
    def test_contains_mode_select(self):
        html = TextSizeFeature().config_html(ctx())
        assert 'id="text-size-mode"' in html

    def test_contains_custom_input(self):
        html = TextSizeFeature().config_html(ctx())
        assert 'id="text-size-custom"' in html

    def test_contains_mode_options(self):
        html = TextSizeFeature().config_html(ctx())
        assert 'value="system"' in html
        assert 'value="small"' in html
        assert 'value="medium"' in html
        assert 'value="large"' in html
        assert 'value="custom"' in html

    def test_wrapped_in_fieldset(self):
        html = TextSizeFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_system_by_default(self):
        assert TextSizeFeature().default_config() == {"mode": "system"}
