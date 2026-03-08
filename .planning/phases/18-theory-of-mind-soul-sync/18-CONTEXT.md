# Phase 18: Theory of Mind Soul-Sync - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

BullishResearcher and BearishResearcher exchange public soul summaries as a barrier step before DebateSynthesizer. The handshake populates `soul_sync_context` in SwarmState from lru_cache — no LLM calls. Researchers produce their theses with static USER.md few-shots only (no dynamic peer injection). The synthesizer is unchanged. ARS Drift Auditor (Phase 19) reads `soul_sync_context` downstream. Full researcher soul population (SOUL-08) is a v2+ concern.

</domain>

<decisions>
## Implementation Decisions

### Graph Topology

- **Barrier node position:** `{bullish_researcher, bearish_researcher} → soul_sync_handshake_node → debate_synthesizer`
- Researchers run in parallel (fan-out topology preserved exactly)
- `soul_sync_handshake_node` is a join/barrier that fires after both researcher threads complete
- `soul_sync_handshake_node` makes zero LLM calls — pure lru_cache reads
- DebateSynthesizer is unchanged in Phase 18; still uses KAMI merit scores for weighting

### soul_sync_context SwarmState field

- New field: `soul_sync_context: Optional[Dict[str, str]] = None`
- Plain field, no Annotated reducer (same pattern as `merit_scores`)
- Written once by `soul_sync_handshake_node`, never accumulated
- Content: `{"MOMENTUM": "<300-char summary>", "CASSANDRA": "<300-char summary>"}`
- Pre-declared in `AUDIT_EXCLUDED_FIELDS` (already present in audit_logger.py from Phase 17 prep)

### public_soul_summary() method on AgentSoul

- **Included sections (fixed order):** `## Core Beliefs`, `## Voice`, `## Non-Goals`
- **Excluded sections:** `{"Drift Guard", "Core Wounds"}` — guard-only if absent (no-op, not error)
- **Format:** verbatim prose extraction, normalize whitespace, cap at ~300 characters
- Principle: peers see reasoning shape (epistemology, communication style, explicit non-goals), not vulnerabilities or internal drift tripwires
- "Core Wounds" does not exist in any soul file in Phase 18 — the exclusion guard is forward-compatible dormant logic

### AgentSoul — users field (USER.md)

- `AgentSoul` grows a new field: `users: str` (default `""`)
- Loaded from `USER.md` in the agent's soul directory; graceful degradation — file absent = empty string, not error
- `warmup_soul_cache()` must still pass with missing USER.md
- `AgentSoul.system_prompt` property extended to include `users` content after AGENTS.md
- USER.md content flows into `system_prompt` (SwarmState field), which is already in `AUDIT_EXCLUDED_FIELDS` — no separate exclusion needed

### USER.md Empathetic Refutation Few-Shots

- **Format:** Fixed prose examples — no `{peer_summary}` or `{peer_handle}` runtime placeholders
- Static examples that demonstrate refutation tone and style relative to the opponent archetype
- Follows project-wide preference for deterministic, statically-testable artifacts over runtime templating
- **Volume:** 2–3 examples per researcher
  - Example themes: opponent makes strong evidence-backed argument; opponent argument is weak/unsupported; neutral/uncertain regime
- Tests: string assertions against static file content (same pattern as soul content fidelity tests in Phase 15)
- Only `bullish_researcher` and `bearish_researcher` require USER.md — other agents do not debate

### Claude's Discretion

- Exact prose content of USER.md few-shot examples for MOMENTUM and CASSANDRA
- Section extraction implementation detail (H2 heading parser, whitespace normaliser)
- Whether `soul_sync_handshake_node` is wrapped with `with_audit_logging` or is bare (no output → no audit record needed)
- `SwarmState` field order for `soul_sync_context` (after `merit_scores`)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `src/core/soul_loader.py` — `AgentSoul` frozen dataclass (add `users: str = ""`), `load_soul()` with `@lru_cache`, `warmup_soul_cache()` — extend gracefully with optional USER.md load
- `src/core/audit_logger.py` — `AUDIT_EXCLUDED_FIELDS` already contains `"soul_sync_context"` (pre-declared Phase 17 prep); `system_prompt` exclusion already covers USER.md content injected via `system_prompt` property
- `src/graph/nodes/memory_writer.py` — template for `soul_sync_handshake_node`: same non-blocking, no-LLM pattern; silent node with no SwarmState field output beyond its one target field
- `src/core/souls/macro_analyst/SOUL.md` — reference for H2 section structure: `## Core Beliefs`, `## Drift Guard`, `## Voice`, `## Non-Goals` — these heading names are the extraction targets
- `tests/core/conftest.py` — `clear_soul_caches` autouse fixture calls `load_soul.cache_clear()` — extend to cover `AgentSoul` hashability after adding `users` field

### Established Patterns

- **Frozen dataclass + lru_cache:** Adding `users: str = ""` to `AgentSoul` — must remain frozen (required for lru_cache hashability with fan-out concurrent reads)
- **Optional file graceful degradation:** Use `try/except FileNotFoundError` for USER.md load, same as skeleton soul handling in Phase 15
- **system_prompt property concatenation:** Currently `identity + soul + agents`; extend to `identity + soul + agents + users` (skip if empty)
- **Barrier node in LangGraph:** `workflow.add_edge(["bullish_researcher", "bearish_researcher"], "soul_sync_handshake_node")` then `workflow.add_edge("soul_sync_handshake_node", "debate_synthesizer")` — replaces the existing direct `→ debate_synthesizer` edge
- **Plain SwarmState field (no reducer):** `soul_sync_context: Optional[Dict[str, str]]` — same as `merit_scores`

### Integration Points

- `src/core/soul_loader.py` — add `users: str` field to `AgentSoul`; extend `load_soul()` to attempt USER.md read; extend `system_prompt` property
- `src/graph/state.py` — add `soul_sync_context: Optional[Dict[str, str]]` field
- `src/graph/orchestrator.py` — wire `soul_sync_handshake_node` between researcher fan-in and debate_synthesizer; add node registration
- `src/core/souls/bullish_researcher/USER.md` — new file (2–3 Empathetic Refutation examples vs. CASSANDRA archetype)
- `src/core/souls/bearish_researcher/USER.md` — new file (2–3 Empathetic Refutation examples vs. MOMENTUM archetype)
- `src/core/audit_logger.py` — no changes needed (`soul_sync_context` already excluded)

</code_context>

<specifics>
## Specific Ideas

- "The intended responsibility split is: researchers produce thesis work with static few-shot identity; soul_sync_handshake_node merges/prepares dynamic soul sync context; debate_synthesizer consumes that context for final synthesis; ARS/auditor inspects the same synced context downstream."
- "Peers should see reasoning shape, not vulnerabilities or internal tripwires." — Core Beliefs + Voice + Non-Goals is the curated peer-visible identity signal.
- "Drift Guard is internal governance metadata, not peer-facing reasoning context." — Excluded from public summary.
- "Core Wounds: guard-only if present" — `exclude_sections = {"Drift Guard", "Core Wounds"}` — no-op if section absent. Forward-compatible.
- `public_soul_summary()` example output shape: "CASSANDRA emphasizes regime shifts, inflation surprises, and structural fragility. Speaks in terse, caution-first language. Avoids consensus comfort, narrative smoothing, and overreliance on lagging indicators."
- soul_sync_context is populated for Phase 19 ARS + future phases — DebateSynthesizer does not consume it in Phase 18.

</specifics>

<deferred>
## Deferred Ideas

- Dynamic peer soul injection into researcher system prompt at runtime (pre-researcher handshake) — would make empathetic refutation genuinely dynamic but changes researcher output semantics; deferred until skeleton souls are fully populated (SOUL-08, v2+)
- Richer soul_sync_context structure with metadata (sections_included, generated_at) — Phase 19 can extend if ARS needs it
- Template-based USER.md with {peer_summary} interpolation — deferred until static few-shots prove insufficient
- Full researcher soul population (MOMENTUM/CASSANDRA HEXACO-6 profiles) — SOUL-08, v2+

</deferred>

---

*Phase: 18-theory-of-mind-soul-sync*
*Context gathered: 2026-03-08*
