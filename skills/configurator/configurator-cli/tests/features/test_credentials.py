"""Tests for CredentialsFeature."""

from configurator.features.credentials import CredentialsFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert CredentialsFeature().meta().id == "credentials"

    def test_depends_on_project(self):
        assert "project" in CredentialsFeature().meta().dependencies

    def test_order(self):
        assert CredentialsFeature().meta().order == 80

    def test_no_group(self):
        assert CredentialsFeature().meta().group is None


class TestManifestToConfig:
    def test_list_of_keys(self):
        f = CredentialsFeature()
        manifest = {"features": {"credentials": ["cloudflare_api_token", "railway_token"]}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == ["cloudflare_api_token", "railway_token"]

    def test_dict_with_keys_field(self):
        f = CredentialsFeature()
        manifest = {"features": {"credentials": {"keys": ["github_token"]}}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == ["github_token"]

    def test_missing(self):
        assert CredentialsFeature().manifest_to_config({}) == []

    def test_empty_list(self):
        f = CredentialsFeature()
        manifest = {"features": {"credentials": []}}
        assert f.manifest_to_config(manifest) == []


class TestDeployedKeys:
    def test_always_empty(self):
        f = CredentialsFeature()
        manifest = {"features": {"credentials": ["cloudflare_api_token"]}}
        assert f.deployed_keys(manifest) == set()

    def test_empty_manifest(self):
        assert CredentialsFeature().deployed_keys({}) == set()


class TestConfigHtml:
    def test_contains_cloudflare_api_token(self):
        html = CredentialsFeature().config_html(ctx())
        assert 'id="cred-cloudflare_api_token"' in html

    def test_contains_railway_token(self):
        html = CredentialsFeature().config_html(ctx())
        assert 'id="cred-railway_token"' in html

    def test_contains_github_token(self):
        html = CredentialsFeature().config_html(ctx())
        assert 'id="cred-github_token"' in html

    def test_contains_database_url(self):
        html = CredentialsFeature().config_html(ctx())
        assert 'id="cred-database_url"' in html

    def test_wrapped_in_fieldset(self):
        html = CredentialsFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_empty_by_default(self):
        assert CredentialsFeature().default_config() == []
