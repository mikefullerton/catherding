"""Feature plugin registry for the configurator."""

from __future__ import annotations

from configurator.features.base import Feature


def discover_features() -> list[Feature]:
    """Return all feature instances, topologically sorted by dependencies."""
    from configurator.features.project import ProjectFeature
    from configurator.features.website import WebsiteFeature
    from configurator.features.backend import BackendFeature
    from configurator.features.admin import AdminFeature
    from configurator.features.dashboard import DashboardFeature
    from configurator.features.auth import AuthFeature

    features = [
        ProjectFeature(),
        WebsiteFeature(),
        BackendFeature(),
        AdminFeature(),
        DashboardFeature(),
        AuthFeature(),
    ]
    return _topo_sort(features)


def _topo_sort(features: list[Feature]) -> list[Feature]:
    """Topological sort respecting dependencies, stable within same level by order."""
    by_id = {f.meta().id: f for f in features}
    visited: set[str] = set()
    result: list[Feature] = []

    def visit(fid: str) -> None:
        if fid in visited:
            return
        visited.add(fid)
        for dep in by_id[fid].meta().dependencies:
            visit(dep)
        result.append(by_id[fid])

    for f in sorted(features, key=lambda f: f.meta().order):
        visit(f.meta().id)

    return result
