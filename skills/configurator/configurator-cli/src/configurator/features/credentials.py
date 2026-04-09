"""Credentials feature — keychain secret status and management."""

from __future__ import annotations

import subprocess

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.1.0"

KEYCHAIN_SERVICE = "configurator"

# (key, label, reason)
CREDENTIAL_DEFS = [
    ("cloudflare_api_token", "Cloudflare API token", "Deploy workers and DNS records to Cloudflare"),
    ("cloudflare_account_id", "Cloudflare account ID", "Identify your Cloudflare account for deployments"),
    ("railway_token", "Railway token", "Deploy backend API and database to Railway"),
    ("github_token", "GitHub token", "Create repos, set secrets, push code"),
    ("database_url", "Database URL", "Connect backend to PostgreSQL database"),
]


def keychain_has(key: str) -> bool:
    """Check if a credential exists in macOS keychain."""
    result = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", key, "-w"],
        capture_output=True, text=True,
    )
    return result.returncode == 0


class CredentialsFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="credentials", label="Secrets", version=_VERSION,
            order=80, dependencies=["project"], category="secrets",
        )

    def config_html(self, ctx: RenderContext) -> str:
        rows: list[str] = []
        any_missing = False
        for key, label, reason in CREDENTIAL_DEFS:
            present = keychain_has(key)
            if present:
                icon = '<span class="secret-ok">set</span>'
            else:
                icon = '<span class="secret-missing">missing</span>'
                any_missing = True
            rows.append(
                f'<div class="secret-row">'
                f'<span class="secret-name">{label}</span>'
                f'{icon}'
                f'<span class="secret-reason">{reason}</span>'
                f'</div>'
            )

        hint = ""
        if any_missing:
            hint = (
                '<div class="secret-hint">'
                'Run <code>configurator --set-credentials</code> in your terminal to set missing secrets.'
                '</div>'
            )

        rows_html = "\n".join(rows)
        return f"""<fieldset>
<legend>Secrets</legend>
<div class="field">
    <div class="secret-list">
        {rows_html}
    </div>
    {hint}
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        # Secrets are read-only in the web UI — they're managed via --set-credentials
        return ""

    def config_js_populate(self) -> str:
        return ""

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
