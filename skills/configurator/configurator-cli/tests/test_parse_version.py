"""Tests for _parse_version — semver string to comparable tuple."""

import pytest

from configurator.cli import _parse_version


class TestParseVersion:
    def test_three_part(self):
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_zeros(self):
        assert _parse_version("0.0.0") == (0, 0, 0)

    def test_large_numbers(self):
        assert _parse_version("12.345.6789") == (12, 345, 6789)

    def test_comparison_major(self):
        assert _parse_version("2.0.0") > _parse_version("1.9.9")

    def test_comparison_minor(self):
        assert _parse_version("0.3.0") > _parse_version("0.2.9")

    def test_comparison_patch(self):
        assert _parse_version("0.3.1") > _parse_version("0.3.0")

    def test_equality(self):
        assert _parse_version("1.0.0") == _parse_version("1.0.0")

    def test_two_part(self):
        """Two-part versions should still produce a comparable tuple."""
        assert _parse_version("1.0") == (1, 0)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            _parse_version("not.a.version")
