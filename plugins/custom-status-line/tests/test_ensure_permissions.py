import json
import pytest


class TestEnsurePermissions:
    def test_extracts_and_merges_bash_patterns(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            "---\n"
            "name: test\n"
            "allowed-tools: Read, Bash(chmod *), Bash(mkdir -p *)\n"
            "---\n"
            "# Test\n"
        )
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"permissions": {"allow": ["Read"]}}))

        from statusline.ensure_permissions import merge_permissions
        merge_permissions(str(skill_md), str(settings))

        result = json.loads(settings.read_text())
        allow = result["permissions"]["allow"]
        assert "Bash(chmod *)" in allow
        assert "Bash(mkdir -p *)" in allow
        assert "Read" in allow

    def test_deduplicates(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nallowed-tools: Bash(chmod *)\n---\n")
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"permissions": {"allow": ["Bash(chmod *)"]}}))

        from statusline.ensure_permissions import merge_permissions
        merge_permissions(str(skill_md), str(settings))

        result = json.loads(settings.read_text())
        assert result["permissions"]["allow"].count("Bash(chmod *)") == 1

    def test_missing_skill_file_is_noop(self, tmp_path):
        settings = tmp_path / "settings.json"
        settings.write_text(json.dumps({"permissions": {"allow": []}}))

        from statusline.ensure_permissions import merge_permissions
        merge_permissions("/nonexistent/SKILL.md", str(settings))

        result = json.loads(settings.read_text())
        assert result["permissions"]["allow"] == []

    def test_missing_settings_file_is_noop(self, tmp_path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nallowed-tools: Bash(chmod *)\n---\n")

        from statusline.ensure_permissions import merge_permissions
        merge_permissions(str(skill_md), "/nonexistent/settings.json")
