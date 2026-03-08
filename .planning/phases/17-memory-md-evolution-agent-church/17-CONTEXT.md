# Phase 17: MEMORY.md Evolution + Agent Church - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Each agent maintains a capped structured self-reflection log (`src/core/souls/{agent_id}/MEMORY.md`) that is written after every task cycle. Agents can propose edits to their own `SOUL.md` via atomic JSON files in `data/soul_proposals/`. A standalone out-of-band script (`python -m src.core.agent_church`) reviews pending proposals and applies or rejects them using a structural heuristic — no LLM calls, no semantic evaluation. LLM-judged review (Theory of Mind), pre-debate soul handshakes, and ARS drift metrics are separate phases.

</domain>

<decisions>
## Implementation Decisions

### MEMORY.md Entry Format

Fixed-field template — one entry per active agent per cycle. Each entry uses labeled lines for deterministic machine parsing by Phase 19 ARS Drift Auditor.

```text
=== 2026-03-08T12:34:56Z ===
[AGENT:] CASSANDRA
[KAMI_DELTA:] +0.04
[MERIT_SCORE:] 0.81
[DRIFT_FLAGS:] none
[THESIS_SUMMARY:] Inflation surprise risk remains underpriced; maintain hawkish bias.
```

Rules:
- Entries are appended (newest at bottom)
- File is capped at 50 entries; oldest entries removed when limit is exceeded
- `[DRIFT_FLAGS:]` contains `none` when no flags are set, or a comma-separated list of flag names
- `[THESIS_SUMMARY:]` is a deterministic one-line extract from the agent's canonical output field (first thesis-bearing sentence), truncated to a sane char limit — NOT a newly authored summary (no extra LLM call)

**Per-agent canonical output field map (for thesis extract):**
- `AXIOM` (macro_analyst) → `state["macro_report"]` — first sentence
- `MOMENTUM` (bullish_researcher) → `state["bullish_thesis"]` — first sentence
- `CASSANDRA` (bearish_researcher) → `state["bearish_thesis"]` — first sentence
- `SIGMA` (quant_modeler) → `state["quant_proposal"]` — first sentence
- `GUARDIAN` (risk_manager) → `state["risk_approval"]` reasoning field — first sentence

**Skip-on-no-output rule:** If the canonical output field for an agent is `None` or absent in this cycle, do not write a MEMORY entry for it. A MEMORY entry = "agent expressed a thesis or decision this cycle." GUARDIAN silence implies system stability — no sentinel entry.

### Orchestrator Wiring

New standalone node: `memory_writer`

**Graph position:** `merit_updater → memory_writer → trade_logger`

This placement ensures:
- `[KAMI_DELTA:]` and `[MERIT_SCORE:]` reflect post-update settled merit values
- MEMORY log is the post-merit, pre-finalization forensic layer (consistent with Phase 16 pattern)

Implementation:
- Single node that iterates all 5 soul handles
- For each agent: checks canonical field; writes MEMORY entry if non-None; then evaluates SOUL proposal triggers
- **Silent node**: no SwarmState field added (no `memory_write_status`)
- **Non-blocking**: on write failure, log high-severity error and continue cycle — MEMORY is forensic infrastructure, not trade-critical

### SOUL.md Proposal Trigger

Located inside `memory_writer`, after each agent's MEMORY entry write.

**Three triggers — OR logic (any one fires the proposal):**

1. **KAMI delta threshold** — `|KAMI_DELTA| >= kami_delta_threshold` (default: 0.05)
   Catches sudden merit shocks suggesting identity drift

2. **Drift streak** — last `drift_streak_n` consecutive MEMORY entries for this agent all have non-empty `[DRIFT_FLAGS:]`
   Catches slow, sustained behavioral drift
   Detection: read and parse the tail of the agent's MEMORY.md after the current entry is written; inspect last N entries' `[DRIFT_FLAGS:]` lines by entry boundary (not raw grep). "Consecutive" = consecutive logged entries for that agent, not global swarm cycles.

3. **Sustained merit decline** — agent's `[MERIT_SCORE:]` has been `<= merit_floor` for the last `merit_floor_k` consecutive MEMORY entries
   Catches chronic underperformance
   Detection: same tail-read approach as drift streak

**Emission rule:** If one or more triggers fire for an agent in a cycle, emit **one merged proposal** with `proposal_reasons` listing all matched triggers (e.g., `["KAMI_SPIKE", "DRIFT_STREAK"]`). No separate proposals per trigger.

**Config in `swarm_config.yaml`** (consistent with KAMI EMA config pattern):
```yaml
phase17:
  kami_delta_threshold: 0.05
  drift_streak_n: 3
  merit_floor: 0.40
  merit_floor_k: 3
  soul_autoapprove_max_chars: 500
  soul_autoapprove_allowed_ops:
    - section_patch
  rate_limit_rejection_k: 3
  rate_limit_window_days: 7
```

### Proposal JSON Schema

Atomic write to `data/soul_proposals/` (temp file + rename). Files accumulate per proposal (not one file per agent) to serve as the rejection ledger.

Pydantic-validated schema:
```json
{
  "proposal_id": "cass_2026_03_08T124122Z",
  "agent_id": "CASSANDRA",
  "target_section": "## Core Beliefs",
  "proposed_content": "## Core Beliefs\n\nInflation regime shifts occur faster than consensus models assume...",
  "proposal_reasons": ["KAMI_SPIKE", "DRIFT_STREAK"],
  "rationale": "Merit declined sharply; drift flags raised on 3 consecutive cycles.",
  "proposed_at": "2026-03-08T12:41:22Z",
  "status": "pending",
  "rejection_reason": null
}
```

Status values: `pending | approved | rejected | rate_limited`

`proposed_content` = **full replacement text for the target H2 section** (not a unified diff). Agent Church locates the target H2, replaces everything until the next H2 with `proposed_content`. No diff engine required.

### Agent Church Review Policy

**Auto-approve conditions (all must be true):**
- `agent_id` is not L1 Orchestrator
- `target_section` exists as a known H2 in current `SOUL.md`
- `len(proposed_content) <= soul_autoapprove_max_chars` (500 chars default)
- `operation` is `section_patch` (replace single existing section, no structural changes)

**Auto-reject conditions (any one triggers rejection):**
- Target section does not exist in current `SOUL.md`
- `proposed_content` exceeds char limit
- Proposal targets multiple sections
- Proposal modifies headings or file structure
- Empty or malformed diff
- Proposer is L1 Orchestrator → raises `RequiresHumanApproval` instead

**Post-approval:** Agent Church calls `load_soul.cache_clear()` + `warmup_soul_cache()` after applying the section replacement (Phase 15 pattern).

**Rate-limiting:** After `rate_limit_rejection_k = 3` rejections for the same `(agent_id, target_section)` key within `rate_limit_window_days = 7` days, suppress new proposals for that pair and log a rate-limit event.
- Rate-limit count: inferred by scanning existing proposal JSON files for matching `agent_id + target_section` with `status == "rejected"` within the window. Proposals double as both the workflow queue and the rejection ledger — no separate persistence surface.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/core/soul_loader.py` — `load_soul()` with `@lru_cache`, `warmup_soul_cache()`, `SoulSecurityError` — use for post-approval cache invalidation and warmup
- `src/graph/nodes/merit_updater.py` — template for `memory_writer` node: same config-loading pattern (`_load_kami_config()`), same position in the post-execution chain
- `src/core/kami.py` — `ALL_SOUL_HANDLES` list for iterating the 5 agents; `RESEARCHER_HANDLE_MAP` for handle-to-agent-id mapping
- `tests/core/conftest.py` — `clear_soul_caches` autouse fixture (extend with `load_soul.cache_clear()` as needed for new cached functions)

### Established Patterns
- **Post-mutation soul cache refresh:** `load_soul.cache_clear()` + `warmup_soul_cache()` (Phase 15, locked)
- **AUDIT_EXCLUDED_FIELDS:** MEMORY.md writes are file side effects, not SwarmState mutations — no audit exclusion needed for memory_writer (it touches no state fields)
- **Non-blocking node failure:** log high-severity error, do not halt cycle (Phase 11 `decision_card_writer` pattern)
- **Config-driven tunables:** `_load_kami_config()` pattern in merit_updater — replicate for MEMORY/proposal config
- **Atomic file write:** temp file + `os.rename()` (POSIX atomic) — use for `data/soul_proposals/` writes
- **H2 section parsing:** Soul files use stable H2 anchors (`## Core Beliefs`, `## Drift Guard`, etc.) — Agent Church targets these by name, replaces until next H2

### Integration Points
- `src/graph/orchestrator.py` line 344-345: `decision_card_writer → merit_updater → trade_logger` becomes `decision_card_writer → merit_updater → memory_writer → trade_logger`
- `src/core/souls/{agent_id}/MEMORY.md` — new file per agent (does not yet exist; created on first write)
- `data/soul_proposals/` — new directory for proposal JSON files (created by memory_writer on first proposal)
- `config/swarm_config.yaml` — extend with `phase17:` config block

</code_context>

<specifics>
## Specific Ideas

- "Is MEMORY.md a forensic log, or just a merit journal?" — Decision: **forensic log**. Every entry reflects observable agent behavior; entries are skipped when an agent produced no output. Phase 19 ARS Drift Auditor depends on this signal density.
- Proposal reasons field example: `["KAMI_SPIKE", "DRIFT_STREAK", "MERIT_FLOOR"]` — all matched triggers in one merged proposal, not separate artifacts
- Drift streak detection reads the MEMORY.md tail **after** appending the current entry, parsing by entry boundary (`=== timestamp ===` separator), not raw line grep. "N consecutive logged entries" means entries that were actually written, not global swarm cycle count.
- Agent Church is a standalone Python script, not a LangGraph node. It runs out-of-band (`python -m src.core.agent_church`), not in the trade execution path.
- `RequiresHumanApproval` — a custom exception raised (not silently swallowed) when L1 Orchestrator self-proposes. Phase 17 does not auto-approve or silently skip L1 proposals.

</specifics>

<deferred>
## Deferred Ideas

- LLM-judged proposal review (semantic persona consistency check) — Phase 18 Theory of Mind
- Fidelity dimension structural section checks in KAMI — Phase 18
- ARS drift metrics computed from MEMORY.md logs (five drift metrics, evolution_suspended column) — Phase 19
- Public soul summaries for pre-debate handshake — Phase 18

</deferred>

---

*Phase: 17-memory-md-evolution-agent-church*
*Context gathered: 2026-03-08*
