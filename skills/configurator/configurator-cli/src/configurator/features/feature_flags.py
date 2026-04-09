"""Feature flags feature — client-side hooks for capabilities, flags, and A/B tests."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"


class FeatureFlagsFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="feature_flags", label="Feature Flags", version=_VERSION,
            order=62, dependencies=["website"], column="right",
        )

    def config_html(self, ctx: RenderContext) -> str:
        return """<fieldset>
<legend>Feature Flags</legend>
<div class="field">
    <label><input type="checkbox" id="feature-flags-enabled"> Enable client-side feature flag hooks</label>
</div>
<div class="field">
    <label><input type="checkbox" id="feature-flags-capability-hooks"> Capability-aware UI hooks</label>
</div>
<div class="field">
    <label><input type="checkbox" id="feature-flags-flag-hooks"> Feature flag hooks</label>
</div>
<div class="field">
    <label><input type="checkbox" id="feature-flags-ab-hooks"> A/B test variant hooks</label>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Feature flags
    if ($("#feature-flags-enabled").checked) {
        const ff = { enabled: true };
        ff.capability_hooks = $("#feature-flags-capability-hooks").checked;
        ff.flag_hooks = $("#feature-flags-flag-hooks").checked;
        ff.ab_hooks = $("#feature-flags-ab-hooks").checked;
        cfg.feature_flags = ff;
    } else {
        cfg.feature_flags = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // Feature flags
    const ff = CONFIG.feature_flags || {};
    $("#feature-flags-enabled").checked = !!ff.enabled;
    $("#feature-flags-capability-hooks").checked = !!ff.capability_hooks;
    $("#feature-flags-flag-hooks").checked = !!ff.flag_hooks;
    $("#feature-flags-ab-hooks").checked = !!ff.ab_hooks;"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Feature flags — disable fields when not enabled
    const ffOn = $("#feature-flags-enabled").checked;
    $("#feature-flags-capability-hooks").disabled = !ffOn;
    $("#feature-flags-flag-hooks").disabled = !ffOn;
    $("#feature-flags-ab-hooks").disabled = !ffOn;"""

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        ff = manifest.get("features", {}).get("feature_flags", {})
        if not ff.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if "capability_hooks" in ff:
            cfg["capability_hooks"] = ff["capability_hooks"]
        if "flag_hooks" in ff:
            cfg["flag_hooks"] = ff["flag_hooks"]
        if "ab_hooks" in ff:
            cfg["ab_hooks"] = ff["ab_hooks"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        ff = manifest.get("features", {}).get("feature_flags", {})
        if ff.get("enabled"):
            return {"feature_flags"}
        return set()
