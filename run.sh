#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/app"
VENV_PY="$SCRIPT_DIR/venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
    echo "Hiba: nem található a venv Python: $VENV_PY"
    exit 1
fi

cd "$APP_DIR"
exec "$VENV_PY" ./main.py
