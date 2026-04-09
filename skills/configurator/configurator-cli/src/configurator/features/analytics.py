"""Analytics feature — web analytics provider configuration."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_PROVIDERS = [
    ("plausible", "Plausible"),
    ("posthog", "PostHog"),
    ("cloudflare", "Cloudflare Web Analytics"),
    ("google", "Google Analytics"),
]


class AnalyticsFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="analytics", label="Analytics", version=_VERSION,
            order=60, dependencies=["website"],
        )

    def config_html(self, ctx: RenderContext) -> str:
        options = "\n        ".join(
            f'<option value="{pid}">{label}</option>' for pid, label in _PROVIDERS
        )
        return f"""<fieldset>
<legend>Analytics</legend>
<div class="field">
    <label><input type="checkbox" id="analytics-enabled"> Enable analytics</label>
</div>
<div class="field">
    <label for="analytics-provider">Provider</label>
    <select id="analytics-provider" data-key="analytics.provider">
        <option value="">-- select --</option>
        {options}
    </select>
</div>
<div class="field">
    <label for="analytics-site-id">Site ID / measurement ID</label>
    <input type="text" id="analytics-site-id" data-key="analytics.site_id" placeholder="">
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Analytics
    if ($("#analytics-enabled").checked) {
        const analytics = { enabled: true };
        const provider = $("#analytics-provider").value;
        if (provider) analytics.provider = provider;
        const siteId = $("#analytics-site-id").value.trim();
        if (siteId) analytics.site_id = siteId;
        cfg.analytics = analytics;
    } else {
        cfg.analytics = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // Analytics
    const analytics = CONFIG.analytics || {};
    $("#analytics-enabled").checked = !!analytics.enabled;
    $("#analytics-provider").value = analytics.provider || "";
    $("#analytics-site-id").value = analytics.site_id || "";"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Analytics — disable fields when not enabled
    const analyticsOn = $("#analytics-enabled").checked;
    $("#analytics-provider").disabled = !analyticsOn;
    $("#analytics-site-id").disabled = !analyticsOn;"""

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        analytics = manifest.get("features", {}).get("analytics", {})
        if not analytics.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if analytics.get("provider"):
            cfg["provider"] = analytics["provider"]
        if analytics.get("site_id"):
            cfg["site_id"] = analytics["site_id"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        analytics = manifest.get("features", {}).get("analytics", {})
        if analytics.get("enabled"):
            return {"analytics"}
        return set()
