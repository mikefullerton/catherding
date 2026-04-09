"""Project feature — repo, org, domain, port, local_path."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"


class ProjectFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="project", label="Project", version=_VERSION,
            order=0, dependencies=[],
        )

    def config_html(self, ctx: RenderContext) -> str:
        return """<fieldset>
<legend>Project</legend>
<div class="field">
    <label for="repo">Repository name</label>
    <input type="text" id="repo" data-key="repo">
</div>
<div class="field">
    <label for="org">Organization</label>
    <select id="org" data-key="org">
        <option value="">-- select --</option>
        <option value="mikefullerton">mikefullerton</option>
        <option value="agentic-cookbook">agentic-cookbook</option>
        <option value="other">other</option>
    </select>
</div>
<div class="field" id="org-other-field" style="display:none">
    <label for="org-other">Organization name</label>
    <input type="text" id="org-other">
</div>
<div class="field">
    <label for="domain">Domain</label>
    <input type="text" id="domain" data-key="domain">
</div>
<div class="field">
    <label for="port">Editor port</label>
    <input type="text" id="port" data-key="port" inputmode="numeric" pattern="[0-9]*">
</div>
<div class="field" id="local-path-field" style="display:none">
    <label>Local path</label>
    <div class="readonly" id="local-path"></div>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Project
    const repo = $("#repo").value.trim();
    if (repo) cfg.repo = repo;

    const orgSel = $("#org").value;
    if (orgSel === "other") {
        const custom = $("#org-other").value.trim();
        if (custom) cfg.org = custom;
    } else if (orgSel) {
        cfg.org = orgSel;
    }

    const domain = $("#domain").value.trim();
    if (domain) cfg.domain = domain;

    const port = parseInt($("#port").value, 10);
    if (port && port > 0) cfg.port = port;

    // Local path (read-only, pass through)
    if (CONFIG.local_path) cfg.local_path = CONFIG.local_path;
    if (CONFIG.create_repo) cfg.create_repo = CONFIG.create_repo;"""

    def config_js_populate(self) -> str:
        return """\
    // Project
    $("#repo").value = CONFIG.repo || "";
    const org = CONFIG.org || "";
    const orgSelect = $("#org");
    const knownOrgs = [...orgSelect.options].map(o => o.value);
    if (org && !knownOrgs.includes(org)) {
        orgSelect.value = "other";
        $("#org-other").value = org;
        $("#org-other-field").style.display = "";
    } else {
        orgSelect.value = org;
    }
    $("#domain").value = CONFIG.domain || "";
    $("#port").value = CONFIG.port || 4040;
    if (CONFIG.local_path) {
        $("#local-path").textContent = CONFIG.local_path;
        $("#local-path-field").style.display = "";
    }

    // Lock repo and org when deployed
    if (DEPLOYED.has("repo")) {
        $("#repo").disabled = true;
    }
    if (DEPLOYED.has("org")) {
        $("#org").disabled = true;
    }"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Org other
    $("#org-other-field").style.display = $("#org").value === "other" ? "" : "none";"""

    def default_config(self) -> dict:
        return {"repo": "", "org": "", "domain": ""}

    def manifest_to_config(self, manifest: dict) -> dict:
        cfg: dict = {}
        project = manifest.get("project", {})
        if project.get("name"):
            cfg["repo"] = project["name"]
        if project.get("org"):
            cfg["org"] = project["org"]
        if project.get("domain"):
            cfg["domain"] = project["domain"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        keys: set[str] = set()
        project = manifest.get("project", {})
        if project.get("name"):
            keys.add("repo")
        if project.get("org"):
            keys.add("org")
        return keys
