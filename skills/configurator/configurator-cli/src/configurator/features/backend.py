"""Backend feature — enabled, domain, docs, environments."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.1.0"


class BackendFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="backend", label="Backend", version=_VERSION,
            order=20, dependencies=["project"],
        )

    def config_html(self, ctx: RenderContext) -> str:
        deployed = 'style=""' if "backend" in ctx.deployed_keys else 'style="display:none"'
        live = 'style=""' if "backend" in ctx.live_domains else 'style="display:none"'
        return f"""<fieldset>
<legend>Backend
    <span class="badge deployed-badge" id="be-deployed" {deployed}>deployed</span>
    <span class="badge live-badge" id="be-live" {live}>live</span>
</legend>
<div class="live-url" id="be-link"><a href="#" target="_blank"></a></div>
<div class="toggle-row">
    <input type="checkbox" id="be-enabled">
    <label for="be-enabled">Enable backend</label>
</div>
<div class="field">
    <label for="be-domain">Backend domain</label>
    <input type="text" id="be-domain">
</div>
<div class="field">
    <div class="toggle-row">
        <input type="checkbox" id="be-docs-enabled">
        <label for="be-docs-enabled">API docs site</label>
    </div>
    <div class="sub-field">
        <label for="be-docs-domain">Docs domain</label>
        <input type="text" id="be-docs-domain">
    </div>
</div>
<div class="field">
    <label>Additional environments</label>
    <div class="checkbox-group">
        <label><input type="checkbox" id="env-staging" value="staging"> <span>Staging</span></label>
        <label><input type="checkbox" id="env-testing" value="testing"> <span>Testing</span></label>
    </div>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Backend
    const be = {};
    if ($("#be-enabled").checked) {
        be.enabled = true;
        be.type = "full";
        const beDomain = $("#be-domain").value.trim();
        if (beDomain) be.domain = beDomain;
        if ($("#be-docs-enabled").checked) {
            const docsDomain = $("#be-docs-domain").value.trim();
            if (docsDomain) be.docs_domain = docsDomain;
        }
        const environments = {};
        if ($("#env-staging").checked) environments.staging = true;
        if ($("#env-testing").checked) environments.testing = true;
        if (Object.keys(environments).length) be.environments = environments;
    } else {
        be.enabled = false;
    }
    cfg.backend = be;"""

    def config_js_populate(self) -> str:
        return """\
    // Backend — populate defaults even if not enabled
    const be = CONFIG.backend || {};
    $("#be-enabled").checked = !!be.enabled;
    $("#be-domain").value = be.domain || defaultDomain("backend");
    $("#be-docs-enabled").checked = !!be.docs_domain;
    $("#be-docs-domain").value = be.docs_domain || defaultDomain("api");

    const envs = be.environments || {};
    $("#env-staging").checked = !!envs.staging;
    $("#env-testing").checked = !!envs.testing;

    if (DEPLOYED.has("backend")) {
        $("#be-enabled").disabled = true;
        setLink("be-link", "backend");
    }"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Backend fields — disable when not enabled
    const beEnabled = $("#be-enabled").checked;
    $("#be-domain").disabled = !beEnabled;
    $("#be-docs-enabled").disabled = !beEnabled;
    const docsEnabled = beEnabled && $("#be-docs-enabled").checked;
    $("#be-docs-domain").disabled = !docsEnabled;
    $("#env-staging").disabled = !beEnabled;
    $("#env-testing").disabled = !beEnabled;"""

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        services = manifest.get("services", {})
        has_backend = "backend" in services or "api" in services or "api-docs" in services
        if not has_backend:
            return {"enabled": False}

        be: dict = {"enabled": True, "type": "full"}
        be_svc = services.get("backend", services.get("api", {}))
        if be_svc.get("domain"):
            be["domain"] = be_svc["domain"]
        if services.get("api-docs", {}).get("domain"):
            be["docs_domain"] = services["api-docs"]["domain"]

        # Extract environments from services or features
        envs: dict = {}
        if "backend-staging" in services:
            envs["staging"] = True
        if "backend-testing" in services:
            envs["testing"] = True
        feat_envs = manifest.get("features", {}).get("backend", {}).get("environments", {})
        if feat_envs.get("staging"):
            envs["staging"] = True
        if feat_envs.get("testing"):
            envs["testing"] = True
        if envs:
            be["environments"] = envs
        return be

    def deployed_keys(self, manifest: dict) -> set[str]:
        services = manifest.get("services", {})
        if "backend" in services or "api" in services or "api-docs" in services:
            return {"backend"}
        return set()
