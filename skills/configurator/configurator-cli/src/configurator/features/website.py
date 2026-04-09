"""Website feature — type, domain, addons."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.1"


class WebsiteFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="website", label="Website", version=_VERSION,
            order=10, dependencies=["project"], category="website",
        )

    def config_html(self, ctx: RenderContext) -> str:
        deployed = 'style=""' if "website" in ctx.deployed_keys else 'style="display:none"'
        live = 'style=""' if "main" in ctx.live_domains else 'style="display:none"'
        return f"""<fieldset>
<legend>Website
    <span class="badge deployed-badge" id="ws-deployed" {deployed}>deployed</span>
    <span class="badge live-badge" id="ws-live" {live}>live</span>
</legend>
<div class="live-url" id="ws-link"><a href="#" target="_blank"></a></div>
<div class="field">
    <label>Type</label>
    <div class="radio-group">
        <label><input type="radio" name="ws-type" value="new"> <span>New</span></label>
        <label><input type="radio" name="ws-type" value="existing"> <span>Existing</span></label>
        <label><input type="radio" name="ws-type" value="none"> <span>None</span></label>
    </div>
</div>
<div class="field">
    <label for="ws-domain">Website domain</label>
    <input type="text" id="ws-domain">
</div>
<div class="field">
    <label>Addons</label>
    <div class="checkbox-group">
        <label><input type="checkbox" id="addon-d1" value="sqlite database"> <span>SQLite database</span></label>
        <label><input type="checkbox" id="addon-kv" value="key-value storage"> <span>Key-value storage</span></label>
        <label><input type="checkbox" id="addon-r2" value="file storage"> <span>File storage</span></label>
    </div>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Website
    const wsType = document.querySelector('input[name="ws-type"]:checked');
    const ws = { type: wsType ? wsType.value : "none" };
    if (ws.type !== "none") {
        const wsDomain = $("#ws-domain").value.trim();
        if (wsDomain) ws.domain = wsDomain;
        const addons = [];
        if ($("#addon-d1").checked) addons.push("sqlite database");
        if ($("#addon-kv").checked) addons.push("key-value storage");
        if ($("#addon-r2").checked) addons.push("file storage");
        if (addons.length) ws.addons = addons;
    }
    cfg.website = ws;"""

    def config_js_populate(self) -> str:
        return """\
    // Website
    const ws = CONFIG.website || {};
    const wsType = ws.type || "none";
    const wsRadio = document.querySelector(`input[name="ws-type"][value="${wsType}"]`);
    if (wsRadio) wsRadio.checked = true;
    $("#ws-domain").value = ws.domain || CONFIG.domain || "";

    const addons = ws.addons || [];
    $("#addon-d1").checked = addons.includes("sqlite database");
    $("#addon-kv").checked = addons.includes("key-value storage");
    $("#addon-r2").checked = addons.includes("file storage");

    if (DEPLOYED.has("website")) {
        for (const radio of $$('input[name="ws-type"]')) {
            radio.disabled = true;
        }
        setLink("ws-link", "main");
    }"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Website fields — disable when type is "none"
    const wsType = document.querySelector('input[name="ws-type"]:checked');
    const wsNone = !wsType || wsType.value === "none";
    $("#ws-domain").disabled = wsNone;
    for (const el of [$("#addon-d1"), $("#addon-kv"), $("#addon-r2")]) {
        el.disabled = wsNone;
    }"""

    def default_config(self) -> dict:
        return {"type": "none"}

    def manifest_to_config(self, manifest: dict) -> dict:
        services = manifest.get("services", {})
        if "main" not in services:
            return {"type": "none"}

        main_svc = services["main"]
        ws: dict = {"type": "existing"}
        if main_svc.get("domain"):
            ws["domain"] = main_svc["domain"]

        addons: list[str] = []
        if main_svc.get("d1") or main_svc.get("database"):
            addons.append("sqlite database")
        if main_svc.get("kv"):
            addons.append("key-value storage")
        if main_svc.get("r2"):
            addons.append("file storage")
        if addons:
            ws["addons"] = addons

        return ws

    def deployed_keys(self, manifest: dict) -> set[str]:
        services = manifest.get("services", {})
        if "main" in services:
            return {"website"}
        return set()
