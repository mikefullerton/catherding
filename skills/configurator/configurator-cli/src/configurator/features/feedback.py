"""Feedback feature — user feedback and bug reporting widget."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_DESTINATIONS = [
    ("github", "GitHub Issues"),
    ("email", "Email"),
    ("api", "Backend API endpoint"),
]


class FeedbackFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="feedback", label="Feedback", version=_VERSION,
            order=14, dependencies=["website"], category="ux",
        )

    def config_html(self, ctx: RenderContext) -> str:
        options = "\n        ".join(
            f'<option value="{did}">{label}</option>' for did, label in _DESTINATIONS
        )
        return f"""<fieldset>
<legend>Feedback / Bug Reporting</legend>
<div class="field">
    <label><input type="checkbox" id="feedback-enabled"> Enable feedback widget</label>
</div>
<div class="field">
    <label for="feedback-destination">Report destination</label>
    <select id="feedback-destination" data-key="feedback.destination">
        <option value="">-- select --</option>
        {options}
    </select>
</div>
<div class="field">
    <label><input type="checkbox" id="feedback-screenshots"> Allow screenshot attachments</label>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Feedback
    if ($("#feedback-enabled").checked) {
        const fb = { enabled: true };
        const dest = $("#feedback-destination").value;
        if (dest) fb.destination = dest;
        fb.screenshots = $("#feedback-screenshots").checked;
        cfg.feedback = fb;
    } else {
        cfg.feedback = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // Feedback
    const fb = CONFIG.feedback || {};
    $("#feedback-enabled").checked = !!fb.enabled;
    $("#feedback-destination").value = fb.destination || "";
    $("#feedback-screenshots").checked = !!fb.screenshots;"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Feedback — disable fields when not enabled
    const fbOn = $("#feedback-enabled").checked;
    $("#feedback-destination").disabled = !fbOn;
    $("#feedback-screenshots").disabled = !fbOn;"""

    def config_identifiers(self) -> dict[str, str]:
        return {
            "feedback.enabled": "bool",
            "feedback.destination": "string",
            "feedback.screenshots": "bool",
        }

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        fb = manifest.get("features", {}).get("feedback", {})
        if not fb.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if fb.get("destination"):
            cfg["destination"] = fb["destination"]
        if "screenshots" in fb:
            cfg["screenshots"] = fb["screenshots"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        fb = manifest.get("features", {}).get("feedback", {})
        if fb.get("enabled"):
            return {"feedback"}
        return set()
