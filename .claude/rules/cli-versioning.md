# CLI Versioning

When modifying any Python source file under `cli/site-manager/src/` or `cli/webinator/src/`, bump the patch version in that CLI's `__init__.py` before committing.

The version is the single `__version__` string in:
- `cli/site-manager/src/site_manager/__init__.py`
- `cli/webinator/src/webinator/__init__.py`

This is the sole source of truth — `pyproject.toml` and `cli.py` read from it dynamically.

Use semver: bump **patch** for fixes and small changes, **minor** for new commands or features, **major** for breaking changes.
