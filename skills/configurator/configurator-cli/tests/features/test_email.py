"""Tests for EmailFeature."""

from configurator.features.email import EmailFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert EmailFeature().meta().id == "email"

    def test_depends_on_backend(self):
        assert "backend" in EmailFeature().meta().dependencies

    def test_order(self):
        assert EmailFeature().meta().order == 50

    def test_no_group(self):
        assert EmailFeature().meta().group is None


class TestManifestToConfig:
    def test_enabled_with_provider(self):
        f = EmailFeature()
        manifest = {"features": {"email": {
            "enabled": True, "provider": "resend",
            "from_address": "hi@example.com", "from_name": "My App",
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {
            "enabled": True,
            "provider": "resend",
            "from_address": "hi@example.com",
            "from_name": "My App",
        }

    def test_enabled_minimal(self):
        f = EmailFeature()
        manifest = {"features": {"email": {"enabled": True}}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {"enabled": True}

    def test_disabled(self):
        f = EmailFeature()
        manifest = {"features": {"email": {"enabled": False}}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {"enabled": False}

    def test_missing(self):
        f = EmailFeature()
        assert f.manifest_to_config({}) == {"enabled": False}

    def test_no_features_section(self):
        f = EmailFeature()
        assert f.manifest_to_config({"project": {}}) == {"enabled": False}


class TestDeployedKeys:
    def test_email_deployed(self):
        f = EmailFeature()
        manifest = {"features": {"email": {"enabled": True}}}
        assert "email" in f.deployed_keys(manifest)

    def test_email_not_deployed(self):
        f = EmailFeature()
        assert f.deployed_keys({}) == set()

    def test_email_disabled_not_deployed(self):
        f = EmailFeature()
        manifest = {"features": {"email": {"enabled": False}}}
        assert f.deployed_keys(manifest) == set()


class TestConfigHtml:
    def test_contains_enabled_checkbox(self):
        html = EmailFeature().config_html(ctx())
        assert 'id="email-enabled"' in html

    def test_contains_provider_select(self):
        html = EmailFeature().config_html(ctx())
        assert 'id="email-provider"' in html

    def test_contains_from_address(self):
        html = EmailFeature().config_html(ctx())
        assert 'id="email-from-address"' in html

    def test_contains_from_name(self):
        html = EmailFeature().config_html(ctx())
        assert 'id="email-from-name"' in html

    def test_contains_provider_options(self):
        html = EmailFeature().config_html(ctx())
        assert 'value="resend"' in html
        assert 'value="sendgrid"' in html
        assert 'value="ses"' in html
        assert 'value="smtp"' in html

    def test_wrapped_in_fieldset(self):
        html = EmailFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_disabled_by_default(self):
        assert EmailFeature().default_config() == {"enabled": False}
