"""Tests for the API View feature."""

from configurator.features.api_view import ApiViewFeature, _default_endpoints, _infer_description
from configurator.features.base import RenderContext


class TestApiViewFeature:
    def setup_method(self):
        self.feature = ApiViewFeature()

    def test_meta(self):
        meta = self.feature.meta()
        assert meta.id == "api_view"
        assert meta.category == "api-view"
        assert "backend" in meta.dependencies

    def test_no_backend_shows_message(self):
        ctx = RenderContext(deployed_keys=set(), urls={}, live_domains=set(), config={})
        html = self.feature.config_html(ctx)
        assert "No backend configured" in html

    def test_backend_enabled_shows_default_endpoints(self):
        ctx = RenderContext(
            deployed_keys=set(), urls={}, live_domains=set(),
            config={
                "backend": {"enabled": True, "domain": "api.test.com"},
                "auth_providers": ["email/password"],
            },
        )
        html = self.feature.config_html(ctx)
        assert "api.test.com" in html
        assert "/api/health" in html
        assert "/api/auth/login" in html
        assert "/api/auth/register" in html

    def test_backend_with_admin_shows_admin_endpoints(self):
        ctx = RenderContext(
            deployed_keys=set(), urls={}, live_domains=set(),
            config={
                "backend": {"enabled": True},
                "auth_providers": ["email/password"],
                "admin_sites": {"admin": {"enabled": True}},
            },
        )
        html = self.feature.config_html(ctx)
        assert "/api/admin/users" in html

    def test_read_only(self):
        assert self.feature.config_js_read() == ""
        assert self.feature.config_js_populate() == ""
        assert self.feature.config_js_update_disabled() == ""
        assert self.feature.default_config() == {}
        assert self.feature.deployed_keys({}) == set()


class TestDefaultEndpoints:
    def test_health_always_present(self):
        eps = _default_endpoints({"backend": {"enabled": True}})
        paths = [e["path"] for e in eps]
        assert "/api/health" in paths

    def test_auth_endpoints_when_providers(self):
        eps = _default_endpoints({"auth_providers": ["email/password"]})
        paths = [e["path"] for e in eps]
        assert "/api/auth/login" in paths
        assert "/api/auth/register" in paths
        assert "/api/auth/me" in paths

    def test_no_auth_endpoints_without_providers(self):
        eps = _default_endpoints({})
        paths = [e["path"] for e in eps]
        assert "/api/auth/login" not in paths

    def test_admin_endpoints_when_admin_enabled(self):
        eps = _default_endpoints({
            "auth_providers": ["email/password"],
            "admin_sites": {"admin": {"enabled": True}},
        })
        paths = [e["path"] for e in eps]
        assert "/api/admin/users" in paths


class TestInferDescription:
    def test_get(self):
        assert "Get" in _infer_description("GET", "/api/users")

    def test_post(self):
        assert "Create" in _infer_description("POST", "/api/users")

    def test_delete(self):
        assert "Delete" in _infer_description("DELETE", "/api/users/:id")
