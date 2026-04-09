"""Logging feature — structured logging / observability configuration."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_PROVIDERS = [
    ("axiom", "Axiom"),
    ("datadog", "Datadog"),
    ("logtail", "Logtail"),
    ("sentry", "Sentry"),
]


class LoggingFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="logging", label="Logging", version=_VERSION,
            order=70, dependencies=["backend"],
        )

    def config_html(self, ctx: RenderContext) -> str:
        options = "\n        ".join(
            f'<option value="{pid}">{label}</option>' for pid, label in _PROVIDERS
        )
        return f"""<fieldset>
<legend>Logging</legend>
<div class="field">
    <label><input type="checkbox" id="logging-enabled"> Enable structured logging</label>
</div>
<div class="field">
    <label for="logging-provider">Provider</label>
    <select id="logging-provider" data-key="logging.provider">
        <option value="">-- select --</option>
        {options}
    </select>
</div>
<div class="field">
    <label for="logging-level">Default level</label>
    <select id="logging-level" data-key="logging.level">
        <option value="debug">Debug</option>
        <option value="info" selected>Info</option>
        <option value="warn">Warn</option>
        <option value="error">Error</option>
    </select>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Logging
    if ($("#logging-enabled").checked) {
        const logging = { enabled: true };
        const provider = $("#logging-provider").value;
        if (provider) logging.provider = provider;
        const level = $("#logging-level").value;
        if (level) logging.level = level;
        cfg.logging = logging;
    } else {
        cfg.logging = { enabled: false };
    }"""

    def config_js_populate(self) -> str:
        return """\
    // Logging
    const logging = CONFIG.logging || {};
    $("#logging-enabled").checked = !!logging.enabled;
    $("#logging-provider").value = logging.provider || "";
    $("#logging-level").value = logging.level || "info";"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Logging — disable fields when not enabled
    const loggingOn = $("#logging-enabled").checked;
    $("#logging-provider").disabled = !loggingOn;
    $("#logging-level").disabled = !loggingOn;"""

    def default_config(self) -> dict:
        return {"enabled": False}

    def manifest_to_config(self, manifest: dict) -> dict:
        logging = manifest.get("features", {}).get("logging", {})
        if not logging.get("enabled"):
            return {"enabled": False}
        cfg: dict = {"enabled": True}
        if logging.get("provider"):
            cfg["provider"] = logging["provider"]
        if logging.get("level"):
            cfg["level"] = logging["level"]
        return cfg

    def deployed_keys(self, manifest: dict) -> set[str]:
        logging = manifest.get("features", {}).get("logging", {})
        if logging.get("enabled"):
            return {"logging"}
        return set()
