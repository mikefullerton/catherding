"""Theme feature — dark/light mode configuration for user site."""

from __future__ import annotations

from configurator.features.base import Feature, FeatureMeta, RenderContext

_VERSION = "1.0.0"

_MODES = [
    ("system", "System preference"),
    ("light", "Light only"),
    ("dark", "Dark only"),
    ("toggle", "User toggle (default light)"),
]


class ThemeFeature(Feature):
    def meta(self) -> FeatureMeta:
        return FeatureMeta(
            id="theme", label="Theme", version=_VERSION,
            order=11, dependencies=["website"], category="ux",
        )

    def config_html(self, ctx: RenderContext) -> str:
        options = "\n        ".join(
            f'<option value="{mid}">{label}</option>' for mid, label in _MODES
        )
        return f"""<fieldset>
<legend>Theme</legend>
<div class="field">
    <label for="theme-mode">Color mode</label>
    <select id="theme-mode" data-key="theme.mode">
        {options}
    </select>
</div>
</fieldset>"""

    def config_js_read(self) -> str:
        return """\
    // Theme
    const themeMode = $("#theme-mode").value;
    if (themeMode) cfg.theme = { mode: themeMode };"""

    def config_js_populate(self) -> str:
        return """\
    // Theme
    const theme = CONFIG.theme || {};
    $("#theme-mode").value = theme.mode || "system";"""

    def config_js_update_disabled(self) -> str:
        return ""

    def default_config(self) -> dict:
        return {"mode": "system"}

    def manifest_to_config(self, manifest: dict) -> dict:
        theme = manifest.get("features", {}).get("theme", {})
        cfg: dict = {}
        if theme.get("mode"):
            cfg["mode"] = theme["mode"]
        return cfg if cfg else {"mode": "system"}

    def deployed_keys(self, manifest: dict) -> set[str]:
        theme = manifest.get("features", {}).get("theme", {})
        if theme.get("mode"):
            return {"theme"}
        return set()
