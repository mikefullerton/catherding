"""Capabilities feature — define permission scopes for users and tokens."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_DEFAULT_CAPABILITIES = [
    "api:read",
    "api:write",
    "admin:access",
    "messaging:send",
]


class CapabilitiesFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="capabilities", label="Capabilities", version=_VERSION,
            order=43, dependencies=["auth"], column="right",
        )

    def config_html(self, ctx: RenderContext) -> str:
        return """<fieldset>
<legend>Capabilities</legend>
<div class="field">
    <label><input type="checkbox" id="capabilities-enabled"> Enable capability-based permissions</label>
</div>
<div class="field">
    <label for="capabilities-list">Defined capabilities (one per line)</label>
    <textarea id="capabilities-list" rows="5" placeholder="api:read&#10;api:write&#10;admin:access"></textarea>
</div>
<div class="field">
    <label><input type="checkbox" id="capabilities-user-assignable"> Allow assigning capabilities to users</label>
</div>
<div class="field">
    <label><input type="checkbox" id="capabilities-token-assignable"> Allow assigning capabilities to API tokens</label>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Capabilities
    if ($("#capabilities-enabled").checked) {
        const caps = { enabled: true };
        const lines = $("#capabilities-list").value.split("\\n").map(l => l.trim()).filter(Boolean);
        if (lines.length) caps.definitions = lines;
        caps.user_assignable = $("#capabilities-user-assignable").checked;
        caps.token_assignable = $("#capabilities-token-assignable").checked;
        cfg.capabilities = caps;
    } else {
        cfg.capabilities = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // Capabilities
    const caps = CONFIG.capabilities || {};
    $("#capabilities-enabled").checked = !!caps.enabled;
    $("#capabilities-list").value = (caps.definitions || []).join("\\n");
    $("#capabilities-user-assignable").checked = caps.user_assignable !== false;
    $("#capabilities-token-assignable").checked = caps.token_assignable !== false;"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Capabilities — disable fields when not enabled
    const capsOn = $("#capabilities-enabled").checked;
    $("#capabilities-list").disabled = !capsOn;
    $("#capabilities-user-assignable").disabled = !capsOn;
    $("#capabilities-token-assignable").disabled = !capsOn;"""

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        caps = manifest.get("features", {}).get("capabilities", {})
        if not caps.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if caps.get("definitions"):
            cfg["definitions"] = list(caps["definitions"])
        if "user_assignable" in caps:
            cfg["user_assignable"] = caps["user_assignable"]
        if "token_assignable" in caps:
            cfg["token_assignable"] = caps["token_assignable"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        caps = manifest.get("features", {}).get("capabilities", {})
        if caps.get("enabled"):
            return {"capabilities"}
        return set()
