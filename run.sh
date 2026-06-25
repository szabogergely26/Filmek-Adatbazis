#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/app"
VENV_PY="$SCRIPT_DIR/venv/bin/python"

cd "$APP_DIR"

exec "$VENV_PY" ./main.py
