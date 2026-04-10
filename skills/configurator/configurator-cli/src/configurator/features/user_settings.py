"""User settings feature — settings panel for end users."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"


class UserSettingsFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="user_settings", label="User Settings", version=_VERSION,
            order=13, dependencies=["website", "auth"], category="ux",
        )

    def config_html(self, ctx: RenderContext) -> str:
        return """<fieldset>
<legend>User Settings Panel</legend>
<div class="field">
    <label><input type="checkbox" id="user-settings-enabled"> Enable user settings panel</label>
</div>
<div class="field">
    <label><input type="checkbox" id="user-settings-profile"> Profile editing</label>
</div>
<div class="field">
    <label><input type="checkbox" id="user-settings-password"> Password change</label>
</div>
<div class="field">
    <label><input type="checkbox" id="user-settings-theme"> Theme preference</label>
</div>
<div class="field">
    <label><input type="checkbox" id="user-settings-notifications"> Notification preferences</label>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // User settings
    if ($("#user-settings-enabled").checked) {
        const us = { enabled: true };
        us.profile = $("#user-settings-profile").checked;
        us.password_change = $("#user-settings-password").checked;
        us.theme_preference = $("#user-settings-theme").checked;
        us.notifications = $("#user-settings-notifications").checked;
        cfg.user_settings = us;
    } else {
        cfg.user_settings = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // User settings
    const us = CONFIG.user_settings || {};
    $("#user-settings-enabled").checked = !!us.enabled;
    $("#user-settings-profile").checked = us.profile !== false;
    $("#user-settings-password").checked = us.password_change !== false;
    $("#user-settings-theme").checked = !!us.theme_preference;
    $("#user-settings-notifications").checked = !!us.notifications;"""

    def config_js_update_disabled(self) -> str:
        return """\
    // User settings — disable fields when not enabled
    const usOn = $("#user-settings-enabled").checked;
    $("#user-settings-profile").disabled = !usOn;
    $("#user-settings-password").disabled = !usOn;
    $("#user-settings-theme").disabled = !usOn;
    $("#user-settings-notifications").disabled = !usOn;"""

    def config_identifiers(self) -> dict[str, str]:
        return {
            "user-settings.enabled": "bool",
            "user-settings.profile": "bool",
            "user-settings.password-change": "bool",
            "user-settings.theme-preference": "bool",
            "user-settings.notifications": "bool",
        }

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        us = manifest.get("features", {}).get("user_settings", {})
        if not us.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if "profile" in us:
            cfg["profile"] = us["profile"]
        if "password_change" in us:
            cfg["password_change"] = us["password_change"]
        if "theme_preference" in us:
            cfg["theme_preference"] = us["theme_preference"]
        if "notifications" in us:
            cfg["notifications"] = us["notifications"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        us = manifest.get("features", {}).get("user_settings", {})
        if us.get("enabled"):
            return {"user_settings"}
        return set()
