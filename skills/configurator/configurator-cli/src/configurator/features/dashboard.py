"""Dashboard feature."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"


class DashboardFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="dashboard", label="Dashboard", version=_VERSION,
            order=31, dependencies=["backend"], group="admin_sites", category="backend",
        )

    def config_html(self, ctx: RenderContext) -> str:
        deployed = 'style=""' if "dashboard" in ctx.deployed_keys else 'style="display:none"'
        live = 'style=""' if "dashboard" in ctx.live_domains else 'style="display:none"'
        return f"""\
<div class="toggle-row" style="margin-top: 0.8rem">
    <input type="checkbox" id="dash-enabled">
    <label for="dash-enabled">Dashboard</label>
    <span class="badge deployed-badge" id="dash-deployed" {deployed}>deployed</span>
    <span class="badge live-badge" id="dash-live" {live}>live</span>
</div>
<div class="live-url" id="dash-link"><a href="#" target="_blank"></a></div>
<div class="sub-field">
    <label for="dash-domain">Dashboard domain</label>
    <input type="text" id="dash-domain">
</div>"""

    def config_js_read(self) -> str:
        return """\
    // Dashboard
    const dashSite = {};
    if ($("#dash-enabled").checked) {
        dashSite.enabled = true;
        const d = $("#dash-domain").value.trim();
        if (d) dashSite.domain = d;
    } else {
        dashSite.enabled = false;
    }
    if (!cfg.admin_sites) cfg.admin_sites = {};
    cfg.admin_sites.dashboard = dashSite;"""

    def config_js_populate(self) -> str:
        return """\
    // Dashboard
    const dashSites = CONFIG.admin_sites || {};
    const dash = dashSites.dashboard || {};
    $("#dash-enabled").checked = !!dash.enabled;
    $("#dash-domain").value = dash.domain || defaultDomain("dashboard");

    if (DEPLOYED.has("dashboard")) {
        $("#dash-enabled").disabled = true;
        setLink("dash-link", "dashboard");
    }"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Dashboard domain — disable when not enabled
    $("#dash-domain").disabled = !$("#dash-enabled").checked;"""

    def config_identifiers(self) -> dict[str, str]:
        return {
            "dashboard.enabled": "bool",
            "dashboard.domain": "string",
        }

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        services = manifest.get("services", {})
        if "dashboard" not in services:
            return {"enabled": False}
        s: dict = {"enabled": True}
        if services["dashboard"].get("domain"):
            s["domain"] = services["dashboard"]["domain"]
        return s

    def deployed_keys(self, manifest: dict) -> set[str]:
        if "dashboard" in manifest.get("services", {}):
            return {"dashboard"}
        return set()
