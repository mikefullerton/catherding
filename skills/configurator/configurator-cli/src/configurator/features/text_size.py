"""Text size feature — system or custom font size for user site."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_MODES = [
    ("system", "Follow system text size"),
    ("small", "Small (14px)"),
    ("medium", "Medium (16px)"),
    ("large", "Large (18px)"),
    ("custom", "Custom"),
]


class TextSizeFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="text_size", label="Text Size", version=_VERSION,
            order=12, dependencies=["website"],
        )

    def config_html(self, ctx: RenderContext) -> str:
        options = "\n        ".join(
            f'<option value="{mid}">{label}</option>' for mid, label in _MODES
        )
        return f"""<fieldset>
<legend>Text Size</legend>
<div class="field">
    <label for="text-size-mode">Base font size</label>
    <select id="text-size-mode" data-key="text_size.mode">
        {options}
    </select>
</div>
<div class="field" id="text-size-custom-field" style="display:none">
    <label for="text-size-custom">Custom size (px)</label>
    <input type="text" id="text-size-custom" data-key="text_size.custom_px" inputmode="numeric" pattern="[0-9]*" placeholder="16">
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Text size
    const tsMode = $("#text-size-mode").value;
    if (tsMode) {
        const ts = { mode: tsMode };
        if (tsMode === "custom") {
            const px = parseInt($("#text-size-custom").value, 10);
            if (px > 0) ts.custom_px = px;
        }
        cfg.text_size = ts;
    }"""

    def config_js_populate(self) -> str:
        return """\
    // Text size
    const ts = CONFIG.text_size || {};
    $("#text-size-mode").value = ts.mode || "system";
    $("#text-size-custom").value = ts.custom_px || "";
    $("#text-size-custom-field").style.display = ts.mode === "custom" ? "" : "none";"""

    def config_js_update_disabled(self) -> str:
        return """\
    // Text size — show custom field only when mode is "custom"
    const tsCustom = $("#text-size-mode").value === "custom";
    $("#text-size-custom-field").style.display = tsCustom ? "" : "none";"""

    def default_config(self) -> dict:
        return {"mode": "system"}

    def manifest_to_config(self, manifest: dict) -> dict:
        ts = manifest.get("features", {}).get("text_size", {})
        cfg: dict = {}
        if ts.get("mode"):
            cfg["mode"] = ts["mode"]
        if ts.get("custom_px"):
            cfg["custom_px"] = ts["custom_px"]
        return cfg if cfg else {"mode": "system"}

    def deployed_keys(self, manifest: dict) -> set[str]:
        ts = manifest.get("features", {}).get("text_size", {})
        if ts.get("mode"):
            return {"text_size"}
        return set()
