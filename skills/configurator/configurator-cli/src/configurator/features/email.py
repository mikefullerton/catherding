"""Email feature — SMTP / transactional email configuration."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_PROVIDERS = [
    ("resend", "Resend"),
    ("sendgrid", "SendGrid"),
    ("ses", "Amazon SES"),
    ("smtp", "Custom SMTP"),
]


class EmailFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="email", label="Email", version=_VERSION,
            order=50, dependencies=["backend"],
        )

    def config_html(self, ctx: RenderContext) -> str:
        options = "\n        ".join(
            f'<option value="{pid}">{label}</option>' for pid, label in _PROVIDERS
        )
        return f"""<fieldset>
<legend>Email</legend>
<div class="field">
    <label><input type="checkbox" id="email-enabled"> Enable transactional email</label>
</div>
<div class="field">
    <label for="email-provider">Provider</label>
    <select id="email-provider" data-key="email.provider">
        <option value="">-- select --</option>
        {options}
    </select>
</div>
<div class="field">
    <label for="email-from-address">From address</label>
    <input type="email" id="email-from-address" data-key="email.from_address" placeholder="noreply@example.com">
</div>
<div class="field">
    <label for="email-from-name">From name</label>
    <input type="text" id="email-from-name" data-key="email.from_name" placeholder="My App">
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Email
    if ($("#email-enabled").checked) {
        const email = { enabled: true };
        const provider = $("#email-provider").value;
        if (provider) email.provider = provider;
        const fromAddr = $("#email-from-address").value.trim();
        if (fromAddr) email.from_address = fromAddr;
        const fromName = $("#email-from-name").value.trim();
        if (fromName) email.from_name = fromName;
        cfg.email = email;
    } else {
        cfg.email = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // Email
    const email = CONFIG.email || {};
    $("#email-enabled").checked = !!email.enabled;
    $("#email-provider").value = email.provider || "";
    $("#email-from-address").value = email.from_address || "";
    $("#email-from-name").value = email.from_name || "";"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Email — disable fields when not enabled
    const emailOn = $("#email-enabled").checked;
    $("#email-provider").disabled = !emailOn;
    $("#email-from-address").disabled = !emailOn;
    $("#email-from-name").disabled = !emailOn;"""

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        email = manifest.get("features", {}).get("email", {})
        if not email.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if email.get("provider"):
            cfg["provider"] = email["provider"]
        if email.get("from_address"):
            cfg["from_address"] = email["from_address"]
        if email.get("from_name"):
            cfg["from_name"] = email["from_name"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        email = manifest.get("features", {}).get("email", {})
        if email.get("enabled"):
            return {"email"}
        return set()
