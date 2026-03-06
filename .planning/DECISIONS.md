---
project: quantum-swarm
updated: 2026-03-05
---

# Architecture Decision Records

## 2026-03-05 — Adopt LangGraph StateGraph for Orchestration

Decision:
Migrate from custom StrategicOrchestrator to LangGraph StateGraph.

Reason:
LangGraph provides built-in state management, conditional routing, and
checkpoint/resume semantics that the custom orchestrator reimplemented poorly.

Impact:
All L1 orchestration now flows through `src/graph/orchestrator.py`. Legacy
orchestrator kept as `strategic_l1_legacy.py` for rollback.

## 2026-03-05 — JSON-driven Obsidian Tracking Updates

Decision:
Use structured JSON payloads applied idempotently to Obsidian vault notes.

Reason:
Manual updates are error-prone and inconsistent for recurring project tracking.

Impact:
Project tracking can be triggered from cron/CI and stays consistent over time.
Schema changes require coordinated updates to payload and script.

## 2026-03-05 — Single State Layer with Transclusion Projections

Decision:
Use `.planning/` as the single authoritative state layer. Obsidian vault
surfaces state via symlinks and `![[]]` transclusions — never duplicates it.

Reason:
Multiple sources of truth (plans/, docs/, obsidian/) inevitably drift.
A single canonical state with read-only projections eliminates this failure mode.

Impact:
All planning documents live in `.planning/`. The Obsidian vault is a navigation
layer only. CI and agents read/write `.planning/` directly.
