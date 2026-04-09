"""Pausing feature — temporary user and token suspension."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"


class PausingFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="pausing", label="User/Token Pausing", version=_VERSION,
            order=42, dependencies=["auth"],
        )

    def config_html(self, ctx: RenderContext) -> str:
        return """<fieldset>
<legend>User/Token Pausing</legend>
<div class="field">
    <label><input type="checkbox" id="pausing-enabled"> Enable user/token pausing</label>
</div>
<div class="field">
    <label><input type="checkbox" id="pausing-users"> Allow pausing users</label>
</div>
<div class="field">
    <label><input type="checkbox" id="pausing-tokens"> Allow pausing API tokens</label>
</div>
<div class="field">
    <label><input type="checkbox" id="pausing-auto-unpause"> Support scheduled auto-unpause</label>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Pausing
    if ($("#pausing-enabled").checked) {
        const pausing = { enabled: true };
        pausing.pause_users = $("#pausing-users").checked;
        pausing.pause_tokens = $("#pausing-tokens").checked;
        pausing.auto_unpause = $("#pausing-auto-unpause").checked;
        cfg.pausing = pausing;
    } else {
        cfg.pausing = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // Pausing
    const pausing = CONFIG.pausing || {};
    $("#pausing-enabled").checked = !!pausing.enabled;
    $("#pausing-users").checked = pausing.pause_users !== false;
    $("#pausing-tokens").checked = pausing.pause_tokens !== false;
    $("#pausing-auto-unpause").checked = !!pausing.auto_unpause;"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Pausing — disable fields when not enabled
    const pausingOn = $("#pausing-enabled").checked;
    $("#pausing-users").disabled = !pausingOn;
    $("#pausing-tokens").disabled = !pausingOn;
    $("#pausing-auto-unpause").disabled = !pausingOn;"""

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        pausing = manifest.get("features", {}).get("pausing", {})
        if not pausing.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if "pause_users" in pausing:
            cfg["pause_users"] = pausing["pause_users"]
        if "pause_tokens" in pausing:
            cfg["pause_tokens"] = pausing["pause_tokens"]
        if "auto_unpause" in pausing:
            cfg["auto_unpause"] = pausing["auto_unpause"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        pausing = manifest.get("features", {}).get("pausing", {})
        if pausing.get("enabled"):
            return {"pausing"}
        return set()
