"""Tests for ProjectFeature."""

from configurator.features.project import ProjectFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestManifestToConfig:
    def test_maps_display_name(self):
        f = ProjectFeature()
        cfg = f.manifest_to_config({"project": {"displayName": "My Project"}})
        assert cfg["displayName"] == "My Project"

    def test_maps_name_to_repo(self):
        f = ProjectFeature()
        assert f.manifest_to_config({"project": {"name": "my-repo"}}) == {"repo": "my-repo"}

    def test_maps_org(self):
        f = ProjectFeature()
        cfg = f.manifest_to_config({"project": {"org": "my-org"}})
        assert cfg["org"] == "my-org"

    def test_maps_domain(self):
        f = ProjectFeature()
        cfg = f.manifest_to_config({"project": {"domain": "example.com"}})
        assert cfg["domain"] == "example.com"

    def test_empty_manifest(self):
        f = ProjectFeature()
        assert f.manifest_to_config({}) == {}

    def test_missing_fields(self):
        f = ProjectFeature()
        assert f.manifest_to_config({"project": {}}) == {}

    def test_all_fields(self):
        f = ProjectFeature()
        cfg = f.manifest_to_config({
            "project": {
                "displayName": "Cool App",
                "name": "cool-app",
                "org": "my-org",
                "domain": "cool-app.com",
            }
        })
        assert cfg == {
            "displayName": "Cool App",
            "repo": "cool-app",
            "org": "my-org",
            "domain": "cool-app.com",
        }


class TestDeployedKeys:
    def test_repo_deployed(self):
        f = ProjectFeature()
        assert "repo" in f.deployed_keys({"project": {"name": "test"}})

    def test_org_deployed(self):
        f = ProjectFeature()
        assert "org" in f.deployed_keys({"project": {"org": "test-org"}})

    def test_empty(self):
        f = ProjectFeature()
        assert f.deployed_keys({}) == set()


class TestConfigHtml:
    def test_contains_display_name_input(self):
        f = ProjectFeature()
        html = f.config_html(ctx())
        assert 'id="display-name"' in html

    def test_contains_repo_input(self):
        f = ProjectFeature()
        html = f.config_html(ctx())
        assert 'id="repo"' in html

    def test_contains_org_select(self):
        f = ProjectFeature()
        html = f.config_html(ctx())
        assert 'id="org"' in html

    def test_contains_domain_input(self):
        f = ProjectFeature()
        html = f.config_html(ctx())
        assert 'id="domain"' in html

    def test_wrapped_in_fieldset(self):
        f = ProjectFeature()
        html = f.config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestMeta:
    def test_id(self):
        assert ProjectFeature().meta().id == "project"

    def test_no_dependencies(self):
        assert ProjectFeature().meta().dependencies == []

    def test_order_is_zero(self):
        assert ProjectFeature().meta().order == 0

    def test_no_group(self):
        assert ProjectFeature().meta().group is None


class TestDefaultConfig:
    def test_has_required_keys(self):
        cfg = ProjectFeature().default_config()
        assert "displayName" in cfg
        assert "repo" in cfg
        assert "org" in cfg
        assert "domain" in cfg
