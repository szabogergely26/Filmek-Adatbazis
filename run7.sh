#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/7.0-modulok"
VENV_PY="$SCRIPT_DIR/venv/bin/python"

cd "$APP_DIR"

exec "$VENV_PY" ./movies7.0.py
