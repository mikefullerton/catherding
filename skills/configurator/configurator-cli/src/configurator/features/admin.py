"""Admin site feature."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"


class AdminFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="admin", label="Admin Site", version=_VERSION,
            order=30, dependencies=["backend"], group="admin_sites",
        )

    def config_html(self, ctx: RenderContext) -> str:
        deployed = 'style=""' if "admin" in ctx.deployed_keys else 'style="display:none"'
        live = 'style=""' if "admin" in ctx.live_domains else 'style="display:none"'
        return f"""\
<div class="toggle-row">
    <input type="checkbox" id="admin-enabled">
    <label for="admin-enabled">Admin site</label>
    <span class="badge deployed-badge" id="admin-deployed" {deployed}>deployed</span>
    <span class="badge live-badge" id="admin-live" {live}>live</span>
</div>
<div class="live-url" id="admin-link"><a href="#" target="_blank"></a></div>
<div class="sub-field">
    <label for="admin-domain">Admin domain</label>
    <input type="text" id="admin-domain">
</div>"""

    def config_js_read(self) -> str:
        return """\
    // Admin site
    const adminSite = {};
    if ($("#admin-enabled").checked) {
        adminSite.enabled = true;
        const d = $("#admin-domain").value.trim();
        if (d) adminSite.domain = d;
    } else {
        adminSite.enabled = false;
    }
    if (!cfg.admin_sites) cfg.admin_sites = {};
    cfg.admin_sites.admin = adminSite;"""

    def config_js_populate(self) -> str:
        return """\
    // Admin site
    const adminSites = CONFIG.admin_sites || {};
    const admin = adminSites.admin || {};
    $("#admin-enabled").checked = !!admin.enabled;
    $("#admin-domain").value = admin.domain || defaultDomain("admin");

    if (DEPLOYED.has("admin")) {
        $("#admin-enabled").disabled = true;
        setLink("admin-link", "admin");
    }"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Admin domain — disable when not enabled
    $("#admin-domain").disabled = !$("#admin-enabled").checked;"""

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        services = manifest.get("services", {})
        if "admin" not in services:
            return {"enabled": False}
        s: dict = {"enabled": True}
        if services["admin"].get("domain"):
            s["domain"] = services["admin"]["domain"]
        return s

    def deployed_keys(self, manifest: dict) -> set[str]:
        if "admin" in manifest.get("services", {}):
            return {"admin"}
        return set()
