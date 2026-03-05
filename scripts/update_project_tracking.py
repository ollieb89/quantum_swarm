#!/usr/bin/env python3
"""Update Obsidian project tracking notes from structured JSON input."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def today_date() -> str:
    return dt.date.today().isoformat()


def iso_week() -> str:
    y, w, _ = dt.date.today().isocalendar()
    return f"{y}-{w:02d}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def split_frontmatter(content: str) -> Tuple[str, str]:
    if content.startswith("---\n"):
        match = re.match(r"^---\n(.*?)\n---\n?", content, re.DOTALL)
        if match:
            return match.group(1), content[match.end() :]
    return "", content


def merge_frontmatter(frontmatter: str, body: str) -> str:
    if frontmatter:
        return f"---\n{frontmatter.strip()}\n---\n\n{body.lstrip()}"
    return body


def set_frontmatter_field(frontmatter: str, key: str, value: str) -> str:
    lines = frontmatter.splitlines() if frontmatter else []
    pattern = re.compile(rf"^{re.escape(key)}:\s*.*$")
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{key}: {value}"
            break
    else:
        lines.append(f"{key}: {value}")
    return "\n".join(lines).strip()


def heading_range(lines: List[str], heading: str) -> Optional[Tuple[int, int]]:
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return start, end


def ensure_lines_in_section(lines: List[str], heading: str, new_lines: List[str]) -> List[str]:
    span = heading_range(lines, heading)
    if not span:
        return lines
    start, end = span
    section = lines[start:end]
    to_add = [ln for ln in new_lines if ln not in section]
    if not to_add:
        return lines
    insert_at = end
    if insert_at > 0 and lines[insert_at - 1].strip() == "":
        insert_at -= 1
    return lines[:insert_at] + to_add + [""] + lines[insert_at:]


def ensure_lines_under_marker(
    lines: List[str],
    section_heading: str,
    marker_line: str,
    new_lines: List[str],
) -> List[str]:
    span = heading_range(lines, section_heading)
    if not span:
        return lines
    start, end = span
    marker_idx = None
    for i in range(start, end):
        if lines[i].strip() == marker_line:
            marker_idx = i
            break
    if marker_idx is None:
        return lines

    insert_at = marker_idx + 1
    while insert_at < end and (lines[insert_at].startswith("  - ") or lines[insert_at].strip() == ""):
        insert_at += 1

    section = lines[start:end]
    to_add = [ln for ln in new_lines if ln not in section]
    if not to_add:
        return lines
    return lines[:insert_at] + to_add + lines[insert_at:]


def ensure_weekly_note(path: Path, project_slug: str, week: str, date_str: str) -> None:
    if path.exists():
        return
    content = f"""---
project: {project_slug}
status: In Progress
owner: ollie
updated: {date_str}
tags:
  - project
  - project/{project_slug}
  - area/delivery
  - status/in-progress
---

# Weekly Status {week}

## Summary
- <update summary>

## Progress
- Completed:
- In progress:

## Blockers
- No blockers recorded.

## Risks
- No additional risks recorded.

## Next Week
- [ ] <next priority>

## Links
- [[Projects/{project_slug}/Overview]]
- [[Projects/{project_slug}/Milestones]]
- [[Projects/{project_slug}/Tasks]]
"""
    write_text(path, content)


def update_weekly(path: Path, payload: Dict[str, Any], project_slug: str, week: str, date_str: str) -> None:
    ensure_weekly_note(path, project_slug, week, date_str)
    content = read_text(path)
    fm, body = split_frontmatter(content)
    fm = set_frontmatter_field(fm, "updated", date_str)

    lines = body.splitlines()
    lines = ensure_lines_in_section(lines, "## Summary", [f"- {x}" for x in payload.get("summary_add", [])])
    lines = ensure_lines_under_marker(
        lines,
        "## Progress",
        "- Completed:",
        [f"  - {x}" for x in payload.get("completed_add", [])],
    )
    lines = ensure_lines_under_marker(
        lines,
        "## Progress",
        "- In progress:",
        [f"  - {x}" for x in payload.get("in_progress_add", [])],
    )
    lines = ensure_lines_in_section(lines, "## Blockers", [f"- {x}" for x in payload.get("blockers_add", [])])
    lines = ensure_lines_in_section(lines, "## Risks", [f"- {x}" for x in payload.get("risks_add", [])])
    lines = ensure_lines_in_section(lines, "## Next Week", [f"- [ ] {x}" for x in payload.get("next_week_add", [])])

    write_text(path, merge_frontmatter(fm, "\n".join(lines).rstrip() + "\n"))


def find_task_line(lines: List[str], needle: str) -> Optional[Tuple[int, str]]:
    for i, line in enumerate(lines):
        if line.startswith("- [") and needle in line:
            return i, line
    return None


def done_section_insert_index(lines: List[str]) -> Optional[int]:
    span = heading_range(lines, "## Done")
    if not span:
        return None
    _, end = span
    insert_at = end
    if insert_at > 0 and lines[insert_at - 1].strip() == "":
        insert_at -= 1
    return insert_at


def to_done_line(line: str, date_str: str) -> str:
    line = re.sub(r"^- \[[ xX]\]", "- [x]", line)
    line = re.sub(r"\|\s*due:\s*[^|]+", "", line)
    line = re.sub(r"\|\s*status:\s*[^|]+", "", line)
    if "| done:" not in line:
        line = f"{line} | done: {date_str}"
    return re.sub(r"\s+\|", " |", line).strip()


def update_tasks(path: Path, payload: Dict[str, Any], date_str: str) -> None:
    content = read_text(path)
    if not content:
        return
    fm, body = split_frontmatter(content)
    fm = set_frontmatter_field(fm, "updated", date_str)

    lines = body.splitlines()

    section_map = {
        "Backlog": "## Backlog",
        "In Progress": "## In Progress",
        "Done": "## Done",
    }

    for item in payload.get("task_add", []):
        section = section_map.get(item.get("section", "Backlog"), "## Backlog")
        checked = item.get("checked", False)
        raw = item["text"].strip()
        line = raw if raw.startswith("- [") else f"- [{'x' if checked else ' '}] {raw}"
        lines = ensure_lines_in_section(lines, section, [line])

    done_targets = payload.get("task_complete", [])
    for needle in done_targets:
        found = find_task_line(lines, needle)
        if not found:
            continue
        idx, line = found
        transformed = to_done_line(line, date_str)
        del lines[idx]
        insert_at = done_section_insert_index(lines)
        if insert_at is None:
            continue
        if transformed not in lines:
            lines = lines[:insert_at] + [transformed] + lines[insert_at:]

    write_text(path, merge_frontmatter(fm, "\n".join(lines).rstrip() + "\n"))


def update_decisions(path: Path, payload: Dict[str, Any], date_str: str) -> None:
    decision = payload.get("decision")
    if not decision:
        return
    content = read_text(path)
    if not content:
        return
    fm, body = split_frontmatter(content)
    fm = set_frontmatter_field(fm, "updated", date_str)

    title = decision["title"].strip()
    header = f"## {date_str} - {title}"
    if header in body:
        write_text(path, merge_frontmatter(fm, body))
        return

    entry = (
        f"\n{header}\n"
        f"- Context: {decision.get('context', '').strip()}\n"
        f"- Decision: {decision.get('decision', '').strip()}\n"
        f"- Consequence: {decision.get('consequence', '').strip()}\n"
    )
    write_text(path, merge_frontmatter(fm, body.rstrip() + "\n" + entry))


def update_overview(path: Path, payload: Dict[str, Any], date_str: str) -> None:
    content = read_text(path)
    if not content:
        return
    fm, body = split_frontmatter(content)
    fm = set_frontmatter_field(fm, "updated", date_str)

    lines = body.splitlines()
    next_actions = payload.get("overview_next_actions_add", [])
    if next_actions:
        lines = ensure_lines_in_section(lines, "## Next Actions", [f"- [ ] {x}" for x in next_actions])

    status_line = payload.get("overview_state")
    if status_line:
        span = heading_range(lines, "## Current Status")
        if span:
            s, e = span
            for i in range(s, e):
                if lines[i].startswith("- State:"):
                    lines[i] = f"- State: {status_line}"
                if lines[i].startswith("- Updated:"):
                    lines[i] = f"- Updated: {date_str}"

    write_text(path, merge_frontmatter(fm, "\n".join(lines).rstrip() + "\n"))


def run_progress_event(vault_root: Path, project_slug: str, payload: Dict[str, Any]) -> None:
    date_str = payload.get("date", today_date())
    week = payload.get("week", iso_week())
    project_dir = vault_root / "Projects" / project_slug

    overview = project_dir / "Overview.md"
    tasks = project_dir / "Tasks.md"
    decisions = project_dir / "Decisions.md"
    weekly = project_dir / "Status" / f"Weekly-{week}.md"

    update_weekly(weekly, payload, project_slug, week, date_str)
    update_tasks(tasks, payload, date_str)
    update_decisions(decisions, payload, date_str)
    update_overview(overview, payload, date_str)

    print(json.dumps(
        {
            "updated_files": [
                str(weekly),
                str(tasks),
                str(decisions),
                str(overview),
            ],
            "project": project_slug,
            "week": week,
            "date": date_str,
        },
        indent=2,
    ))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update Obsidian project tracking notes from JSON input.")
    parser.add_argument("--project", required=True, help="Project slug, e.g. quantum-swarm")
    parser.add_argument("--event", required=True, choices=["progress"], help="Update event type")
    parser.add_argument("--input", required=True, help="Path to JSON payload")
    parser.add_argument(
        "--vault-root",
        default="quantum-swarm",
        help="Vault root path (default: quantum-swarm)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload_path = Path(args.input)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    vault_root = Path(args.vault_root)

    if args.event == "progress":
        run_progress_event(vault_root, args.project, payload)
        return

    raise ValueError(f"Unsupported event: {args.event}")


if __name__ == "__main__":
    main()
