"""Authentication feature — providers."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_PROVIDER_MAP = {"email": "email/password"}


class AuthFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="auth", label="Authentication", version=_VERSION,
            order=40, dependencies=["backend"], category="auth",
        )

    def config_html(self, ctx: RenderContext) -> str:
        return """<fieldset>
<legend>Authentication</legend>
<div class="field">
    <label>Providers</label>
    <div class="checkbox-group">
        <label><input type="checkbox" id="auth-email" value="email/password"> <span>Email/password</span></label>
        <label><input type="checkbox" id="auth-github" value="github"> <span>GitHub</span></label>
        <label><input type="checkbox" id="auth-google" value="google"> <span>Google</span></label>
        <label><input type="checkbox" id="auth-apple" value="apple"> <span>Apple</span></label>
    </div>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Auth
    const providers = [];
    if ($("#auth-email").checked) providers.push("email/password");
    if ($("#auth-github").checked) providers.push("github");
    if ($("#auth-google").checked) providers.push("google");
    if ($("#auth-apple").checked) providers.push("apple");
    if (providers.length) cfg.auth_providers = providers;"""

    def config_js_populate(self) -> str:
        return """\
    // Auth
    const providers = CONFIG.auth_providers || [];
    $("#auth-email").checked = providers.includes("email/password");
    $("#auth-github").checked = providers.includes("github");
    $("#auth-google").checked = providers.includes("google");
    $("#auth-apple").checked = providers.includes("apple");"""

    def config_js_update_disabled(self) -> str:
        return ""

    def config_identifiers(self) -> dict[str, str]:
        return {"auth.providers": "list"}

    def default_config(self) -> list:
        return []

    def manifest_to_config(self, manifest: dict) -> list:
        auth = manifest.get("features", {}).get("auth", manifest.get("auth", {}))
        providers = auth.get("providers", [])
        if not providers:
            return []
        return [_PROVIDER_MAP.get(p, p) for p in providers]

    def deployed_keys(self, manifest: dict) -> set[str]:
        return set()
