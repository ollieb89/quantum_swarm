# Phase 19: ARS Drift Auditor - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Standalone out-of-band auditor that computes five drift metrics from MEMORY.md evolution logs, detects ego-hijacking and persona drift, and suspends evolution for flagged agents. Never gates trade execution. Uses stdlib regex + Counter cosine only — no LLM calls, no external dependencies beyond existing `pyproject.toml`.

</domain>

<decisions>
## Implementation Decisions

### Drift Thresholds & Alerting

- **Per-metric thresholds** — each of the 5 metrics has its own independent threshold. Any single breach triggers a flag. No composite drift score.
- **Flag-then-suspend** — first breach = WARNING log + audit event. Sustained breach over N=3 consecutive audits = auto-suspend `evolution_suspended=True`. Breach counter resets to zero on clean audit cycle (consecutive breaches only, not cumulative).
- **Ops alerting** — structured JSON events appended to `data/audit.jsonl` (same file as rule validation and decision card events). Schema: `event`, `agent`, `metric`, `value`, `threshold`, `breach_count`, `action`, `audit_cycle`, `ts`. Plus Python `WARNING` for flags, `CRITICAL` for suspensions.
- **Breach counter persistence** — breach counts per agent per metric stored in dedicated `ars_state` PostgreSQL table (not in `agent_merit_scores`). Separates ARS control state from merit scores.

### Metric Computation — Five Drift Metrics

**1. Diff Rejection Rate (two sub-metrics)**
- `proposal_rejection_rate` — `rejected / total` proposals from `data/soul_proposals/*.json` for each agent over trailing window. Measures failed self-mutation instability.
- `drift_flag_frequency` — ratio of MEMORY.md entries with non-empty `[DRIFT_FLAGS:]` over recent cycles. Measures runtime behavioral anomalies.
- Both tracked independently with separate thresholds. Both are ARS-gated metrics.

**2. KAMI Dimension Variance (primary + diagnostic)**
- Primary ARS metric: cross-dimension variance — `statistics.variance([accuracy, recovery, consensus, fidelity])` for a single agent. Detects lopsided capability degradation.
- Diagnostic telemetry (logged, not threshold-gated): temporal variance per dimension over rolling window. Detects erratic oscillation.

**3. Alignment Section Mutation Count**
- Counts approved SOUL.md replacements targeting **identity-critical sections only**: `Core Beliefs`, `Drift Guard`, `Core Wounds`.
- Operational sections (`Workflow Rules`, `Output Contract`) are tracked as diagnostic telemetry (`operational_edit_count`) but do NOT count toward this ARS metric.
- One mutation event per approved H2 section replacement (Phase 17 atomic edit unit).
- Source: scan `data/soul_proposals/*.json` with `status=approved` and `target_section` matching identity-critical list.

**4. Self-Reflection Sentiment Shift**
- Analyzes `[THESIS_SUMMARY:]` text from MEMORY.md entries using three lexicons: `bullish_terms`, `bearish_terms`, `uncertainty_terms`.
- Per entry: build normalized 3-dim vector `{bullish: hits/tokens, bearish: hits/tokens, uncertainty: hits/tokens}` + signed polarity `bullish_hits - bearish_hits`.
- Compare current entry to agent's rolling baseline (last N summaries) via cosine distance on 3-dim vector + polarity delta.
- Flag when BOTH: semantic distance from baseline exceeds threshold AND polarity delta exceeds threshold (or polarity sign flips).
- Distance catches tone drift; polarity delta catches directional drift; sign flip catches obvious reversals.

**5. Role Boundary Vocabulary Violations**
- Per-agent forbidden vocabulary list keyed to soul archetype (e.g., CASSANDRA forbidden: `breakout`, `opportunity`, `upside`, `acceleration`; MOMENTUM forbidden: `capitulation`, `structural impairment`, `downside spiral`).
- Context-aware counting: forbidden term counts as violation only when near assertion markers (`is`, `likely`, `expect`, `suggests`) and NOT near negation/refutation markers (`not`, `unlikely`, `despite`, `however`, `risk`).
- Prevents false flags on rebuttal context (e.g., "The bull case hinges on breakout expectations, but I do not endorse it" — not a violation).
- Score: `weighted_forbidden_hits / token_count`. Flag when score exceeds threshold or absolute `forbidden_hits >= min_hits`.

### Invocation & Scheduling

- **Standalone `__main__` script** — `python -m src.core.ars_auditor`. Same pattern as Agent Church (`python -m src.core.agent_church`). Not a LangGraph node.
- **Own systemd timer** — separate from Obsidian tracking timer. More frequent than weekly (daily or every N hours). Timer frequency is Claude's discretion.
- **All agents by default** — single run audits all 5 agents sequentially. `--agent MOMENTUM` flag for single-agent targeted runs. Also supports `--dry-run` and `--verbose`.
- **30-cycle warm-up** — agents with fewer than 30 MEMORY.md entries do not trigger alerts regardless of metric values (ARS-01 requirement).

### Suspension & Recovery

- **Full evolution freeze** — when `evolution_suspended=True`, `memory_writer` skips MEMORY.md write AND skips SOUL proposal emission for that agent. Diagnostic visibility via log line ("memory_writer skipped due to evolution_suspended") only.
- **memory_writer gate** — `memory_writer_node` must check `evolution_suspended` flag (from DB or SwarmState) before writing. Early return if suspended.
- **Manual unsuspend only** — `python -m src.core.ars_auditor --unsuspend MOMENTUM`. Human must review drift before re-enabling evolution. Writes `ARS_UNSUSPEND` audit event.
- **Reset on unsuspend** — breach counters reset to zero on manual unsuspend. Audit history preserved in `audit.jsonl`. Clean slate for new observation window.
- **Strict scope boundary** — no code path connects `evolution_suspended` to `order_router_node` or `route_after_institutional_guard`. Suspension gates evolution only, never trade execution (ARS-02 requirement).

### Claude's Discretion

- Exact threshold values for each of the 5 metrics
- `swarm_config.yaml` schema for ARS config section
- `ars_state` PostgreSQL table schema (columns, indexes)
- Systemd timer frequency (daily vs every N hours)
- Exact bullish/bearish/uncertainty lexicon contents
- Exact assertion/negation marker lists
- Rolling baseline window size N for sentiment shift
- Cosine distance implementation details (Counter-based)
- How `memory_writer` reads `evolution_suspended` (DB query vs SwarmState field loaded at session start)

</decisions>

<specifics>
## Specific Ideas

- ARS events use same `data/audit.jsonl` as rule validation and decision cards — single audit surface, no split-brain
- `ars_state` table is semantically separate from `agent_merit_scores` — merit = learned performance score, ARS state = control/safety state machine
- Sentiment shift requires BOTH distance AND polarity breach to flag — avoids false positives from minor wording drift
- Role boundary violations use context guards (assertion vs negation proximity) to avoid penalizing agents who mention opposing vocabulary in rebuttal
- "Consecutive breaches" means consecutive auditor runs where the metric is above threshold — counter resets on any clean run
- Suspension is a hard freeze: no MEMORY.md, no proposals, no evolution artifacts. If you want forensic visibility, it belongs in audit/log telemetry, not the agent's own memory stream
- Manual unsuspend is the explicit human checkpoint — implies the drift was investigated and the agent is cleared to evolve again

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/graph/nodes/memory_writer.py` — MEMORY.md entry parser, `_extract_drift_flags()`, entry boundary parsing (`=== timestamp ===`). Source data for ARS metric computation.
- `src/core/agent_church.py` — standalone `__main__` script pattern. Template for `ars_auditor.py` invocation structure.
- `src/core/persistence.py` — `AsyncConnectionPool`, `setup_persistence()` with `CREATE TABLE IF NOT EXISTS` pattern. Use for `ars_state` table creation.
- `src/core/kami.py` — `ALL_SOUL_HANDLES` list for iterating agents; `compute_merit()` for KAMI dimension access.
- `data/audit.jsonl` — existing append-only audit file. ARS events use same format.
- `config/swarm_config.yaml` — existing config pattern. Add `ars:` section for thresholds and lexicons.
- `src/core/persistence.py:115` — `evolution_suspended BOOLEAN DEFAULT FALSE` column already exists in `agent_merit_scores` table (pre-declared in Phase 16).

### Established Patterns
- **Standalone out-of-band scripts:** `agent_church.py` pattern — `__main__` module, argparse, not a LangGraph node
- **Atomic file writes:** temp file + `os.rename()` (POSIX atomic) — use for any file outputs
- **Non-blocking node pattern:** memory_writer logs errors and continues cycle — same pattern for suspension gate check
- **Config-driven tunables:** `_load_kami_config()` pattern from merit_updater — replicate for ARS config
- **MEMORY.md entry parsing:** `=== timestamp ===` separator, labeled lines with `[FIELD:]` format — established in Phase 17

### Integration Points
- `src/core/ars_auditor.py` — new standalone module (Phase 19 primary deliverable)
- `src/core/persistence.py:setup_persistence()` — add `CREATE TABLE IF NOT EXISTS ars_state` block
- `src/graph/nodes/memory_writer.py` — add `evolution_suspended` gate check at start of per-agent processing
- `config/swarm_config.yaml` — add `ars:` config section with thresholds, lexicons, and timing
- `scripts/` — new systemd timer unit file for ARS scheduling

</code_context>

<deferred>
## Deferred Ideas

- LLM-judged drift detection (semantic persona consistency) — Out of Scope per REQUIREMENTS.md (circular evaluation, shared base model blind spots)
- Sentence-transformers for ARS — Out of Scope per REQUIREMENTS.md (cold-start latency not justified at v1.3 scale)
- Auto-recovery after cooldown — explicitly rejected; manual unsuspend only for v1.3
- KAMI profile entropy (replacing variance) — future phase when swarm matures
- Adaptive threshold tuning based on market regime — future phase
- ARS dashboard / observability UI — future phase

</deferred>

---

*Phase: 19-ars-drift-auditor*
*Context gathered: 2026-03-08*
