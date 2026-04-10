"""A/B testing feature — experiment platform configuration."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_PROVIDERS = [
    ("growthbook", "GrowthBook"),
    ("launchdarkly", "LaunchDarkly"),
    ("statsig", "Statsig"),
    ("custom", "Custom"),
]


class AbTestingFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="ab_testing", label="A/B Testing", version=_VERSION,
            order=61, dependencies=["website"], category="analytics",
        )

    def config_html(self, ctx: RenderContext) -> str:
        options = "\n        ".join(
            f'<option value="{pid}">{label}</option>' for pid, label in _PROVIDERS
        )
        return f"""<fieldset>
<legend>A/B Testing</legend>
<div class="field">
    <label><input type="checkbox" id="ab-testing-enabled"> Enable A/B testing</label>
</div>
<div class="field">
    <label for="ab-testing-provider">Provider</label>
    <select id="ab-testing-provider" data-key="ab_testing.provider">
        <option value="">-- select --</option>
        {options}
    </select>
</div>
<div class="field">
    <label for="ab-testing-client-key">Client key</label>
    <input type="text" id="ab-testing-client-key" data-key="ab_testing.client_key" placeholder="">
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // A/B Testing
    if ($("#ab-testing-enabled").checked) {
        const ab = { enabled: true };
        const provider = $("#ab-testing-provider").value;
        if (provider) ab.provider = provider;
        const clientKey = $("#ab-testing-client-key").value.trim();
        if (clientKey) ab.client_key = clientKey;
        cfg.ab_testing = ab;
    } else {
        cfg.ab_testing = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // A/B Testing
    const ab = CONFIG.ab_testing || {};
    $("#ab-testing-enabled").checked = !!ab.enabled;
    $("#ab-testing-provider").value = ab.provider || "";
    $("#ab-testing-client-key").value = ab.client_key || "";"""

    def config_js_update_disabled(self) -> str:
        return """\
    // A/B Testing — disable fields when not enabled
    const abOn = $("#ab-testing-enabled").checked;
    $("#ab-testing-provider").disabled = !abOn;
    $("#ab-testing-client-key").disabled = !abOn;"""

    def config_identifiers(self) -> dict[str, str]:
        return {
            "ab-testing.enabled": "bool",
            "ab-testing.provider": "string",
            "ab-testing.client-key": "string",
        }

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        ab = manifest.get("features", {}).get("ab_testing", {})
        if not ab.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if ab.get("provider"):
            cfg["provider"] = ab["provider"]
        if ab.get("client_key"):
            cfg["client_key"] = ab["client_key"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        ab = manifest.get("features", {}).get("ab_testing", {})
        if ab.get("enabled"):
            return {"ab_testing"}
        return set()
