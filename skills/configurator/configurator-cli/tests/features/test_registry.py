"""Tests for the feature registry and discovery."""

from configurator.features import discover_features, _topo_sort
from configurator.features.base import Feature


class TestDiscoverFeatures:
    def test_returns_all_features(self):
        features = discover_features()
        assert len(features) == 8

    def test_feature_ids(self):
        ids = [f.meta().id for f in discover_features()]
        assert set(ids) == {"project", "website", "backend", "admin", "dashboard", "auth", "email", "sms"}

    def test_project_is_first(self):
        features = discover_features()
        assert features[0].meta().id == "project"

    def test_dependencies_come_before_dependents(self):
        features = discover_features()
        seen: set[str] = set()
        for f in features:
            for dep in f.meta().dependencies:
                assert dep in seen, f"{f.meta().id} depends on {dep} but {dep} hasn't appeared yet"
            seen.add(f.meta().id)

    def test_all_are_feature_instances(self):
        for f in discover_features():
            assert isinstance(f, Feature)

    def test_admin_and_dashboard_share_group(self):
        features = discover_features()
        by_id = {f.meta().id: f for f in features}
        assert by_id["admin"].meta().group == "admin_sites"
        assert by_id["dashboard"].meta().group == "admin_sites"

    def test_no_duplicate_ids(self):
        features = discover_features()
        ids = [f.meta().id for f in features]
        assert len(ids) == len(set(ids))

    def test_all_have_versions(self):
        for f in discover_features():
            assert f.meta().version, f"{f.meta().id} has no version"


class TestTopoSort:
    def test_respects_order_for_independent_features(self):
        features = discover_features()
        orders = [f.meta().order for f in features]
        # Project (0) must come before everything
        assert orders[0] == 0
