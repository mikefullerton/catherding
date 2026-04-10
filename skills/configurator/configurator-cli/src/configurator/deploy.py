"""Deploy plan logic — determines what needs deploying vs. what can be skipped."""

from __future__ import annotations

from configurator.features import discover_features
from configurator.cli import _apply_feature_config


def feature_versions() -> dict[str, str]:
    """Return {feature_id: version} for all registered features."""
    return {f.meta().id: f.meta().version for f in discover_features()}


def deploy_plan(config: dict, manifest: dict) -> dict:
    """Compare config against manifest and categorize each feature.

    Returns::

        {
            "skip": [{"id": "website", "version": "1.0.1", "reason": "..."}],
            "update": [{"id": "backend", "version": "1.1.0", "reason": "..."}],
            "add": [{"id": "dashboard", "version": "1.0.0", "reason": "..."}],
        }
    """
    manifest_versions = manifest.get("feature_versions", {})
    features = discover_features()

    skip: list[dict] = []
    update: list[dict] = []
    add: list[dict] = []

    for feature in features:
        meta = feature.meta()
        fid = meta.id

        # Get what this feature thinks the config should be from the manifest
        from_manifest = feature.manifest_to_config(manifest)
        deployed_keys = feature.deployed_keys(manifest)

        # Get what the config says this feature should be
        current_cfg: dict = {}
        _apply_feature_config(current_cfg, feature, feature.default_config())
        desired_cfg: dict = {}
        _apply_feature_config(desired_cfg, feature, _extract_feature_config(config, feature))

        # Is this feature even desired in the new config?
        if desired_cfg == current_cfg and not deployed_keys:
            # Feature is at defaults and not deployed — nothing to do
            continue

        if not deployed_keys:
            # Not deployed but desired → add
            add.append({
                "id": fid,
                "version": meta.version,
                "reason": "not yet deployed",
            })
            continue

        # Feature is deployed — check if version matches
        manifest_version = manifest_versions.get(fid)

        if manifest_version == meta.version:
            # Same version — check if config changed
            manifest_cfg: dict = {}
            _apply_feature_config(manifest_cfg, feature, from_manifest)

            if manifest_cfg == desired_cfg:
                skip.append({
                    "id": fid,
                    "version": meta.version,
                    "reason": f"v{meta.version} already deployed, config unchanged",
                })
            else:
                update.append({
                    "id": fid,
                    "version": meta.version,
                    "reason": "config changed",
                })
        else:
            old = manifest_version or "unknown"
            update.append({
                "id": fid,
                "version": meta.version,
                "reason": f"version {old} -> {meta.version}",
            })

    return {"skip": skip, "update": update, "add": add}


def _extract_feature_config(config: dict, feature):
    """Extract a feature's config from the full config dict."""
    fid = feature.meta().id
    if fid == "project":
        # Project fields live at the top level
        return {k: config.get(k) for k in ("repo", "org", "domain", "port", "display_name", "local_path")
                if config.get(k) is not None}
    elif fid == "admin":
        return config.get("admin_sites", {}).get("admin", feature.default_config())
    elif fid == "dashboard":
        return config.get("admin_sites", {}).get("dashboard", feature.default_config())
    elif fid == "auth":
        return config.get("auth_providers", feature.default_config())
    else:
        return config.get(fid, feature.default_config())
