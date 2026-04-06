"""Tests for webinator versioning."""

import re
from webinator import __version__
from webinator.cli import _build_parser


def test_version_is_semver():
    assert re.match(r"^\d+\.\d+\.\d+$", __version__)


def test_parser_version_includes_package_version():
    parser = _build_parser()
    for action in parser._actions:
        if isinstance(action, type(parser._actions[0])) and "--version" in getattr(action, "option_strings", []):
            assert __version__ in action.version
            break
