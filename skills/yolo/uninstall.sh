#!/usr/bin/env bash
# Thin wrapper around uninstall-yolo.py.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/uninstall-yolo.py" "$@"
