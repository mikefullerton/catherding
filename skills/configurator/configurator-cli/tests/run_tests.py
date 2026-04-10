#!/usr/bin/env python3
"""Run configurator tests with proper fixture setup and cleanup."""

import subprocess
import sys
from pathlib import Path

SITES_DIR = Path.home() / ".local-server" / "sites"
SITE_FILE = SITES_DIR / "configurator.html"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    # Setup: publish test fixture
    SITES_DIR.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from configurator.web import build_page

    cfg = {"repo": "test-fixture", "domain": "test.com"}
    html = build_page(cfg, deployed_keys=set(), api_base="http://localhost:4040")
    SITE_FILE.write_text(html, encoding="utf-8")
    print(f"Setup: published {SITE_FILE}", file=sys.stderr)

    try:
        # Run tests
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-x", "-q"],
            cwd=PROJECT_ROOT,
        )
    finally:
        # Cleanup: always remove fixture
        if SITE_FILE.exists():
            SITE_FILE.unlink()
            print(f"Cleanup: removed {SITE_FILE}", file=sys.stderr)

        # Verify: fail loudly if cleanup didn't work
        if SITE_FILE.exists():
            print(f"ERROR: {SITE_FILE} still exists after cleanup!", file=sys.stderr)
            sys.exit(1)
        print("Verify: no test pages left behind", file=sys.stderr)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
