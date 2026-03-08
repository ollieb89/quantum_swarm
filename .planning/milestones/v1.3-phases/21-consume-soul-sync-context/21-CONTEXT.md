# Phase 21: Consume Soul-Sync Context in Debate - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

`debate_synthesizer` reads `soul_sync_context` from SwarmState so peer soul summaries actually influence debate synthesis, completing the Theory of Mind data flow. Closes INT-02 (soul_sync_context orphaned output) from v1.3 audit. No new SwarmState fields. No LLM calls added. No score formula changes.

</domain>

<decisions>
## Implementation Decisions

### Influence Mechanism
- Peer soul summaries **enrich `debate_history` only** — they do not change consensus weighting math
- KAMI merit remains the sole influence on `weighted_consensus_score` (Phase 16 decision preserved)
- Soul summaries are interpretive context, not earned performance — they belong in provenance, not in scoring
- Each `debate_history` entry gains an optional `peer_soul_summary` field containing the **opponent's** public soul summary
  - Bullish entry gets CASSANDRA's summary (what does the bear believe?)
  - Bearish entry gets MOMENTUM's summary (what does the bull believe?)
- Field is a flat optional key on the existing entry dict — no nested `context` sub-dict

### DebateSynthesizer Stays No-LLM
- DebateSynthesizer remains a **pure aggregation step** with zero LLM calls
- Soul summaries are read from `state["soul_sync_context"]` and embedded into debate_history entries — deterministic dict enrichment only
- No token cost, no latency added, no API failure risk introduced
- Rule: agent nodes do cognition, DebateSynthesizer does aggregation

### Opponent Mapping (Inline)
- `_OPPONENT_MAP` dict mapping `_BULLISH_SOURCE → "CASSANDRA"` and `_BEARISH_SOURCE → "MOMENTUM"` lives **inside `debate.py`**
- Not extracted to `kami.py` — this is presentation-adjacent logic, not merit logic
- ~3 lines, used only by DebateSynthesizer

### Absent/Empty Handling
- **Omit `peer_soul_summary` field entirely** when no meaningful summary exists
- `soul_sync_context` is `None` → field omitted from all entries
- Opponent summary is empty string → field omitted from that entry
- **No distinction** between `None` context and empty summaries — both result in omission
- No warnings logged — absence is a normal state
- Neutral placeholder entry (no researchers ran) never gets soul context — soul context only attaches to real agent turns
- Result: when soul_sync_context is present, debate output demonstrably differs (entries have `peer_soul_summary`); when absent, output is identical to pre-Phase 21

### No State Passthrough
- DebateSynthesizer does NOT return `soul_sync_context` in its output dict
- Context goes in, artifacts come out — `soul_sync_context` is input context, `debate_history` is output artifact
- Downstream nodes access soul summaries via `debate_history[i]["peer_soul_summary"]` if needed

### Downstream Consumers
- `decision_card_writer` already serializes `debate_history` — `peer_soul_summary` flows into decision card audit trail automatically
- No downstream node reads `peer_soul_summary` for control logic in Phase 21
- `risk_manager` ignores it — future phases can consume if needed

### Claude's Discretion
- Exact test structure and organization
- Whether to add a lightweight INFO log line noting soul context was consumed
- Helper function naming (`_peer_summary_for` or inline conditional)
- Any additional test edge cases beyond the core present/absent comparison

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/graph/debate.py` — `DebateSynthesizer` function (~160 lines), `_extract_researcher_text()` helper, `_BULLISH_SOURCE`/`_BEARISH_SOURCE` constants
- `src/graph/nodes/soul_sync_handshake.py` — produces `{"soul_sync_context": {"MOMENTUM": "<summary>", "CASSANDRA": "<summary>"}}` upstream
- `src/core/kami.py` — `RESEARCHER_HANDLE_MAP`, `DEFAULT_MERIT` (already imported by debate.py)
- `tests/test_adversarial_debate.py` — existing debate synthesizer tests to extend

### Established Patterns
- **No-LLM aggregation nodes:** DebateSynthesizer, soul_sync_handshake_node — pure dict manipulation
- **Optional field omission:** sparse dict entries (only include key if value is meaningful) — consistent with drift flags pattern
- **AUDIT_EXCLUDED_FIELDS:** `soul_sync_context` already in exclusion set (Phase 17 prep) — no audit changes needed
- **debate_history schema:** `{source, hypothesis, evidence, strength}` — extend with optional `peer_soul_summary`

### Integration Points
- `src/graph/debate.py:DebateSynthesizer()` — read `state["soul_sync_context"]`, enrich debate_history entries with `peer_soul_summary`
- `src/graph/debate.py` — add `_OPPONENT_MAP` module constant
- `tests/test_adversarial_debate.py` — add tests: soul context present → field exists; soul context absent → field absent; score unchanged in both cases

</code_context>

<specifics>
## Specific Ideas

- The change to `debate.py` is ~10 lines: read soul_sync_context from state, look up opponent handle, conditionally add `peer_soul_summary` to each debate_history entry
- Success criteria test: `assert result["debate_history"][0]["peer_soul_summary"] != ""` when context present; `assert "peer_soul_summary" not in result["debate_history"][0]` when absent; `assert score_with == score_without`
- `peer_soul_summary` means "this agent's compact model of the other side" — the word "peer" refers to the opponent participant
- decision_card_writer preserves peer_soul_summary automatically through debate_history serialization — no code change needed there

</specifics>

<deferred>
## Deferred Ideas

- LLM-based synthesis that reasons about soul context to produce richer narrative — add as a separate downstream presenter/explainer module if needed, not inside DebateSynthesizer
- `soul_alignment_score` as a separate SwarmState field — only add if explicit telemetry or offline analysis is needed
- Downstream risk_manager consuming peer_soul_summary for gating decisions — future phase if soul-aware risk logic is desired
- Nested `context` sub-dict in debate_history for future extensibility — premature; flat optional field is sufficient for now

</deferred>

---

*Phase: 21-consume-soul-sync-context*
*Context gathered: 2026-03-08*
