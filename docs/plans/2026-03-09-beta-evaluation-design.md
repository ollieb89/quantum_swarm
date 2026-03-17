# Beta Evaluation Design: Structured Confidence Check

**Date:** 2026-03-09
**Milestone:** Post v1.4 (Beta: Observable Swarm)
**Status:** Approved — ready for implementation

## Purpose

Validate the swarm's cognitive pipeline before paper trading. Confirm that agents debate adversarially, risk gates have teeth, and personas stay in character across 30 cycles.

## Run Matrix

| Asset | Cycles | Purpose |
|-------|--------|---------|
| BTC   | 10     | Baseline calibration (familiar, high liquidity) |
| ETH   | 10     | Cross-asset consistency check |
| SOL   | 10     | High-beta stress test for risk gating |

- **Mode:** paper
- **Total cycles:** 30
- **Estimated API calls:** ~900 (Gemini 2.0 Flash)

## Scoring Dimensions (priority order)

### 1. Consensus Friction

Measures whether agents actually disagree before converging.

- **Metric:** σ(initial conviction scores) across 4 L2 agents
- **Post-debate delta:** |mean_initial - final_consensus|
- **Outlier triggers:**
  - Friction < 0.1 → Echo Chamber (agents agree too easily)
  - High friction + low delta → Bully Agent (one agent steamrolling)

### 2. Risk Gating

Measures whether guards catch what they should.

- **Metrics:**
  - `block_rate` — fraction of cycles where trade was rejected
  - `block_reasons` — categorized (exposure, concentration, drawdown, low conviction)
  - `false_positive_flag` — blocked trade where consensus_score > 0.8
  - `pass_through_flag` — approved trade where any agent had conviction < 0.3
- **SOL-specific concern:** high-leverage pass-throughs on high-beta assets

### 3. Persona Fidelity

Measures whether each agent stays in character.

- **Method:** Keyword signature vectors per persona
  - AXIOM: "regime", "macro", "cycle", "structural", "fiscal", "monetary"
  - MOMENTUM: "flow", "momentum", "breakout", "accumulation", "trend", "volume"
  - CASSANDRA: "tail", "hedge", "downside", "contagion", "liquidation", "systemic"
  - SIGMA: "volatility", "correlation", "skew", "quantile", "variance", "distribution"
- **Score:** Cosine similarity between actual keyword frequency and expected signature
- **Outlier triggers:**
  - Cosine sim < 0.5 → Persona Drift
  - Cross-contamination: agent's top keyword belongs to another persona's cluster
  - Sentiment-polarity breach: CASSANDRA with conviction > 0.8 (permabear going bullish)

### 4. Merit Drift

Tracks KAMI score trends across a 10-cycle asset run.

- **Metric:** Per-agent KAMI delta from cycle 1 to cycle 10
- **Outlier trigger:** Monotonic decay > 0.2 over the run
- **Significance:** Systematic merit decay suggests bias against that agent's role

## Script Architecture

**File:** `scripts/run_evaluation.py` (~200 lines, standalone)

### CLI Commands

```bash
# Run full evaluation batch
python scripts/run_evaluation.py run

# Re-score existing batch without re-running cycles
python scripts/run_evaluation.py score data/evaluations/2026-03-09-eval.jsonl

# Print report from scored data
python scripts/run_evaluation.py report data/evaluations/2026-03-09-eval.jsonl
```

### Phase 1: Run Cycles

- Loops through assets × cycles, calling existing `CycleRunner`
- 1-second sleep between cycles for rate limit headroom
- Exponential backoff retry (3 attempts) on transient Gemini errors
- Incremental JSONL writes (no data loss on crash)
- Per-cycle metadata: `{asset, cycle_id, timestamp, soul_versions}`

### Phase 2: Score

Three scorer functions + merit drift tracker:

- `score_consensus_friction(cycle)` → friction, delta, bully_flag
- `score_risk_gates(cycle)` → block_rate, reasons, false_positive, pass_through
- `score_persona_fidelity(cycle)` → per-agent cosine sim, contamination flags, polarity breach
- `track_merit_drift(cycles_for_asset)` → per-agent trend, decay alerts

### Phase 3: Report

Rich terminal output:

- Per-asset summary table (averages + ranges)
- Outlier list with reason codes
- Top 3 deep-dive recommendations with `replay show <cycle_id>` commands
- Bully agent + persona breach alerts
- Merit drift sparklines per agent

## Storage

- **Raw + scored data:** `data/evaluations/YYYY-MM-DD-eval.jsonl`
- **Format:** JSON Lines (one object per cycle, append-safe)
- **Metadata key:** captures soul versions and agent temperatures for reproducibility

## Known Limitations (acceptable for v1)

- KAMI Accuracy frozen at 0.5 — 30% of merit weight is inert. Will document impact.
- Keyword-based fidelity is a proxy — proper PersonaScore (SOUL-09) is deferred.
- 10 cycles per asset is directional, not statistically conclusive.
- ARS drift auditor needs 30 cycles warm-up per agent — won't trigger during evaluation.

## Success Criteria

| Outcome | Interpretation |
|---------|---------------|
| Friction consistently > 0.1, no bully flags | Adversarial debate is working |
| Block rate > 0 for SOL, reasons are sensible | Risk gates have teeth |
| All persona cosine sims > 0.5, no polarity breaches | Agents stay in character |
| No monotonic merit decay > 0.2 | System isn't biased against any role |
| At least 1 outlier found | The detection logic is sensitive enough |

## Next Steps

1. Implement `scripts/run_evaluation.py`
2. Run the 30-cycle batch
3. Review report, deep-dive outliers via Replay CLI
4. Decide: fix issues found, or proceed to paper trading
