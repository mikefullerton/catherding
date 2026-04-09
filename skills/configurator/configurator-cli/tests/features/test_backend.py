"""Tests for BackendFeature."""

from configurator.features.backend import BackendFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestManifestToConfig:
    def test_backend_service(self):
        f = BackendFeature()
        cfg = f.manifest_to_config({"services": {"backend": {"status": "deployed"}}})
        assert cfg["enabled"] is True
        assert cfg["type"] == "full"

    def test_api_service(self):
        f = BackendFeature()
        cfg = f.manifest_to_config({"services": {"api": {"domain": "api.example.com"}}})
        assert cfg["enabled"] is True
        assert cfg["domain"] == "api.example.com"

    def test_api_docs_only(self):
        f = BackendFeature()
        cfg = f.manifest_to_config({"services": {"api-docs": {"domain": "docs.example.com"}}})
        assert cfg["enabled"] is True
        assert cfg["docs_domain"] == "docs.example.com"

    def test_backend_with_docs(self):
        f = BackendFeature()
        cfg = f.manifest_to_config({"services": {
            "backend": {"domain": "backend.example.com"},
            "api-docs": {"domain": "api.example.com"},
        }})
        assert cfg["domain"] == "backend.example.com"
        assert cfg["docs_domain"] == "api.example.com"

    def test_no_backend(self):
        f = BackendFeature()
        assert f.manifest_to_config({"services": {}}) == {"enabled": False}

    def test_backend_without_domain(self):
        f = BackendFeature()
        cfg = f.manifest_to_config({"services": {"backend": {"platform": "railway"}}})
        assert cfg["enabled"] is True
        assert "domain" not in cfg

    def test_staging_service(self):
        f = BackendFeature()
        cfg = f.manifest_to_config({"services": {
            "backend": {"domain": "backend.example.com"},
            "backend-staging": {"domain": "staging.example.com"},
        }})
        assert cfg["environments"]["staging"] is True
        assert "testing" not in cfg["environments"]

    def test_testing_service(self):
        f = BackendFeature()
        cfg = f.manifest_to_config({"services": {
            "backend": {},
            "backend-testing": {"domain": "test.example.com"},
        }})
        assert cfg["environments"]["testing"] is True

    def test_environments_from_features(self):
        f = BackendFeature()
        cfg = f.manifest_to_config({
            "services": {"backend": {}},
            "features": {"backend": {"environments": {"staging": True, "testing": True}}},
        })
        assert cfg["environments"]["staging"] is True
        assert cfg["environments"]["testing"] is True

    def test_no_environments_when_none(self):
        f = BackendFeature()
        cfg = f.manifest_to_config({"services": {"backend": {}}})
        assert "environments" not in cfg


class TestDeployedKeys:
    def test_backend_deployed(self):
        assert "backend" in BackendFeature().deployed_keys({"services": {"backend": {}}})

    def test_api_counts(self):
        assert "backend" in BackendFeature().deployed_keys({"services": {"api": {}}})

    def test_empty(self):
        assert BackendFeature().deployed_keys({"services": {}}) == set()


class TestConfigHtml:
    def test_contains_enable_checkbox(self):
        html = BackendFeature().config_html(ctx())
        assert 'id="be-enabled"' in html

    def test_deployed_badge(self):
        html = BackendFeature().config_html(ctx(deployed_keys={"backend"}))
        assert 'id="be-deployed" style=""' in html

    def test_live_badge(self):
        html = BackendFeature().config_html(ctx(live_domains={"backend"}))
        assert 'id="be-live" style=""' in html
