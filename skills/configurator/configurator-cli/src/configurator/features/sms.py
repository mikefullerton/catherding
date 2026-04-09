"""SMS feature — transactional SMS / messaging configuration."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_PROVIDERS = [
    ("twilio", "Twilio"),
    ("vonage", "Vonage"),
    ("aws-sns", "Amazon SNS"),
]


class SmsFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="sms", label="SMS", version=_VERSION,
            order=51, dependencies=["backend"], column="right",
        )

    def config_html(self, ctx: RenderContext) -> str:
        options = "\n        ".join(
            f'<option value="{pid}">{label}</option>' for pid, label in _PROVIDERS
        )
        return f"""<fieldset>
<legend>SMS</legend>
<div class="field">
    <label><input type="checkbox" id="sms-enabled"> Enable SMS messaging</label>
</div>
<div class="field">
    <label for="sms-provider">Provider</label>
    <select id="sms-provider" data-key="sms.provider">
        <option value="">-- select --</option>
        {options}
    </select>
</div>
<div class="field">
    <label for="sms-from-number">From number</label>
    <input type="tel" id="sms-from-number" data-key="sms.from_number" placeholder="+15551234567">
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // SMS
    if ($("#sms-enabled").checked) {
        const sms = { enabled: true };
        const provider = $("#sms-provider").value;
        if (provider) sms.provider = provider;
        const fromNum = $("#sms-from-number").value.trim();
        if (fromNum) sms.from_number = fromNum;
        cfg.sms = sms;
    } else {
        cfg.sms = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // SMS
    const sms = CONFIG.sms || {};
    $("#sms-enabled").checked = !!sms.enabled;
    $("#sms-provider").value = sms.provider || "";
    $("#sms-from-number").value = sms.from_number || "";"""

    def config_js_update_disabled(self) -> str:
        return """\
    // SMS — disable fields when not enabled
    const smsOn = $("#sms-enabled").checked;
    $("#sms-provider").disabled = !smsOn;
    $("#sms-from-number").disabled = !smsOn;"""

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        sms = manifest.get("features", {}).get("sms", {})
        if not sms.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if sms.get("provider"):
            cfg["provider"] = sms["provider"]
        if sms.get("from_number"):
            cfg["from_number"] = sms["from_number"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        sms = manifest.get("features", {}).get("sms", {})
        if sms.get("enabled"):
            return {"sms"}
        return set()
