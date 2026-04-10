"""Tests for deploy plan logic."""

from configurator.deploy import deploy_plan, feature_versions


class TestFeatureVersions:
    def test_returns_all_features(self):
        versions = feature_versions()
        assert "project" in versions
        assert "website" in versions
        assert "backend" in versions
        assert "auth" in versions

    def test_versions_are_strings(self):
        versions = feature_versions()
        for fid, ver in versions.items():
            assert isinstance(ver, str), f"{fid} version is not a string"
            parts = ver.split(".")
            assert len(parts) == 3, f"{fid} version {ver} is not semver"


class TestDeployPlan:
    def test_empty_manifest_adds_configured_features(self):
        config = {
            "repo": "test",
            "domain": "test.com",
            "backend": {"enabled": True, "domain": "api.test.com"},
        }
        manifest = {"project": {"name": "test"}, "services": {}}
        plan = deploy_plan(config, manifest)
        # Backend is in config but not deployed → add
        add_ids = [item["id"] for item in plan["add"]]
        assert "backend" in add_ids

    def test_matching_version_and_config_skips(self):
        versions = feature_versions()
        config = {
            "repo": "test",
            "domain": "test.com",
            "website": {"type": "existing", "domain": "test.com"},
        }
        manifest = {
            "project": {"name": "test", "domain": "test.com"},
            "services": {"main": {"platform": "cloudflare", "domain": "test.com"}},
            "feature_versions": versions,
        }
        plan = deploy_plan(config, manifest)
        skip_ids = [item["id"] for item in plan["skip"]]
        assert "website" in skip_ids

    def test_version_mismatch_triggers_update(self):
        config = {
            "repo": "test",
            "domain": "test.com",
            "website": {"type": "existing", "domain": "test.com"},
        }
        manifest = {
            "project": {"name": "test", "domain": "test.com"},
            "services": {"main": {"platform": "cloudflare", "domain": "test.com"}},
            "feature_versions": {"website": "0.0.1"},  # old version
        }
        plan = deploy_plan(config, manifest)
        update_ids = [item["id"] for item in plan["update"]]
        assert "website" in update_ids

    def test_no_feature_versions_in_manifest_triggers_update(self):
        config = {
            "repo": "test",
            "domain": "test.com",
            "website": {"type": "existing"},
        }
        manifest = {
            "project": {"name": "test"},
            "services": {"main": {"platform": "cloudflare"}},
            # No feature_versions key at all
        }
        plan = deploy_plan(config, manifest)
        update_ids = [item["id"] for item in plan["update"]]
        assert "website" in update_ids

    def test_config_change_triggers_update_even_with_same_version(self):
        versions = feature_versions()
        config = {
            "repo": "test",
            "domain": "test.com",
            "backend": {"enabled": True, "domain": "api.test.com"},
        }
        manifest = {
            "project": {"name": "test"},
            "services": {"backend": {"platform": "railway", "domain": "old-api.test.com"}},
            "feature_versions": versions,
        }
        plan = deploy_plan(config, manifest)
        update_ids = [item["id"] for item in plan["update"]]
        assert "backend" in update_ids

    def test_plan_has_correct_structure(self):
        plan = deploy_plan({}, {"project": {"name": "test"}, "services": {}})
        assert "skip" in plan
        assert "update" in plan
        assert "add" in plan
        assert isinstance(plan["skip"], list)
        assert isinstance(plan["update"], list)
        assert isinstance(plan["add"], list)

    def test_each_entry_has_required_fields(self):
        config = {
            "repo": "test",
            "domain": "test.com",
            "backend": {"enabled": True, "domain": "api.test.com"},
        }
        manifest = {"project": {"name": "test"}, "services": {}}
        plan = deploy_plan(config, manifest)
        for category in ("skip", "update", "add"):
            for entry in plan[category]:
                assert "id" in entry
                assert "version" in entry
                assert "reason" in entry
