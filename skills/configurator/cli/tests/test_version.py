"""Tests for site-manager versioning."""

import re
from site_manager import __version__
from site_manager.cli import _build_parser


def test_version_is_semver():
    assert re.match(r"^\d+\.\d+\.\d+$", __version__)


def test_parser_version_includes_package_version():
    parser = _build_parser()
    # The version action stores the version string
    for action in parser._actions:
        if isinstance(action, type(parser._actions[0])) and "--version" in getattr(action, "option_strings", []):
            assert __version__ in action.version
            break
