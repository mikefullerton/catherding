"""Tests for CapabilitiesFeature."""

from configurator.features.capabilities import CapabilitiesFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert CapabilitiesFeature().meta().id == "capabilities"

    def test_depends_on_auth(self):
        assert "auth" in CapabilitiesFeature().meta().dependencies

    def test_order(self):
        assert CapabilitiesFeature().meta().order == 43

    def test_no_group(self):
        assert CapabilitiesFeature().meta().group is None


class TestManifestToConfig:
    def test_enabled_full(self):
        f = CapabilitiesFeature()
        manifest = {"features": {"capabilities": {
            "enabled": True,
            "definitions": ["api:read", "api:write"],
            "user_assignable": True,
            "token_assignable": True,
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {
            "enabled": True,
            "definitions": ["api:read", "api:write"],
            "user_assignable": True,
            "token_assignable": True,
        }

    def test_enabled_minimal(self):
        f = CapabilitiesFeature()
        manifest = {"features": {"capabilities": {"enabled": True}}}
        assert f.manifest_to_config(manifest) == {"enabled": True}

    def test_disabled(self):
        f = CapabilitiesFeature()
        manifest = {"features": {"capabilities": {"enabled": False}}}
        assert f.manifest_to_config(manifest) == {"enabled": False}

    def test_missing(self):
        assert CapabilitiesFeature().manifest_to_config({}) == {"enabled": False}

    def test_definitions_copied(self):
        f = CapabilitiesFeature()
        defs = ["api:read", "admin:access"]
        manifest = {"features": {"capabilities": {"enabled": True, "definitions": defs}}}
        cfg = f.manifest_to_config(manifest)
        assert cfg["definitions"] == ["api:read", "admin:access"]
        assert cfg["definitions"] is not defs


class TestDeployedKeys:
    def test_deployed(self):
        f = CapabilitiesFeature()
        manifest = {"features": {"capabilities": {"enabled": True}}}
        assert "capabilities" in f.deployed_keys(manifest)

    def test_not_deployed(self):
        assert CapabilitiesFeature().deployed_keys({}) == set()

    def test_disabled_not_deployed(self):
        f = CapabilitiesFeature()
        manifest = {"features": {"capabilities": {"enabled": False}}}
        assert f.deployed_keys(manifest) == set()


class TestConfigHtml:
    def test_contains_enabled_checkbox(self):
        html = CapabilitiesFeature().config_html(ctx())
        assert 'id="capabilities-enabled"' in html

    def test_contains_list_textarea(self):
        html = CapabilitiesFeature().config_html(ctx())
        assert 'id="capabilities-list"' in html

    def test_contains_user_assignable(self):
        html = CapabilitiesFeature().config_html(ctx())
        assert 'id="capabilities-user-assignable"' in html

    def test_contains_token_assignable(self):
        html = CapabilitiesFeature().config_html(ctx())
        assert 'id="capabilities-token-assignable"' in html

    def test_wrapped_in_fieldset(self):
        html = CapabilitiesFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_disabled_by_default(self):
        assert CapabilitiesFeature().default_config() == {"enabled": False}
