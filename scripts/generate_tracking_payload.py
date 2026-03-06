#!/usr/bin/env python3
"""Generate an Obsidian tracking payload from recent git commits.

Parses conventional commits (feat:, fix:, docs:, refactor:, etc.) from the
git log and maps them into the JSON schema expected by update_project_tracking.py.

Usage:
    python scripts/generate_tracking_payload.py [--commits N] [--output PATH]

Designed to be called from GitHub Actions or cron. Reads git history from the
current working directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


COMMIT_RE = re.compile(
    r"^(?P<type>[a-z]+)"
    r"(?:\((?P<scope>[^)]*)\))?"
    r"(?P<breaking>!)?"
    r":\s*(?P<desc>.+)$",
    re.IGNORECASE,
)

TYPE_LABELS = {
    "feat": "Feature",
    "fix": "Bug fix",
    "docs": "Docs",
    "refactor": "Refactor",
    "test": "Test",
    "chore": "Chore",
    "ci": "CI",
    "perf": "Performance",
    "style": "Style",
    "build": "Build",
    "decision": "Decision",
    "research": "Research",
}

# Commit types that generate architecture decision records
DECISION_TYPES = {"decision", "research"}


def git_log(n: int) -> List[str]:
    """Return the last N commit subject lines."""
    result = subprocess.run(
        ["git", "log", f"-{n}", "--pretty=format:%s"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.strip().splitlines() if line]


def git_changed_files(n: int) -> List[str]:
    """Return files changed in the last N commits."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"HEAD~{n}", "HEAD"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().splitlines() if f]


def parse_commit(subject: str) -> Tuple[str, Optional[str], str]:
    """Parse a conventional commit subject into (type, scope, description)."""
    match = COMMIT_RE.match(subject)
    if match:
        return match.group("type").lower(), match.group("scope"), match.group("desc")
    return "chore", None, subject


def classify_files(files: List[str]) -> Dict[str, List[str]]:
    """Group changed files by area for context."""
    areas: Dict[str, List[str]] = {}
    for f in files:
        if f.startswith("src/"):
            areas.setdefault("source", []).append(f)
        elif f.startswith("scripts/"):
            areas.setdefault("automation", []).append(f)
        elif f.startswith(".planning/"):
            areas.setdefault("planning", []).append(f)
        elif f.startswith(".gemini-kit/"):
            areas.setdefault("plugin-context", []).append(f)
        elif f.startswith("quantum-swarm/"):
            areas.setdefault("obsidian", []).append(f)
        elif f.startswith("docs/") or f.endswith(".md"):
            areas.setdefault("docs", []).append(f)
        elif f.startswith("tests/"):
            areas.setdefault("tests", []).append(f)
        else:
            areas.setdefault("other", []).append(f)
    return areas


def build_decision_entry(date_str: str, desc: str, scope: Optional[str], files: List[str]) -> str:
    """Build a markdown ADR entry for .planning/DECISIONS.md."""
    scope_str = f" ({scope})" if scope else ""
    impacted = ", ".join(files[:5]) if files else "N/A"
    return (
        f"\n## {date_str} — {desc}{scope_str}\n\n"
        f"Decision:\n{desc}\n\n"
        f"Reason:\nRecorded from commit.\n\n"
        f"Impact:\nFiles impacted: {impacted}\n"
    )


def append_decisions_to_planning(
    parsed: List[Tuple[str, Optional[str], str]], files: List[str], date_str: str, planning_dir: Path
) -> None:
    """Append decision/research commits to .planning/DECISIONS.md."""
    decision_commits = [(ctype, scope, desc) for ctype, scope, desc in parsed if ctype in DECISION_TYPES]
    if not decision_commits:
        return

    decisions_path = planning_dir / "DECISIONS.md"
    if not decisions_path.exists():
        return

    content = decisions_path.read_text(encoding="utf-8")
    new_entries = []
    for ctype, scope, desc in decision_commits:
        header = f"## {date_str} — {desc}"
        if header not in content:
            new_entries.append(build_decision_entry(date_str, desc, scope, files))

    if new_entries:
        content = content.rstrip() + "\n" + "".join(new_entries)
        decisions_path.write_text(content, encoding="utf-8")


def build_payload(commits: List[str], files: List[str]) -> Dict[str, Any]:
    """Build the tracking_update.json payload from parsed commits."""
    today = dt.date.today()
    year, week_num, _ = today.isocalendar()

    parsed = [parse_commit(c) for c in commits]
    areas = classify_files(files)

    # Summary: one line per commit, labeled by type
    summary_add = []
    for ctype, scope, desc in parsed:
        label = TYPE_LABELS.get(ctype, ctype.capitalize())
        scope_str = f" ({scope})" if scope else ""
        summary_add.append(f"[{label}]{scope_str} {desc}")

    # Completed: features and fixes
    completed = [desc for ctype, _, desc in parsed if ctype in ("feat", "fix")]

    # In progress: refactors, tests, docs (likely ongoing)
    in_progress = [desc for ctype, _, desc in parsed if ctype in ("refactor", "test", "docs", "perf")]

    # Tasks: add each commit as a done task
    task_add = []
    for ctype, scope, desc in parsed:
        label = TYPE_LABELS.get(ctype, ctype.capitalize())
        task_add.append({
            "section": "Done",
            "text": f"[{label}] {desc} | owner: ci | done: {today.isoformat()}",
            "checked": True,
        })

    # Decision/research commits also produce Obsidian decision entries
    decision_commits = [(ctype, scope, desc) for ctype, scope, desc in parsed if ctype in DECISION_TYPES]
    decision = None
    if decision_commits:
        _, scope, desc = decision_commits[0]
        decision = {
            "title": desc,
            "context": f"Recorded from commit ({scope or 'general'}).",
            "decision": desc,
            "consequence": f"Files impacted: {', '.join(files[:5]) if files else 'N/A'}",
        }

    # File-area based risks/notes
    risks = []
    if "source" in areas and len(areas["source"]) > 5:
        risks.append(f"Large changeset across {len(areas['source'])} source files — review for regressions.")
    if "plugin-context" in areas:
        risks.append("Plugin context (.gemini-kit) was modified — verify downstream plugin compatibility.")
    if "planning" in areas:
        risks.append("Planning state (.planning) was modified — ensure roadmap consistency.")

    payload: Dict[str, Any] = {
        "date": today.isoformat(),
        "week": f"{year}-{week_num:02d}",
        "summary_add": summary_add or [f"CI sync: {len(commits)} commit(s) on {today.isoformat()}"],
        "completed_add": completed,
        "in_progress_add": in_progress,
        "blockers_add": [],
        "risks_add": risks,
        "next_week_add": [],
        "task_add": task_add,
        "task_complete": [],
        "overview_next_actions_add": [],
        "overview_state": "In Progress",
    }

    if decision:
        payload["decision"] = decision

    return payload, parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Obsidian tracking payload from git commits.")
    parser.add_argument("--commits", type=int, default=1, help="Number of recent commits to parse (default: 1)")
    parser.add_argument("--output", default=None, help="Output path (default: stdout)")
    parser.add_argument("--planning-dir", default=".planning", help="Path to .planning directory")
    args = parser.parse_args()

    commits = git_log(args.commits)
    if not commits:
        print("No commits found.", file=sys.stderr)
        sys.exit(1)

    files = git_changed_files(args.commits)
    payload, parsed = build_payload(commits, files)

    # Append decision/research commits to .planning/DECISIONS.md
    planning_dir = Path(args.planning_dir)
    if planning_dir.exists():
        append_decisions_to_planning(parsed, files, payload["date"], planning_dir)

    output = json.dumps(payload, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Payload written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
