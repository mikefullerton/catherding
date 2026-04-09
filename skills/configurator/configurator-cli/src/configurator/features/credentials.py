"""Credentials feature — keychain credential and API key management."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_CREDENTIAL_KEYS = [
    ("cloudflare_api_token", "Cloudflare API token"),
    ("cloudflare_account_id", "Cloudflare account ID"),
    ("railway_token", "Railway token"),
    ("github_token", "GitHub token"),
    ("database_url", "Database URL"),
]


class CredentialsFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="credentials", label="Credentials", version=_VERSION,
            order=80, dependencies=["project"],
        )

    def config_html(self, ctx: RenderContext) -> str:
        checkboxes = "\n        ".join(
            f'<label><input type="checkbox" id="cred-{kid}" value="{kid}"> <span>{label}</span></label>'
            for kid, label in _CREDENTIAL_KEYS
        )
        return f"""<fieldset>
<legend>Credentials</legend>
<div class="field">
    <label>Required credentials (stored in macOS Keychain)</label>
    <div class="checkbox-group">
        {checkboxes}
    </div>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        checks = "\n".join(
            f'        if ($("#cred-{kid}").checked) creds.push("{kid}");'
            for kid, _ in _CREDENTIAL_KEYS
        )
        return f"""\
    // Credentials
    const creds = [];
{checks}
    if (creds.length) cfg.credentials = creds;"""

    def config_js_populate(self) -> str:
        sets = "\n".join(
            f'    $("#cred-{kid}").checked = creds.includes("{kid}");'
            for kid, _ in _CREDENTIAL_KEYS
        )
        return f"""\
    // Credentials
    const creds = CONFIG.credentials || [];
{sets}"""

    def config_js_update_disabled(self) -> str:
        return ""

    def default_config(self) -> list:
        return []

    def manifest_to_config(self, manifest: dict) -> list:
        creds = manifest.get("features", {}).get("credentials", [])
        if isinstance(creds, dict):
            creds = creds.get("keys", [])
        return list(creds)

    def deployed_keys(self, manifest: dict) -> set[str]:
        return set()
