"""Tests for PausingFeature."""

from configurator.features.pausing import PausingFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert PausingFeature().meta().id == "pausing"

    def test_depends_on_auth(self):
        assert "auth" in PausingFeature().meta().dependencies

    def test_order(self):
        assert PausingFeature().meta().order == 42

    def test_no_group(self):
        assert PausingFeature().meta().group is None


class TestManifestToConfig:
    def test_enabled_full(self):
        f = PausingFeature()
        manifest = {"features": {"pausing": {
            "enabled": True, "pause_users": True, "pause_tokens": True, "auto_unpause": True,
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {
            "enabled": True, "pause_users": True,
            "pause_tokens": True, "auto_unpause": True,
        }

    def test_enabled_minimal(self):
        f = PausingFeature()
        manifest = {"features": {"pausing": {"enabled": True}}}
        assert f.manifest_to_config(manifest) == {"enabled": True}

    def test_disabled(self):
        f = PausingFeature()
        manifest = {"features": {"pausing": {"enabled": False}}}
        assert f.manifest_to_config(manifest) == {"enabled": False}

    def test_missing(self):
        assert PausingFeature().manifest_to_config({}) == {"enabled": False}

    def test_auto_unpause_false(self):
        f = PausingFeature()
        manifest = {"features": {"pausing": {
            "enabled": True, "auto_unpause": False,
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg["auto_unpause"] is False


class TestDeployedKeys:
    def test_deployed(self):
        f = PausingFeature()
        manifest = {"features": {"pausing": {"enabled": True}}}
        assert "pausing" in f.deployed_keys(manifest)

    def test_not_deployed(self):
        assert PausingFeature().deployed_keys({}) == set()

    def test_disabled_not_deployed(self):
        f = PausingFeature()
        manifest = {"features": {"pausing": {"enabled": False}}}
        assert f.deployed_keys(manifest) == set()


class TestConfigHtml:
    def test_contains_enabled_checkbox(self):
        html = PausingFeature().config_html(ctx())
        assert 'id="pausing-enabled"' in html

    def test_contains_users_checkbox(self):
        html = PausingFeature().config_html(ctx())
        assert 'id="pausing-users"' in html

    def test_contains_tokens_checkbox(self):
        html = PausingFeature().config_html(ctx())
        assert 'id="pausing-tokens"' in html

    def test_contains_auto_unpause_checkbox(self):
        html = PausingFeature().config_html(ctx())
        assert 'id="pausing-auto-unpause"' in html

    def test_wrapped_in_fieldset(self):
        html = PausingFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_disabled_by_default(self):
        assert PausingFeature().default_config() == {"enabled": False}
