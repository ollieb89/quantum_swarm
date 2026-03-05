#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="quantum-swarm-tracking"
UNIT_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${UNIT_DIR}/${SERVICE_NAME}.service"
TIMER_FILE="${UNIT_DIR}/${SERVICE_NAME}.timer"
ENV_FILE="${UNIT_DIR}/${SERVICE_NAME}.env"

PROJECT_SLUG="${PROJECT_SLUG:-quantum-swarm}"
EVENT_NAME="${EVENT_NAME:-progress}"
INPUT_FILE="${INPUT_FILE:-${REPO_DIR}/data/tracking_update.json}"
VAULT_ROOT="${VAULT_ROOT:-${REPO_DIR}/quantum-swarm}"
CALENDAR_EXPR="${CALENDAR_EXPR:-Mon *-*-* 09:00:00}"

usage() {
  cat <<EOF
Install/update a user-level systemd timer for Obsidian project tracking.

Usage:
  scripts/install_obsidian_tracking_timer.sh [--install|--uninstall|--status]

Environment overrides:
  PROJECT_SLUG   (default: quantum-swarm)
  EVENT_NAME     (default: progress)
  INPUT_FILE     (default: ${REPO_DIR}/data/tracking_update.json)
  VAULT_ROOT     (default: ${REPO_DIR}/quantum-swarm)
  CALENDAR_EXPR  (default: Mon *-*-* 09:00:00)
EOF
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

escape_for_env_file() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/ }"
  printf '"%s"' "$value"
}

preflight_check() {
  if [[ ! -f "${REPO_DIR}/scripts/update_project_tracking.py" ]]; then
    echo "Missing updater script: ${REPO_DIR}/scripts/update_project_tracking.py" >&2
    exit 1
  fi
  if [[ ! -f "${REPO_DIR}/scripts/run_obsidian_tracking_update.sh" ]]; then
    echo "Missing runner script: ${REPO_DIR}/scripts/run_obsidian_tracking_update.sh" >&2
    exit 1
  fi
  chmod +x "${REPO_DIR}/scripts/run_obsidian_tracking_update.sh"

  if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Input file not found: $INPUT_FILE" >&2
    exit 1
  fi
  if [[ ! -d "$VAULT_ROOT" ]]; then
    echo "Vault root directory not found: $VAULT_ROOT" >&2
    exit 1
  fi
}

install_units() {
  require_cmd systemctl
  preflight_check
  mkdir -p "$UNIT_DIR"

  local project_slug_escaped
  local event_name_escaped
  local input_file_escaped
  local vault_root_escaped
  local python_bin_escaped
  project_slug_escaped="$(escape_for_env_file "$PROJECT_SLUG")"
  event_name_escaped="$(escape_for_env_file "$EVENT_NAME")"
  input_file_escaped="$(escape_for_env_file "$INPUT_FILE")"
  vault_root_escaped="$(escape_for_env_file "$VAULT_ROOT")"
  python_bin_escaped="$(escape_for_env_file "${PYTHON_BIN:-}")"

  cat >"$ENV_FILE" <<EOF
PROJECT_SLUG=${project_slug_escaped}
EVENT_NAME=${event_name_escaped}
INPUT_FILE=${input_file_escaped}
VAULT_ROOT=${vault_root_escaped}
PYTHON_BIN=${python_bin_escaped}
EOF

  cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=Update Obsidian project tracking for ${PROJECT_SLUG}

[Service]
Type=oneshot
WorkingDirectory=${REPO_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${REPO_DIR}/scripts/run_obsidian_tracking_update.sh
EOF

  cat >"$TIMER_FILE" <<EOF
[Unit]
Description=Run Obsidian project tracking update (${PROJECT_SLUG})

[Timer]
OnCalendar=${CALENDAR_EXPR}
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl --user daemon-reload
  systemctl --user enable --now "${SERVICE_NAME}.timer"
  echo "Installed and enabled ${SERVICE_NAME}.timer"
  systemctl --user list-timers "${SERVICE_NAME}.timer" --all
}

uninstall_units() {
  require_cmd systemctl
  systemctl --user disable --now "${SERVICE_NAME}.timer" >/dev/null 2>&1 || true
  rm -f "$SERVICE_FILE" "$TIMER_FILE" "$ENV_FILE"
  systemctl --user daemon-reload
  echo "Removed ${SERVICE_NAME}.service, ${SERVICE_NAME}.timer, and ${SERVICE_NAME}.env"
}

show_status() {
  require_cmd systemctl
  systemctl --user status "${SERVICE_NAME}.timer" --no-pager || true
  systemctl --user list-timers "${SERVICE_NAME}.timer" --all || true
}

ACTION="${1:---install}"
case "$ACTION" in
  --install)
    install_units
    ;;
  --uninstall)
    uninstall_units
    ;;
  --status)
    show_status
    ;;
  -h|--help)
    usage
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    usage
    exit 1
    ;;
esac
