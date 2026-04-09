"""Tests for UserSettingsFeature."""

from configurator.features.user_settings import UserSettingsFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert UserSettingsFeature().meta().id == "user_settings"

    def test_depends_on_website_and_auth(self):
        deps = UserSettingsFeature().meta().dependencies
        assert "website" in deps
        assert "auth" in deps

    def test_order(self):
        assert UserSettingsFeature().meta().order == 13

    def test_no_group(self):
        assert UserSettingsFeature().meta().group is None


class TestManifestToConfig:
    def test_enabled_full(self):
        f = UserSettingsFeature()
        manifest = {"features": {"user_settings": {
            "enabled": True, "profile": True, "password_change": True,
            "theme_preference": True, "notifications": True,
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {
            "enabled": True, "profile": True, "password_change": True,
            "theme_preference": True, "notifications": True,
        }

    def test_enabled_minimal(self):
        f = UserSettingsFeature()
        manifest = {"features": {"user_settings": {"enabled": True}}}
        assert f.manifest_to_config(manifest) == {"enabled": True}

    def test_disabled(self):
        f = UserSettingsFeature()
        manifest = {"features": {"user_settings": {"enabled": False}}}
        assert f.manifest_to_config(manifest) == {"enabled": False}

    def test_missing(self):
        assert UserSettingsFeature().manifest_to_config({}) == {"enabled": False}


class TestDeployedKeys:
    def test_deployed(self):
        f = UserSettingsFeature()
        manifest = {"features": {"user_settings": {"enabled": True}}}
        assert "user_settings" in f.deployed_keys(manifest)

    def test_not_deployed(self):
        assert UserSettingsFeature().deployed_keys({}) == set()

    def test_disabled_not_deployed(self):
        f = UserSettingsFeature()
        manifest = {"features": {"user_settings": {"enabled": False}}}
        assert f.deployed_keys(manifest) == set()


class TestConfigHtml:
    def test_contains_enabled_checkbox(self):
        html = UserSettingsFeature().config_html(ctx())
        assert 'id="user-settings-enabled"' in html

    def test_contains_profile_checkbox(self):
        html = UserSettingsFeature().config_html(ctx())
        assert 'id="user-settings-profile"' in html

    def test_contains_password_checkbox(self):
        html = UserSettingsFeature().config_html(ctx())
        assert 'id="user-settings-password"' in html

    def test_contains_theme_checkbox(self):
        html = UserSettingsFeature().config_html(ctx())
        assert 'id="user-settings-theme"' in html

    def test_contains_notifications_checkbox(self):
        html = UserSettingsFeature().config_html(ctx())
        assert 'id="user-settings-notifications"' in html

    def test_wrapped_in_fieldset(self):
        html = UserSettingsFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_disabled_by_default(self):
        assert UserSettingsFeature().default_config() == {"enabled": False}
