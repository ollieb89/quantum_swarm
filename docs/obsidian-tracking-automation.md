# Obsidian Tracking Automation

Use a user-level `systemd` timer to run project tracking updates weekly without relying on `crontab`.

## Why systemd timer

- Avoids `crontab` access-control issues.
- Provides `journalctl` logs for each run.
- Supports `Persistent=true` so missed runs execute on next login after downtime.
- Works while logged out only when user lingering is enabled.

## Install

From the repo root:

```bash
chmod +x scripts/run_obsidian_tracking_update.sh scripts/install_obsidian_tracking_timer.sh
scripts/install_obsidian_tracking_timer.sh --install
```

## Verify

```bash
scripts/install_obsidian_tracking_timer.sh --status
systemctl --user list-timers quantum-swarm-tracking.timer --all
```

## Run while logged out (optional)

User-level timers normally depend on your user session.
Enable lingering if you want execution while logged out:

```bash
sudo loginctl enable-linger "$USER"
```

## Run once manually

```bash
systemctl --user start quantum-swarm-tracking.service
journalctl --user -u quantum-swarm-tracking.service --no-pager -n 100
```

## Custom schedule / inputs

Set environment overrides when running the installer:

```bash
CALENDAR_EXPR="Mon *-*-* 09:00:00" \
PROJECT_SLUG="quantum-swarm" \
INPUT_FILE="$PWD/data/tracking_update.json" \
VAULT_ROOT="$PWD/quantum-swarm" \
scripts/install_obsidian_tracking_timer.sh --install
```

## Remove

```bash
scripts/install_obsidian_tracking_timer.sh --uninstall
```
