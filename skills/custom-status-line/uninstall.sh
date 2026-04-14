#!/usr/bin/env bash
# Thin wrapper around uninstall-statusline.py.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/uninstall-statusline.py" "$@"
