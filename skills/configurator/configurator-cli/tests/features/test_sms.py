"""Tests for SmsFeature."""

from configurator.features.sms import SmsFeature
from configurator.features.base import RenderContext


def ctx(**kwargs):
    defaults = dict(deployed_keys=set(), urls={}, live_domains={}, config={})
    defaults.update(kwargs)
    return RenderContext(**defaults)


class TestMeta:
    def test_id(self):
        assert SmsFeature().meta().id == "sms"

    def test_depends_on_backend(self):
        assert "backend" in SmsFeature().meta().dependencies

    def test_order(self):
        assert SmsFeature().meta().order == 51

    def test_no_group(self):
        assert SmsFeature().meta().group is None


class TestManifestToConfig:
    def test_enabled_with_provider(self):
        f = SmsFeature()
        manifest = {"features": {"sms": {
            "enabled": True, "provider": "twilio", "from_number": "+15551234567",
        }}}
        cfg = f.manifest_to_config(manifest)
        assert cfg == {"enabled": True, "provider": "twilio", "from_number": "+15551234567"}

    def test_enabled_minimal(self):
        f = SmsFeature()
        manifest = {"features": {"sms": {"enabled": True}}}
        assert f.manifest_to_config(manifest) == {"enabled": True}

    def test_disabled(self):
        f = SmsFeature()
        manifest = {"features": {"sms": {"enabled": False}}}
        assert f.manifest_to_config(manifest) == {"enabled": False}

    def test_missing(self):
        f = SmsFeature()
        assert f.manifest_to_config({}) == {"enabled": False}


class TestDeployedKeys:
    def test_sms_deployed(self):
        f = SmsFeature()
        manifest = {"features": {"sms": {"enabled": True}}}
        assert "sms" in f.deployed_keys(manifest)

    def test_sms_not_deployed(self):
        assert SmsFeature().deployed_keys({}) == set()

    def test_sms_disabled_not_deployed(self):
        f = SmsFeature()
        manifest = {"features": {"sms": {"enabled": False}}}
        assert f.deployed_keys(manifest) == set()


class TestConfigHtml:
    def test_contains_enabled_checkbox(self):
        html = SmsFeature().config_html(ctx())
        assert 'id="sms-enabled"' in html

    def test_contains_provider_select(self):
        html = SmsFeature().config_html(ctx())
        assert 'id="sms-provider"' in html

    def test_contains_from_number(self):
        html = SmsFeature().config_html(ctx())
        assert 'id="sms-from-number"' in html

    def test_contains_provider_options(self):
        html = SmsFeature().config_html(ctx())
        assert 'value="twilio"' in html
        assert 'value="vonage"' in html
        assert 'value="aws-sns"' in html

    def test_wrapped_in_fieldset(self):
        html = SmsFeature().config_html(ctx())
        assert html.strip().startswith("<fieldset>")
        assert html.strip().endswith("</fieldset>")


class TestDefaultConfig:
    def test_disabled_by_default(self):
        assert SmsFeature().default_config() == {"enabled": False}
