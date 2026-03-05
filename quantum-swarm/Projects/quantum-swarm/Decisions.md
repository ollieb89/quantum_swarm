---
project: quantum-swarm
status: Planned
owner: ollie
updated: 2026-03-05
tags:
  - project
  - project/quantum-swarm
  - area/delivery
  - status/planned
---

# Decisions

## 2026-03-05 - Prioritize Safe Maintainability Fixes in Core Entry Paths
- Context: First `/sc:improve` pass needed low-risk, high-leverage changes with fast verification.
- Decision: Refactor `src/core/cli_wrapper.py` for shared JSON parsing and fix two correctness bugs; also fix `main.py` class-name mismatch blocking `--mode test`.
- Consequence: Baseline test command now runs successfully; wrapper behavior is simpler and covered by focused unit tests.

## 2026-03-05 - Use Obsidian Structure for Project Tracking
- Context: Project progress needed a consistent tracking system across milestones, tasks, and weekly status.
- Decision: Use standardized notes under `Projects/quantum-swarm/` with linked files for overview, milestones, tasks, decisions, and weekly updates.
- Consequence: Tracking is repeatable and easy to update; future automation can target stable headings/paths.

## 2026-03-05 - Use JSON-driven updates for Obsidian project tracking
- Context: Manual updates are error-prone and inconsistent for recurring project tracking events.
- Decision: Adopt a script that applies structured JSON updates idempotently to Tasks, Weekly Status, Decisions, and Overview notes.
- Consequence: Project tracking can be triggered from cron/CI and stays consistent over time.
