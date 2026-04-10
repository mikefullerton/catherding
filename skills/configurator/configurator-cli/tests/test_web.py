"""Tests for the web editor module."""

import json
import threading
import urllib.request

from configurator.web import build_page, start_server


class TestBuildPage:
    def test_embeds_config_as_json(self):
        cfg = {"repo": "my-project", "domain": "example.com"}
        html = build_page(cfg, deployed_keys=set())
        assert "my-project" in html
        assert "example.com" in html

    def test_embeds_deployed_keys(self):
        cfg = {"repo": "test", "backend": {"enabled": True}}
        html = build_page(cfg, deployed_keys={"backend"})
        assert '"backend"' in html

    def test_returns_valid_html(self):
        html = build_page({}, deployed_keys=set())
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_config_is_parseable_json_in_script(self):
        cfg = {"repo": "test", "domain": "test.com", "website": {"type": "existing"}}
        html = build_page(cfg, deployed_keys=set())
        # Extract the JSON from the script tag
        start = html.index("const CONFIG = ") + len("const CONFIG = ")
        end = html.index(";", start)
        parsed = json.loads(html[start:end])
        assert parsed["repo"] == "test"

    def test_embeds_urls(self):
        cfg = {"repo": "test"}
        urls = {"main": "https://example.com", "backend": "https://api.example.com"}
        html = build_page(cfg, deployed_keys=set(), urls=urls)
        assert "https://example.com" in html
        assert "https://api.example.com" in html

    def test_embeds_live_domains(self):
        cfg = {"repo": "test"}
        html = build_page(cfg, deployed_keys=set(), live_domains={"main", "backend"})
        assert '"backend"' in html
        assert '"main"' in html


class TestServer:
    def test_patch_updates_config(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        cfg = {"repo": "test-project"}
        httpd, port = start_server("test-project", cfg, deployed_keys=set(), port=0)

        def handle_two():
            httpd.handle_request()
            httpd.handle_request()

        t = threading.Thread(target=handle_two)
        t.start()
        try:
            data = json.dumps({"repo": "updated", "domain": "new.com"}).encode()
            req = urllib.request.Request(
                f"http://localhost:{port}/api/config",
                data=data,
                method="PATCH",
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req)
            assert resp.status == 200

            # Verify the file was written
            saved = json.loads((tmp_path / "test-project.json").read_text())
            assert saved["repo"] == "updated"
            assert saved["domain"] == "new.com"
        finally:
            httpd.server_close()
            t.join(timeout=2)

    def test_deploy_sets_action(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        cfg = {"repo": "test-project"}
        httpd, port = start_server("test-project", cfg, deployed_keys=set(), port=0)
        assert httpd.action == "cancel"  # default
        t = threading.Thread(target=httpd.handle_request)
        t.start()
        try:
            req = urllib.request.Request(
                f"http://localhost:{port}/api/deploy",
                data=b"",
                method="POST",
            )
            resp = urllib.request.urlopen(req)
            assert resp.status == 200
            assert httpd.action == "deploy"
        finally:
            httpd.server_close()
            t.join(timeout=2)

    def test_cancel_sets_action(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CONFIG_DIR", tmp_path)
        cfg = {"repo": "test-project"}
        httpd, port = start_server("test-project", cfg, deployed_keys=set(), port=0)
        t = threading.Thread(target=httpd.handle_request)
        t.start()
        try:
            req = urllib.request.Request(
                f"http://localhost:{port}/api/cancel",
                data=b"",
                method="POST",
            )
            resp = urllib.request.urlopen(req)
            assert resp.status == 200
            assert httpd.action == "cancel"
        finally:
            httpd.server_close()
            t.join(timeout=2)
