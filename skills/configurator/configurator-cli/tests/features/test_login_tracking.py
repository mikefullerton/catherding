"""Tests for LoginTrackingFeature."""

from configurator.features.login_tracking import LoginTrackingFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert LoginTrackingFeature().meta().id == "login_tracking"

    def test_depends_on_auth(self):
        assert "auth" in LoginTrackingFeature().meta().dependencies

    def test_order(self):
        assert LoginTrackingFeature().meta().order == 41

    def test_no_group(self):
        assert LoginTrackingFeature().meta().group is None


class TestManifestToConfig:
    def test_enabled_full(self):
        f = LoginTrackingFeature()
        manifest = {"features": {"login_tracking": {
            "enabled": True, "track_users": True, "track_tokens": True, "retention_days": 30,
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {"enabled": True, "track_users": True, "track_tokens": True, "retention_days": 30}

    def test_enabled_minimal(self):
        f = LoginTrackingFeature()
        manifest = {"features": {"login_tracking": {"enabled": True}}}
        assert f.manifest_to_config(manifest) == {"enabled": True}

    def test_disabled(self):
        f = LoginTrackingFeature()
        manifest = {"features": {"login_tracking": {"enabled": False}}}
        assert f.manifest_to_config(manifest) == {"enabled": False}

    def test_missing(self):
        assert LoginTrackingFeature().manifest_to_config({}) == {"enabled": False}

    def test_track_users_false(self):
        f = LoginTrackingFeature()
        manifest = {"features": {"login_tracking": {
            "enabled": True, "track_users": False,
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg["track_users"] is False


class TestDeployedKeys:
    def test_deployed(self):
        f = LoginTrackingFeature()
        manifest = {"features": {"login_tracking": {"enabled": True}}}
        assert "login_tracking" in f.deployed_keys(manifest)

    def test_not_deployed(self):
        assert LoginTrackingFeature().deployed_keys({}) == set()

    def test_disabled_not_deployed(self):
        f = LoginTrackingFeature()
        manifest = {"features": {"login_tracking": {"enabled": False}}}
        assert f.deployed_keys(manifest) == set()


class TestConfigHtml:
    def test_contains_enabled_checkbox(self):
        html = LoginTrackingFeature().config_html(ctx())
        assert 'id="login-tracking-enabled"' in html

    def test_contains_track_users_checkbox(self):
        html = LoginTrackingFeature().config_html(ctx())
        assert 'id="login-tracking-users"' in html

    def test_contains_track_tokens_checkbox(self):
        html = LoginTrackingFeature().config_html(ctx())
        assert 'id="login-tracking-tokens"' in html

    def test_contains_retention_input(self):
        html = LoginTrackingFeature().config_html(ctx())
        assert 'id="login-tracking-retention"' in html

    def test_wrapped_in_fieldset(self):
        html = LoginTrackingFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_disabled_by_default(self):
        assert LoginTrackingFeature().default_config() == {"enabled": False}
