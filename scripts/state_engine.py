#!/usr/bin/env python3
"""Machine interface for .planning/ state files.

Reads and writes the YAML frontmatter in STATE.md and ROADMAP.md, then
regenerates the markdown body to keep human-readable content in sync.

This is the single programmatic entry point for all state mutations.
CI, orchestration agents, and CLI tools call this instead of editing
the markdown files directly.

Usage:
    # Query current state
    python scripts/state_engine.py query phase
    python scripts/state_engine.py query health
    python scripts/state_engine.py query roadmap

    # Transition phase status
    python scripts/state_engine.py transition --phase 2 --status in_progress
    python scripts/state_engine.py transition --phase 2 --status completed

    # Add/clear blockers and risks
    python scripts/state_engine.py blocker --add "Waiting for API keys"
    python scripts/state_engine.py blocker --clear 0
    python scripts/state_engine.py risk --add "Exchange rate volatility"
    python scripts/state_engine.py risk --clear 0

    # Set health status
    python scripts/state_engine.py health --status green
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


PLANNING_DIR = Path(".planning")
STATE_FILE = PLANNING_DIR / "STATE.md"
ROADMAP_FILE = PLANNING_DIR / "ROADMAP.md"

VALID_STATUSES = {"not_started", "in_progress", "blocked", "completed"}
VALID_HEALTH = {"green", "yellow", "red"}


# ---------------------------------------------------------------------------
# YAML frontmatter parsing
# ---------------------------------------------------------------------------

def parse_frontmatter(path: Path) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter and markdown body from a file."""
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if not match:
        return {}, content
    fm = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return fm, body


def write_state_file(path: Path, fm: Dict[str, Any], body: str) -> None:
    """Write YAML frontmatter + markdown body back to file."""
    fm["updated"] = dt.date.today().isoformat()
    yaml_str = yaml.dump(fm, default_flow_style=False, sort_keys=False, allow_unicode=True)
    content = f"---\n{yaml_str}---\n{body}"
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# STATE.md body regeneration
# ---------------------------------------------------------------------------

def render_state_body(fm: Dict[str, Any]) -> str:
    """Regenerate the markdown body of STATE.md from its YAML frontmatter."""
    phase = fm.get("phase", {})
    prev = fm.get("previous_phase", {})
    health = fm.get("health", {})
    arch = fm.get("architecture", {})
    paths = fm.get("paths", {})

    status_label = (phase.get("status", "unknown")).replace("_", " ").title()
    prev_label = f"Phase {prev.get('number', '?')} ({prev.get('name', '?')})"
    prev_completed = prev.get("completed", "?")
    health_status = (health.get("status", "unknown")).replace("_", " ").title()

    lines = [
        "",
        "# Project State",
        "",
        "> Machine-readable state lives in YAML frontmatter above.",
        "> This markdown body is auto-generated — do not edit manually.",
        "",
        "## Current Phase",
        "",
        f"**Phase {phase.get('current', '?')}** — {phase.get('name', '?')}",
        f"- Status: {status_label}",
    ]

    if phase.get("started"):
        lines.append(f"- Started: {phase['started']}")
    if phase.get("completed"):
        lines.append(f"- Completed: {phase['completed']}")

    lines.append(f"- Previous: {prev_label} — Completed {prev_completed}")

    # Blockers
    blockers = phase.get("blockers", [])
    if blockers:
        lines.extend(["", "### Blockers"])
        for i, b in enumerate(blockers):
            lines.append(f"- [{i}] {b}")

    # Health
    lines.extend(["", "## Health", "", f"Status: {health_status}"])

    risks = health.get("risks", [])
    if risks:
        lines.extend(["", "### Risks"])
        for i, r in enumerate(risks):
            lines.append(f"- [{i}] {r}")

    h_blockers = health.get("blockers", [])
    if h_blockers:
        lines.extend(["", "### Blockers"])
        for i, b in enumerate(h_blockers):
            lines.append(f"- [{i}] {b}")

    # Architecture
    runtime = arch.get("runtime", "?")
    pattern = arch.get("pattern", "?").replace("_", " ").title()
    layers = arch.get("layers", {})
    layer_str = " > ".join(
        v.replace("_", " ").title() for v in layers.values()
    ) if layers else "?"
    comm = arch.get("communication", "?").replace("_", " ").title()
    dash = arch.get("dashboard", "?").replace("_", " ").title()

    lines.extend([
        "",
        "## Architecture",
        "",
        f"- Runtime: {runtime.replace('_', ' ').title()}",
        f"- Pattern: {pattern} ({layer_str})",
        f"- Communication: {comm}",
        f"- Dashboard: {dash}",
    ])

    # Key Paths
    if paths:
        lines.extend(["", "## Key Paths", "", "| Component | Path |", "|-----------|------|"])
        for key, val in paths.items():
            label = key.replace("_", " ").title()
            lines.append(f"| {label} | `{val}` |")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ROADMAP.md body regeneration
# ---------------------------------------------------------------------------

def render_roadmap_body(fm: Dict[str, Any]) -> str:
    """Regenerate the markdown body of ROADMAP.md from its YAML frontmatter."""
    phases = fm.get("phases", [])

    lines = [
        "",
        "# Roadmap",
        "",
        "> Machine-readable phase data lives in YAML frontmatter above.",
        "> This markdown body is auto-generated — do not edit manually.",
        "",
    ]

    for p in phases:
        num = p.get("number", "?")
        name = p.get("name", "?")
        status = p.get("status", "not_started").upper().replace("_", " ")
        lines.append(f"## Phase {num} — {name} [{status}]")

        if p.get("completed"):
            lines.append(f"- Completed: {p['completed']}")
        if p.get("started") and not p.get("completed"):
            lines.append(f"- Started: {p['started']}")
        if p.get("plan_file"):
            ref = p["plan_file"].replace(".md", "")
            lines.append(f"- Plan: [[planning/{ref}]]")

        deliverables = p.get("deliverables", [])
        if deliverables and status != "COMPLETED":
            lines.append("- Deliverables:")
            for d in deliverables:
                lines.append(f"  - {d}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# State mutations
# ---------------------------------------------------------------------------

def transition_phase(phase_num: int, new_status: str) -> Dict[str, Any]:
    """Transition a phase to a new status. Updates both STATE.md and ROADMAP.md."""
    if new_status not in VALID_STATUSES:
        print(f"Invalid status: {new_status}. Must be one of {VALID_STATUSES}", file=sys.stderr)
        sys.exit(1)

    today = dt.date.today().isoformat()

    # Update ROADMAP.md
    rm_fm, _ = parse_frontmatter(ROADMAP_FILE)
    phases = rm_fm.get("phases", [])
    target_phase = None
    for p in phases:
        if p.get("number") == phase_num:
            p["status"] = new_status
            if new_status == "in_progress" and not p.get("started"):
                p["started"] = today
            if new_status == "completed":
                p["completed"] = today
            target_phase = p
            break

    if not target_phase:
        print(f"Phase {phase_num} not found in roadmap.", file=sys.stderr)
        sys.exit(1)

    rm_fm["phases"] = phases
    write_state_file(ROADMAP_FILE, rm_fm, render_roadmap_body(rm_fm))

    # Update STATE.md
    st_fm, _ = parse_frontmatter(STATE_FILE)
    phase_data = st_fm.get("phase", {})

    if new_status == "completed":
        # Archive current phase as previous, advance to next
        st_fm["previous_phase"] = {
            "number": phase_num,
            "name": target_phase["name"],
            "status": "completed",
            "completed": today,
        }
        # Find next phase
        next_phase = None
        for p in phases:
            if p["number"] == phase_num + 1:
                next_phase = p
                break

        if next_phase:
            st_fm["phase"] = {
                "current": next_phase["number"],
                "name": next_phase["name"],
                "status": "not_started",
                "started": None,
                "completed": None,
                "blockers": [],
            }
        else:
            st_fm["phase"]["status"] = "completed"
            st_fm["phase"]["completed"] = today
    else:
        phase_data["status"] = new_status
        if new_status == "in_progress" and not phase_data.get("started"):
            phase_data["started"] = today
        st_fm["phase"] = phase_data

    write_state_file(STATE_FILE, st_fm, render_state_body(st_fm))

    result = {
        "action": "transition",
        "phase": phase_num,
        "status": new_status,
        "date": today,
    }
    return result


def modify_list(file: Path, section: str, key: str, add: Optional[str], clear: Optional[int]) -> Dict[str, Any]:
    """Add or remove an item from a list field in STATE.md."""
    fm, _ = parse_frontmatter(file)

    container = fm.get(section, {})
    items: List[str] = container.get(key, [])

    if add:
        if add not in items:
            items.append(add)
    elif clear is not None:
        if 0 <= clear < len(items):
            removed = items.pop(clear)
        else:
            print(f"Index {clear} out of range (0-{len(items) - 1})", file=sys.stderr)
            sys.exit(1)

    container[key] = items
    fm[section] = container
    write_state_file(file, fm, render_state_body(fm))

    return {"action": "modify_list", "section": section, "key": key, "items": items}


def set_health(status: str) -> Dict[str, Any]:
    """Set the health status in STATE.md."""
    if status not in VALID_HEALTH:
        print(f"Invalid health status: {status}. Must be one of {VALID_HEALTH}", file=sys.stderr)
        sys.exit(1)

    fm, _ = parse_frontmatter(STATE_FILE)
    health = fm.get("health", {})
    health["status"] = status
    fm["health"] = health
    write_state_file(STATE_FILE, fm, render_state_body(fm))

    return {"action": "set_health", "status": status}


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def query_state(what: str) -> Dict[str, Any]:
    """Query project state and return structured data."""
    if what == "phase":
        fm, _ = parse_frontmatter(STATE_FILE)
        return fm.get("phase", {})
    elif what == "health":
        fm, _ = parse_frontmatter(STATE_FILE)
        return fm.get("health", {})
    elif what == "roadmap":
        fm, _ = parse_frontmatter(ROADMAP_FILE)
        return {"phases": fm.get("phases", [])}
    elif what == "paths":
        fm, _ = parse_frontmatter(STATE_FILE)
        return fm.get("paths", {})
    elif what == "architecture":
        fm, _ = parse_frontmatter(STATE_FILE)
        return fm.get("architecture", {})
    elif what == "all":
        st_fm, _ = parse_frontmatter(STATE_FILE)
        rm_fm, _ = parse_frontmatter(ROADMAP_FILE)
        return {"state": st_fm, "roadmap": rm_fm}
    else:
        print(f"Unknown query: {what}. Try: phase, health, roadmap, paths, architecture, all", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Machine interface for .planning/ state.")
    sub = parser.add_subparsers(dest="command", required=True)

    # query
    q = sub.add_parser("query", help="Query project state")
    q.add_argument("what", choices=["phase", "health", "roadmap", "paths", "architecture", "all"])

    # transition
    t = sub.add_parser("transition", help="Transition phase status")
    t.add_argument("--phase", type=int, required=True)
    t.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))

    # blocker
    b = sub.add_parser("blocker", help="Add or clear phase blockers")
    bx = b.add_mutually_exclusive_group(required=True)
    bx.add_argument("--add", type=str)
    bx.add_argument("--clear", type=int)

    # risk
    r = sub.add_parser("risk", help="Add or clear health risks")
    rx = r.add_mutually_exclusive_group(required=True)
    rx.add_argument("--add", type=str)
    rx.add_argument("--clear", type=int)

    # health
    h = sub.add_parser("health", help="Set health status")
    h.add_argument("--status", required=True, choices=sorted(VALID_HEALTH))

    # regenerate (re-render markdown bodies from YAML)
    sub.add_parser("regenerate", help="Regenerate markdown bodies from YAML frontmatter")

    args = parser.parse_args()

    if args.command == "query":
        result = query_state(args.what)
    elif args.command == "transition":
        result = transition_phase(args.phase, args.status)
    elif args.command == "blocker":
        result = modify_list(STATE_FILE, "phase", "blockers", args.add, args.clear)
    elif args.command == "risk":
        result = modify_list(STATE_FILE, "health", "risks", args.add, args.clear)
    elif args.command == "health":
        result = set_health(args.status)
    elif args.command == "regenerate":
        st_fm, _ = parse_frontmatter(STATE_FILE)
        write_state_file(STATE_FILE, st_fm, render_state_body(st_fm))
        rm_fm, _ = parse_frontmatter(ROADMAP_FILE)
        write_state_file(ROADMAP_FILE, rm_fm, render_roadmap_body(rm_fm))
        result = {"action": "regenerate", "files": [str(STATE_FILE), str(ROADMAP_FILE)]}
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
