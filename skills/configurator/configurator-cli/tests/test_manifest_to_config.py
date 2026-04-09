"""Tests for _manifest_to_config — populating a draft config from a site manifest."""

from copy import deepcopy

import pytest

from configurator.cli import _deployed_keys_from_manifest, _manifest_to_config


# ── Full project (real-world manifest from agenticdeveloperhub) ──────────


FULL_PROJECT_MANIFEST = {
    "version": "1.0.0",
    "_site_manager_version": "1.18.0",
    "project": {
        "name": "agenticdeveloperhub",
        "displayName": "Agenticdeveloperhub",
        "domain": "agenticdeveloperhub.com",
        "type": "full",
        "created": "2026-04-09T15:27:54.556096+00:00",
    },
    "services": {
        "backend": {
            "status": "deployed",
            "platform": "railway",
            "url": "https://backend-production-5770.up.railway.app",
            "database": "postgresql",
        },
        "main": {
            "status": "deployed",
            "platform": "cloudflare",
            "domain": "agenticdeveloperhub.com",
            "workerName": "agenticdeveloperhub-main",
        },
        "admin": {
            "status": "deployed",
            "platform": "cloudflare",
            "domain": "admin.agenticdeveloperhub.com",
        },
        "dashboard": {
            "status": "deployed",
            "platform": "cloudflare",
            "domain": "dashboard.agenticdeveloperhub.com",
            "d1Database": "agenticdeveloperhub-dashboard-db",
        },
    },
    "features": {
        "auth": {
            "enabled": True,
            "mode": "built-in",
            "providers": ["email", "github"],
            "adminSeeded": True,
        },
    },
}


@pytest.fixture
def full_manifest():
    return deepcopy(FULL_PROJECT_MANIFEST)


class TestFullProject:
    def test_project_fields(self, full_manifest):
        cfg = _manifest_to_config(full_manifest)
        assert cfg["repo"] == "agenticdeveloperhub"
        assert cfg["domain"] == "agenticdeveloperhub.com"

    def test_website_from_main_service(self, full_manifest):
        cfg = _manifest_to_config(full_manifest)
        assert cfg["website"]["type"] == "existing"
        assert cfg["website"]["domain"] == "agenticdeveloperhub.com"

    def test_backend_enabled(self, full_manifest):
        cfg = _manifest_to_config(full_manifest)
        assert cfg["backend"]["enabled"] is True
        assert cfg["backend"]["type"] == "full"

    def test_admin_enabled(self, full_manifest):
        cfg = _manifest_to_config(full_manifest)
        assert cfg["admin_sites"]["admin"]["enabled"] is True
        assert cfg["admin_sites"]["admin"]["domain"] == "admin.agenticdeveloperhub.com"

    def test_dashboard_enabled(self, full_manifest):
        cfg = _manifest_to_config(full_manifest)
        assert cfg["admin_sites"]["dashboard"]["enabled"] is True
        assert cfg["admin_sites"]["dashboard"]["domain"] == "dashboard.agenticdeveloperhub.com"

    def test_auth_providers_mapped(self, full_manifest):
        cfg = _manifest_to_config(full_manifest)
        assert cfg["auth_providers"] == ["email/password", "github"]

    def test_does_not_mutate_input(self, full_manifest):
        original = deepcopy(full_manifest)
        _manifest_to_config(full_manifest)
        assert full_manifest == original


# ── Auth provider mapping ────────────────────────────────────────────────


class TestAuthProviders:
    def test_email_maps_to_email_password(self):
        manifest = {"features": {"auth": {"providers": ["email"]}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["auth_providers"] == ["email/password"]

    def test_email_password_passes_through(self):
        """Manifest may already store 'email/password' — should not double-map."""
        manifest = {"features": {"auth": {"providers": ["email/password"]}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["auth_providers"] == ["email/password"]

    def test_github_passes_through(self):
        manifest = {"features": {"auth": {"providers": ["github"]}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["auth_providers"] == ["github"]

    def test_google_passes_through(self):
        manifest = {"features": {"auth": {"providers": ["google"]}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["auth_providers"] == ["google"]

    def test_apple_passes_through(self):
        manifest = {"features": {"auth": {"providers": ["apple"]}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["auth_providers"] == ["apple"]

    def test_multiple_providers(self):
        manifest = {"features": {"auth": {"providers": ["email", "github", "google"]}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["auth_providers"] == ["email/password", "github", "google"]

    def test_legacy_top_level_auth(self):
        """Older manifests may have auth at top level instead of features.auth."""
        manifest = {"auth": {"providers": ["email", "github"]}}
        cfg = _manifest_to_config(manifest)
        assert cfg["auth_providers"] == ["email/password", "github"]

    def test_features_auth_takes_precedence_over_top_level(self):
        manifest = {
            "auth": {"providers": ["email"]},
            "features": {"auth": {"providers": ["email", "github"]}},
        }
        cfg = _manifest_to_config(manifest)
        assert cfg["auth_providers"] == ["email/password", "github"]

    def test_no_auth_section(self):
        manifest = {"project": {"name": "test"}}
        cfg = _manifest_to_config(manifest)
        assert "auth_providers" not in cfg

    def test_auth_without_providers(self):
        manifest = {"features": {"auth": {"enabled": True}}}
        cfg = _manifest_to_config(manifest)
        assert "auth_providers" not in cfg

    def test_empty_providers_list(self):
        manifest = {"features": {"auth": {"providers": []}}}
        cfg = _manifest_to_config(manifest)
        assert "auth_providers" not in cfg


# ── Backend detection ────────────────────────────────────────────────────


class TestBackend:
    def test_backend_service_enables_backend(self):
        manifest = {"services": {"backend": {"status": "deployed"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["backend"]["enabled"] is True
        assert cfg["backend"]["type"] == "full"

    def test_api_service_enables_backend(self):
        """Older manifests with 'api' service key should enable backend."""
        manifest = {"services": {"api": {"status": "deployed", "domain": "api.example.com"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["backend"]["enabled"] is True
        assert cfg["backend"]["domain"] == "api.example.com"

    def test_api_docs_only_enables_backend(self):
        manifest = {"services": {"api-docs": {"domain": "api.example.com"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["backend"]["enabled"] is True
        assert cfg["backend"]["docs_domain"] == "api.example.com"
        assert "domain" not in cfg["backend"]

    def test_backend_with_api_docs(self):
        manifest = {
            "services": {
                "backend": {"status": "deployed", "domain": "backend.example.com"},
                "api-docs": {"domain": "api.example.com"},
            },
        }
        cfg = _manifest_to_config(manifest)
        assert cfg["backend"]["enabled"] is True
        assert cfg["backend"]["domain"] == "backend.example.com"
        assert cfg["backend"]["docs_domain"] == "api.example.com"

    def test_no_backend(self):
        manifest = {"services": {"main": {"status": "deployed"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["backend"]["enabled"] is False

    def test_empty_services(self):
        manifest = {"services": {}}
        cfg = _manifest_to_config(manifest)
        assert cfg["backend"]["enabled"] is False

    def test_backend_without_domain(self):
        manifest = {"services": {"backend": {"status": "deployed", "platform": "railway"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["backend"]["enabled"] is True
        assert "domain" not in cfg["backend"]


# ── Website (main service) ───────────────────────────────────────────────


class TestWebsite:
    def test_main_service_creates_existing_website(self):
        manifest = {"services": {"main": {"domain": "example.com"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["website"]["type"] == "existing"
        assert cfg["website"]["domain"] == "example.com"

    def test_no_main_service_creates_none_website(self):
        manifest = {"services": {"backend": {"status": "deployed"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["website"]["type"] == "none"

    def test_d1_addon_detected(self):
        manifest = {"services": {"main": {"d1": True}}}
        cfg = _manifest_to_config(manifest)
        assert "sqlite database" in cfg["website"]["addons"]

    def test_database_field_detected_as_d1(self):
        """Dashboard-style 'database' field should also trigger sqlite addon."""
        manifest = {"services": {"main": {"database": "some-db"}}}
        cfg = _manifest_to_config(manifest)
        assert "sqlite database" in cfg["website"]["addons"]

    def test_kv_addon_detected(self):
        manifest = {"services": {"main": {"kv": True}}}
        cfg = _manifest_to_config(manifest)
        assert "key-value storage" in cfg["website"]["addons"]

    def test_r2_addon_detected(self):
        manifest = {"services": {"main": {"r2": True}}}
        cfg = _manifest_to_config(manifest)
        assert "file storage" in cfg["website"]["addons"]

    def test_multiple_addons(self):
        manifest = {"services": {"main": {"d1": True, "kv": True, "r2": True}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["website"]["addons"] == ["sqlite database", "key-value storage", "file storage"]

    def test_no_addons_omits_key(self):
        manifest = {"services": {"main": {"domain": "example.com"}}}
        cfg = _manifest_to_config(manifest)
        assert "addons" not in cfg["website"]

    def test_main_without_domain(self):
        manifest = {"services": {"main": {"status": "deployed"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["website"]["type"] == "existing"
        assert "domain" not in cfg["website"]


# ── Admin sites ──────────────────────────────────────────────────────────


class TestAdminSites:
    def test_admin_enabled_with_domain(self):
        manifest = {"services": {"admin": {"domain": "admin.example.com"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["admin_sites"]["admin"]["enabled"] is True
        assert cfg["admin_sites"]["admin"]["domain"] == "admin.example.com"

    def test_dashboard_enabled_with_domain(self):
        manifest = {"services": {"dashboard": {"domain": "dashboard.example.com"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["admin_sites"]["dashboard"]["enabled"] is True
        assert cfg["admin_sites"]["dashboard"]["domain"] == "dashboard.example.com"

    def test_no_admin_sites(self):
        manifest = {"services": {}}
        cfg = _manifest_to_config(manifest)
        assert cfg["admin_sites"]["admin"]["enabled"] is False
        assert cfg["admin_sites"]["dashboard"]["enabled"] is False

    def test_admin_without_dashboard(self):
        manifest = {"services": {"admin": {"domain": "admin.example.com"}}}
        cfg = _manifest_to_config(manifest)
        assert cfg["admin_sites"]["admin"]["enabled"] is True
        assert cfg["admin_sites"]["dashboard"]["enabled"] is False


# ── Project fields ───────────────────────────────────────────────────────


class TestProjectFields:
    def test_name_maps_to_repo(self):
        manifest = {"project": {"name": "my-project"}}
        cfg = _manifest_to_config(manifest)
        assert cfg["repo"] == "my-project"

    def test_org_mapped(self):
        manifest = {"project": {"org": "my-org"}}
        cfg = _manifest_to_config(manifest)
        assert cfg["org"] == "my-org"

    def test_domain_mapped(self):
        manifest = {"project": {"domain": "example.com"}}
        cfg = _manifest_to_config(manifest)
        assert cfg["domain"] == "example.com"

    def test_missing_project_section(self):
        cfg = _manifest_to_config({})
        assert "repo" not in cfg
        assert "org" not in cfg
        assert "domain" not in cfg

    def test_empty_manifest(self):
        cfg = _manifest_to_config({})
        assert cfg["website"] == {"type": "none"}
        assert cfg["backend"]["enabled"] is False
        assert cfg["admin_sites"]["admin"]["enabled"] is False
        assert cfg["admin_sites"]["dashboard"]["enabled"] is False

    def test_backend_only_project(self):
        """Backend-only deployment — no main, no admin, no dashboard."""
        manifest = {
            "project": {"name": "api-service", "domain": "api.example.com"},
            "services": {"backend": {"status": "deployed", "domain": "backend.api.example.com"}},
        }
        cfg = _manifest_to_config(manifest)
        assert cfg["repo"] == "api-service"
        assert cfg["website"]["type"] == "none"
        assert cfg["backend"]["enabled"] is True
        assert cfg["backend"]["domain"] == "backend.api.example.com"
        assert cfg["admin_sites"]["admin"]["enabled"] is False
        assert cfg["admin_sites"]["dashboard"]["enabled"] is False


# ── Deployed keys ───────────────────────────────────────────────────────


class TestDeployedKeys:
    def test_backend_deployed(self):
        manifest = {"services": {"backend": {"status": "deployed"}}}
        assert "backend" in _deployed_keys_from_manifest(manifest)

    def test_admin_deployed(self):
        manifest = {"services": {"admin": {"status": "deployed"}}}
        assert "admin" in _deployed_keys_from_manifest(manifest)

    def test_dashboard_deployed(self):
        manifest = {"services": {"dashboard": {"domain": "dash.example.com"}}}
        assert "dashboard" in _deployed_keys_from_manifest(manifest)

    def test_main_deployed(self):
        manifest = {"services": {"main": {"domain": "example.com"}}}
        assert "website" in _deployed_keys_from_manifest(manifest)

    def test_nothing_deployed(self):
        manifest = {"services": {}}
        assert _deployed_keys_from_manifest(manifest) == set()

    def test_empty_manifest(self):
        assert _deployed_keys_from_manifest({}) == set()

    def test_api_counts_as_backend(self):
        manifest = {"services": {"api": {"status": "deployed"}}}
        assert "backend" in _deployed_keys_from_manifest(manifest)
