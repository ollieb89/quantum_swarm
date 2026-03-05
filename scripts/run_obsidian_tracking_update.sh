#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_SLUG="${PROJECT_SLUG:-${1:-quantum-swarm}}"
EVENT="${EVENT_NAME:-${2:-progress}}"
INPUT_PATH="${INPUT_FILE:-${3:-$REPO_DIR/data/tracking_update.json}}"
VAULT_ROOT="${VAULT_ROOT:-${4:-$REPO_DIR/quantum-swarm}}"

if [[ -n "${PYTHON_BIN:-}" ]]; then
  PYTHON_EXEC="$PYTHON_BIN"
elif [[ -x "$REPO_DIR/.venv/bin/python3" ]]; then
  PYTHON_EXEC="$REPO_DIR/.venv/bin/python3"
else
  PYTHON_EXEC="$(command -v python3 || true)"
fi

if [[ -z "${PYTHON_EXEC:-}" ]]; then
  echo "python3 not found. Set PYTHON_BIN or install python3." >&2
  exit 1
fi

exec "$PYTHON_EXEC" "$REPO_DIR/scripts/update_project_tracking.py" \
  --project "$PROJECT_SLUG" \
  --event "$EVENT" \
  --input "$INPUT_PATH" \
  --vault-root "$VAULT_ROOT"
