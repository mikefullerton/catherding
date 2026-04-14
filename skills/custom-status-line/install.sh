#!/usr/bin/env bash
# Thin wrapper around install-statusline.py — runs the skill's Python installer
# from the skill dir regardless of the caller's cwd.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$HERE/install-statusline.py" "$@"
