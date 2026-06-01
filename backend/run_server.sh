#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
PYTHON_BIN="../.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="python"
fi

if ss -ltn | grep -q ":${PORT} "; then
  echo "TurboTurn ya esta corriendo en http://127.0.0.1:${PORT}"
  echo "No abras otro servidor. Usa esa URL o deten el proceso actual con Ctrl+C."
  exit 0
fi

echo "Iniciando TurboTurn en http://127.0.0.1:${PORT}"
exec "$PYTHON_BIN" -m uvicorn main:app --host "$HOST" --port "$PORT"
