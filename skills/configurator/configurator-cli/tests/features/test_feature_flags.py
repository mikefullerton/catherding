"""Tests for FeatureFlagsFeature."""

from configurator.features.feature_flags import FeatureFlagsFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert FeatureFlagsFeature().meta().id == "feature_flags"

    def test_depends_on_website(self):
        assert "website" in FeatureFlagsFeature().meta().dependencies

    def test_order(self):
        assert FeatureFlagsFeature().meta().order == 62

    def test_no_group(self):
        assert FeatureFlagsFeature().meta().group is None


class TestManifestToConfig:
    def test_enabled_full(self):
        f = FeatureFlagsFeature()
        manifest = {"features": {"feature_flags": {
            "enabled": True,
            "capability_hooks": True,
            "flag_hooks": True,
            "ab_hooks": True,
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {
            "enabled": True,
            "capability_hooks": True,
            "flag_hooks": True,
            "ab_hooks": True,
        }

    def test_enabled_minimal(self):
        f = FeatureFlagsFeature()
        manifest = {"features": {"feature_flags": {"enabled": True}}}
        assert f.manifest_to_config(manifest) == {"enabled": True}

    def test_disabled(self):
        f = FeatureFlagsFeature()
        manifest = {"features": {"feature_flags": {"enabled": False}}}
        assert f.manifest_to_config(manifest) == {"enabled": False}

    def test_missing(self):
        assert FeatureFlagsFeature().manifest_to_config({}) == {"enabled": False}

    def test_partial_hooks(self):
        f = FeatureFlagsFeature()
        manifest = {"features": {"feature_flags": {
            "enabled": True, "capability_hooks": True, "ab_hooks": False,
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg["capability_hooks"] is True
        assert cfg["ab_hooks"] is False


class TestDeployedKeys:
    def test_deployed(self):
        f = FeatureFlagsFeature()
        manifest = {"features": {"feature_flags": {"enabled": True}}}
        assert "feature_flags" in f.deployed_keys(manifest)

    def test_not_deployed(self):
        assert FeatureFlagsFeature().deployed_keys({}) == set()

    def test_disabled_not_deployed(self):
        f = FeatureFlagsFeature()
        manifest = {"features": {"feature_flags": {"enabled": False}}}
        assert f.deployed_keys(manifest) == set()


class TestConfigHtml:
    def test_contains_enabled_checkbox(self):
        html = FeatureFlagsFeature().config_html(ctx())
        assert 'id="feature-flags-enabled"' in html

    def test_contains_capability_hooks(self):
        html = FeatureFlagsFeature().config_html(ctx())
        assert 'id="feature-flags-capability-hooks"' in html

    def test_contains_flag_hooks(self):
        html = FeatureFlagsFeature().config_html(ctx())
        assert 'id="feature-flags-flag-hooks"' in html

    def test_contains_ab_hooks(self):
        html = FeatureFlagsFeature().config_html(ctx())
        assert 'id="feature-flags-ab-hooks"' in html

    def test_wrapped_in_fieldset(self):
        html = FeatureFlagsFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_disabled_by_default(self):
        assert FeatureFlagsFeature().default_config() == {"enabled": False}
