"""Tests for config identifiers."""

from configurator.features import discover_features


class TestConfigIdentifiers:
    def test_all_identifiers_use_hyphens(self):
        for feature in discover_features():
            for ident in feature.config_identifiers():
                assert "_" not in ident, f"{ident} uses underscores, should use hyphens"

    def test_all_identifiers_start_with_feature_prefix(self):
        for feature in discover_features():
            ids = feature.config_identifiers()
            if not ids:
                continue
            # All identifiers should start with a consistent prefix
            prefixes = {ident.split(".")[0] for ident in ids}
            assert len(prefixes) == 1, f"{feature.meta().id} has mixed prefixes: {prefixes}"

    def test_all_identifiers_have_valid_types(self):
        valid_types = {"bool", "string", "int", "enum", "list"}
        for feature in discover_features():
            for ident, vtype in feature.config_identifiers().items():
                assert vtype in valid_types, f"{ident} has invalid type '{vtype}'"

    def test_no_duplicate_identifiers(self):
        all_ids: list[str] = []
        for feature in discover_features():
            all_ids.extend(feature.config_identifiers().keys())
        assert len(all_ids) == len(set(all_ids)), "Duplicate identifiers found"

    def test_read_only_features_return_empty(self):
        by_id = {f.meta().id: f for f in discover_features()}
        assert by_id["data_model"].config_identifiers() == {}
        assert by_id["api_view"].config_identifiers() == {}
        assert by_id["credentials"].config_identifiers() == {}

    def test_total_identifier_count(self):
        total = sum(len(f.config_identifiers()) for f in discover_features())
        assert total == 60

    def test_specific_identifiers_exist(self):
        all_ids: dict[str, str] = {}
        for feature in discover_features():
            all_ids.update(feature.config_identifiers())
        assert "project.display-name" in all_ids
        assert "backend.enabled" in all_ids
        assert "email.from-address" in all_ids
        assert "auth.providers" in all_ids
        assert "ab-testing.client-key" in all_ids
        assert "backend.environments.staging" in all_ids
