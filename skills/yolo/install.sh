#!/usr/bin/env bash
# Thin wrapper around install-yolo.py.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/install-yolo.py" --skill-dir "$HERE" "$@"
