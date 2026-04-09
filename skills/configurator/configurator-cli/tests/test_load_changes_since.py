"""Tests for _load_changes_since — parsing CHANGES.md with version filtering."""

from pathlib import Path
from textwrap import dedent

from configurator.cli import _load_changes_since


SAMPLE_CHANGES = dedent("""\
    # Change History

    ## 0.3.0

    - **Feature A**: Description of feature A.
    - **Feature B**: Description of feature B.

    ## 0.2.0

    - **Feature C**: Description of feature C.

    ## 0.1.0

    - Initial release.
""")


class TestLoadChangesSince:
    def test_all_versions_when_none(self, monkeypatch, tmp_path):
        changes_file = tmp_path / "CHANGES.md"
        changes_file.write_text(SAMPLE_CHANGES)
        monkeypatch.setattr("configurator.cli.CHANGES_PATH", changes_file)

        result = _load_changes_since(None)
        assert "0.3.0" in result
        assert "0.2.0" in result
        assert "0.1.0" in result

    def test_since_0_1_0(self, monkeypatch, tmp_path):
        changes_file = tmp_path / "CHANGES.md"
        changes_file.write_text(SAMPLE_CHANGES)
        monkeypatch.setattr("configurator.cli.CHANGES_PATH", changes_file)

        result = _load_changes_since("0.1.0")
        assert "0.3.0" in result
        assert "0.2.0" in result
        assert "0.1.0" not in result

    def test_since_0_2_0(self, monkeypatch, tmp_path):
        changes_file = tmp_path / "CHANGES.md"
        changes_file.write_text(SAMPLE_CHANGES)
        monkeypatch.setattr("configurator.cli.CHANGES_PATH", changes_file)

        result = _load_changes_since("0.2.0")
        assert "0.3.0" in result
        assert "0.2.0" not in result

    def test_since_latest_returns_empty(self, monkeypatch, tmp_path):
        changes_file = tmp_path / "CHANGES.md"
        changes_file.write_text(SAMPLE_CHANGES)
        monkeypatch.setattr("configurator.cli.CHANGES_PATH", changes_file)

        result = _load_changes_since("0.3.0")
        assert result == {}

    def test_items_are_bullet_lines(self, monkeypatch, tmp_path):
        changes_file = tmp_path / "CHANGES.md"
        changes_file.write_text(SAMPLE_CHANGES)
        monkeypatch.setattr("configurator.cli.CHANGES_PATH", changes_file)

        result = _load_changes_since("0.2.0")
        items = result["0.3.0"]
        assert len(items) == 2
        assert all(item.startswith("- ") for item in items)

    def test_missing_file_returns_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr("configurator.cli.CHANGES_PATH", tmp_path / "nope.md")
        assert _load_changes_since(None) == {}

    def test_non_bullet_lines_excluded(self, monkeypatch, tmp_path):
        changes_file = tmp_path / "CHANGES.md"
        changes_file.write_text(dedent("""\
            ## 1.0.0

            Some paragraph text that is not a bullet.

            - **Actual item**: This should be included.

            Another paragraph.
        """))
        monkeypatch.setattr("configurator.cli.CHANGES_PATH", changes_file)

        result = _load_changes_since(None)
        assert len(result["1.0.0"]) == 1

    def test_empty_file_returns_empty(self, monkeypatch, tmp_path):
        changes_file = tmp_path / "CHANGES.md"
        changes_file.write_text("")
        monkeypatch.setattr("configurator.cli.CHANGES_PATH", changes_file)

        assert _load_changes_since(None) == {}
