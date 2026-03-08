#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# ARS Drift Auditor — systemd user timer installer
#
# Installs a daily systemd timer that runs the ARS drift auditor at 06:00 UTC.
# Separate from the Obsidian tracking timer (quantum-swarm-tracking).
#
# Usage:
#   scripts/install_ars_timer.sh [--install|--uninstall|--status]
# ---------------------------------------------------------------------------

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="quantum-swarm-ars-auditor"
UNIT_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${UNIT_DIR}/${SERVICE_NAME}.service"
TIMER_FILE="${UNIT_DIR}/${SERVICE_NAME}.timer"
ENV_FILE="${UNIT_DIR}/${SERVICE_NAME}.env"

CALENDAR_EXPR="${CALENDAR_EXPR:-*-*-* 06:00:00}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_DIR}/.venv/bin/python3.12}"

usage() {
  cat <<EOF
Install/update a user-level systemd timer for the ARS Drift Auditor.

Usage:
  scripts/install_ars_timer.sh [--install|--uninstall|--status]

Environment overrides:
  CALENDAR_EXPR  (default: *-*-* 06:00:00  — daily at 06:00 UTC)
  PYTHON_BIN     (default: \${REPO_DIR}/.venv/bin/python3.12)
  DATABASE_URL   (required at runtime for DB queries)
EOF
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

preflight_check() {
  if [[ ! -f "${REPO_DIR}/src/core/ars_auditor.py" ]]; then
    echo "Missing ARS auditor module: ${REPO_DIR}/src/core/ars_auditor.py" >&2
    exit 1
  fi
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python binary not found or not executable: $PYTHON_BIN" >&2
    exit 1
  fi
}

install_units() {
  require_cmd systemctl
  preflight_check
  mkdir -p "$UNIT_DIR"

  # Write environment file (DATABASE_URL loaded from user environment)
  cat >"$ENV_FILE" <<EOF
# ARS auditor environment — add DATABASE_URL here if not in user env
# DATABASE_URL=postgresql://user:pass@localhost:5432/quantum_swarm
EOF

  cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=ARS Drift Auditor for quantum-swarm

[Service]
Type=oneshot
WorkingDirectory=${REPO_DIR}
EnvironmentFile=-${ENV_FILE}
ExecStart=${PYTHON_BIN} -m src.core.ars_auditor
StandardOutput=journal
StandardError=journal
EOF

  cat >"$TIMER_FILE" <<EOF
[Unit]
Description=Run ARS Drift Auditor daily (quantum-swarm)

[Timer]
OnCalendar=${CALENDAR_EXPR}
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl --user daemon-reload
  systemctl --user enable --now "${SERVICE_NAME}.timer"
  echo "Installed and enabled ${SERVICE_NAME}.timer (schedule: ${CALENDAR_EXPR})"
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
