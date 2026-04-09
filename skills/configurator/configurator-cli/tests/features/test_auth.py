"""Tests for AuthFeature."""

from configurator.features.auth import AuthFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestManifestToConfig:
    def test_email_maps_to_email_password(self):
        f = AuthFeature()
        assert f.manifest_to_config({"features": {"auth": {"providers": ["email"]}}}) == ["email/password"]

    def test_email_password_passes_through(self):
        f = AuthFeature()
        assert f.manifest_to_config({"features": {"auth": {"providers": ["email/password"]}}}) == ["email/password"]

    def test_github_passes_through(self):
        f = AuthFeature()
        assert f.manifest_to_config({"features": {"auth": {"providers": ["github"]}}}) == ["github"]

    def test_multiple_providers(self):
        f = AuthFeature()
        result = f.manifest_to_config({"features": {"auth": {"providers": ["email", "github", "google"]}}})
        assert result == ["email/password", "github", "google"]

    def test_legacy_top_level(self):
        f = AuthFeature()
        assert f.manifest_to_config({"auth": {"providers": ["email", "github"]}}) == ["email/password", "github"]

    def test_features_takes_precedence(self):
        f = AuthFeature()
        manifest = {
            "auth": {"providers": ["email"]},
            "features": {"auth": {"providers": ["email", "github"]}},
        }
        assert f.manifest_to_config(manifest) == ["email/password", "github"]

    def test_no_auth(self):
        f = AuthFeature()
        assert f.manifest_to_config({"project": {"name": "test"}}) == []

    def test_empty_providers(self):
        f = AuthFeature()
        assert f.manifest_to_config({"features": {"auth": {"providers": []}}}) == []


class TestDeployedKeys:
    def test_always_empty(self):
        assert AuthFeature().deployed_keys({"features": {"auth": {"providers": ["email"]}}}) == set()


class TestConfigHtml:
    def test_contains_provider_checkboxes(self):
        html = AuthFeature().config_html(ctx())
        assert 'id="auth-email"' in html
        assert 'id="auth-github"' in html
        assert 'id="auth-google"' in html
        assert 'id="auth-apple"' in html

    def test_wrapped_in_fieldset(self):
        html = AuthFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")


class TestMeta:
    def test_depends_on_backend(self):
        assert "backend" in AuthFeature().meta().dependencies

    def test_no_group(self):
        assert AuthFeature().meta().group is None
