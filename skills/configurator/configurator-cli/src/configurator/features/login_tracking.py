"""Login tracking feature — user and token login event tracking."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"


class LoginTrackingFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="login_tracking", label="Login Tracking", version=_VERSION,
            order=41, dependencies=["auth"],
        )

    def config_html(self, ctx: RenderContext) -> str:
        return """<fieldset>
<legend>Login Tracking</legend>
<div class="field">
    <label><input type="checkbox" id="login-tracking-enabled"> Enable login tracking</label>
</div>
<div class="field">
    <label><input type="checkbox" id="login-tracking-users"> Track user logins</label>
</div>
<div class="field">
    <label><input type="checkbox" id="login-tracking-tokens"> Track API token usage</label>
</div>
<div class="field">
    <label for="login-tracking-retention">Retention (days)</label>
    <input type="text" id="login-tracking-retention" data-key="login_tracking.retention_days" inputmode="numeric" pattern="[0-9]*" placeholder="90">
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Login tracking
    if ($("#login-tracking-enabled").checked) {
        const lt = { enabled: true };
        lt.track_users = $("#login-tracking-users").checked;
        lt.track_tokens = $("#login-tracking-tokens").checked;
        const retention = parseInt($("#login-tracking-retention").value, 10);
        if (retention > 0) lt.retention_days = retention;
        cfg.login_tracking = lt;
    } else {
        cfg.login_tracking = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // Login tracking
    const lt = CONFIG.login_tracking || {};
    $("#login-tracking-enabled").checked = !!lt.enabled;
    $("#login-tracking-users").checked = lt.track_users !== false;
    $("#login-tracking-tokens").checked = lt.track_tokens !== false;
    $("#login-tracking-retention").value = lt.retention_days || 90;"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Login tracking — disable fields when not enabled
    const ltOn = $("#login-tracking-enabled").checked;
    $("#login-tracking-users").disabled = !ltOn;
    $("#login-tracking-tokens").disabled = !ltOn;
    $("#login-tracking-retention").disabled = !ltOn;"""

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        lt = manifest.get("features", {}).get("login_tracking", {})
        if not lt.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if "track_users" in lt:
            cfg["track_users"] = lt["track_users"]
        if "track_tokens" in lt:
            cfg["track_tokens"] = lt["track_tokens"]
        if lt.get("retention_days"):
            cfg["retention_days"] = lt["retention_days"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        lt = manifest.get("features", {}).get("login_tracking", {})
        if lt.get("enabled"):
            return {"login_tracking"}
        return set()
