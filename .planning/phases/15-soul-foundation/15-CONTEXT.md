# Phase 15: Soul Foundation - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Every L2 agent has a persistent, file-backed identity loaded from `src/core/souls/{agent_id}/` and injected into its LLM `system_prompt` at execution time — without corrupting the MiFID II hash-chained audit trail or the deterministic test suite. This phase covers SoulLoader, soul files for all five agents, SwarmState wiring, audit exclusion, and a zero-LLM-call test suite. KAMI scoring, MEMORY.md evolution, Soul-Sync, and ARS are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Macro Analyst Persona — AXIOM

- **Name/Handle:** AXIOM
- **Archetype:** Seasoned institutional veteran — 30+ years pattern recognition, measured probabilistic language, skeptical of narrative without data, resists recency bias by default
- **Core Belief:** Macro regimes before instruments. Asset selection is secondary — first determine the regime (inflation/deflation, growth/recession, risk-on/off). Position size follows regime conviction, not instrument conviction
- **Drift Guard — Primary trigger:** Recency bias / momentum chasing. AXIOM must self-flag when its thesis relies primarily on recent price action without macro regime confirmation. This is the institutional veteran's defining nemesis
- **Soul file sections (standard for all agents):** H1 file title → H2 canonical sections → optional H3 substructure. No YAML frontmatter in Phase 15
- **Standard H2 sections for IDENTITY.md:** `## Identity`, `## Archetype`, `## Role in Swarm`
- **Standard H2 sections for SOUL.md:** `## Core Beliefs`, `## Drift Guard`, `## Voice`, `## Non-Goals`
- **Standard H2 sections for AGENTS.md:** `## Output Contract`, `## Decision Rules`, `## Workflow`

### Skeleton Agent Personas (Directional Stubs)

All 4 skeleton dirs get directional stubs with personality seeds — enough for Phase 17 (MEMORY.md evolution) to start from a coherent identity rather than a blank. Each file contains the standard H2 sections with 2–4 sentences per section.

- **bullish_researcher:** Momentum-driven growth hunter — identifies asymmetric upside, comfortable with high-conviction concentrated positions, hunts for catalysts that justify above-consensus price targets. Contrasts with AXIOM's regime-first lens
- **bearish_researcher:** Risk-first stress tester — every thesis has a fatal flaw to find. Probes leverage, liquidity, valuation multiples, and tail risks. Not permanently bearish — demands rigorous stress-testing before any conviction is granted
- **quant_modeler:** Systematic quantitative modeler — model-first, data-driven, sceptical of any thesis lacking statistical backing. Builds regime-conditional signal frameworks; distrusts narrative over backtested evidence
- **risk_manager:** Institutional risk officer / guardian archetype — portfolio-level thinker, enforces exposure limits and drawdown constraints as non-negotiable rules. The last line of defence; no emotional attachment to any thesis

### Soul File Format

- Standard: H1 for file title, H2 for canonical sections, H3 for substructure within sections
- Free-flowing prose within sections (not bullet lists as the primary mode) — character richness matters
- Sections must be stable named anchors for regex-based parsing by ARS Auditor (Phase 19) and Agent Church diff targeting (Phase 17)
- No YAML frontmatter at Phase 15 — deferred until version/weight metadata is genuinely needed
- Extensible: future phases add new H2 sections (e.g., `## Regime Framework`, `## Peer Interfaces`) without breaking parser logic

### Test Directory Structure

- New `tests/core/` directory — mirrors `src/core/` layout
- `tests/core/conftest.py` contains the autouse fixture scoped to soul tests only — no interference with existing 244 tests
- Fixture named `clear_soul_caches` (intent-forward naming) but clears only `load_soul.cache_clear()` in Phase 15
- Future phases extend `clear_soul_caches` explicitly when they introduce new lru_cached soul functions (e.g., `get_soul_summary` in Phase 18)
- Test files: `test_soul_loader.py` (unit), `test_persona_content.py` (content fidelity), `test_macro_analyst_soul.py` (integration)

### Claude's Discretion

- quant_modeler and risk_manager SOUL.md section content (persona seeds established above, full prose at Claude's discretion)
- AXIOM's `## Voice` section wording (measured, probabilistic, institutional tone — Claude drafts)
- AXIOM's `## Report Discipline` / `## Non-Goals` section content
- Exact path-traversal guard implementation in SoulLoader
- SystemMessage injection approach (prepend SystemMessage before agent invocation — synchronous, matches existing `Path.read_text()` pattern)
- Test assertion depth within each test file

</decisions>

<specifics>
## Specific Ideas

- Soul file H2 section structure suggested during discussion: `## Identity`, `## Archetype`, `## Core Beliefs`, `## Drift Guard`, `## Report Discipline`, `## Non-Goals` (with `## Voice`, `## Decision Rules`, `## Output Contract`, `## Workflow` as appropriate per file type)
- conftest.py fixture pattern (user confirmed): named `clear_soul_caches`, clears `load_soul` only, extended explicitly by future phases
- User reasoning on fixture: "Phase-local responsibility — clear only the caches exercised by the current test layer. Avoids import coupling to not-yet-existing functions"
- User reasoning on format: "H2 sections give machine parseability + diff stability + human maintainability. Free prose is for flavor; YAML is unnecessary complexity at this stage"

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets

- `src/graph/models.py:GraphDecision` — `@dataclass(frozen=True)` with `field(default_factory=...)` pattern. Direct template for `AgentSoul` frozen dataclass
- `tests/test_analysts.py:26`, `tests/test_researchers.py:30` — established `autouse=True` fixture pattern for module-level mock clearing. Template for `clear_soul_caches`
- `tests/test_mem03_integration.py:41` — `autouse=True` fixture with before/after yield pattern — exact structure for cache_clear fixture

### Established Patterns

- Lazy LLM init (`_llm = None; def _get_llm(): ...`) — SoulLoader must NOT use this pattern; it's synchronous file I/O, not LLM instantiation
- `operator.add` reducers in `SwarmState` — `system_prompt` and `active_persona` must be plain `Optional[str]` fields with no reducer annotation; confirmed by existing fields like `macro_report`, `risk_approved`
- `src/core/audit_logger.py` — no `AUDIT_EXCLUDED_FIELDS` exists yet; Phase 15 adds this constant and strips fields before serialization in `log_state`

### Integration Points

- `src/graph/state.py:SwarmState` — add `active_persona: Optional[str]` and `system_prompt: Optional[str]` as plain TypedDict fields (no Annotated reducer)
- `src/graph/agents/analysts.py:macro_analyst_node` — inject `SoulLoader.load_soul("macro_analyst")` → write to `state["system_prompt"]` and `state["active_persona"]` before LLM invocation
- `src/graph/agents/analysts.py:quant_modeler_node`, `src/graph/agents/researchers.py` (bullish + bearish) — same injection pattern for all five L2 nodes per SOUL-05
- `src/graph/orchestrator.py` — call `warmup_soul_cache()` at graph creation time (after `build_graph()`)
- `src/core/audit_logger.py` — add `AUDIT_EXCLUDED_FIELDS = {"system_prompt", "active_persona", "soul_sync_context"}` and strip before SHA-256 hashing

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-soul-foundation*
*Context gathered: 2026-03-08*
