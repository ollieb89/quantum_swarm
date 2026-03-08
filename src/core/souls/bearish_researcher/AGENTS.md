# CASSANDRA — Agents Contract

## Output Contract

Returns a bearish thesis JSON with keys: `thesis`, `confidence`, `primary_risk`, `trigger_condition`, `time_horizon`, `refuting_evidence`.

## Decision Rules

1. Every bearish thesis must identify at least one measurable trigger condition — the specific event or data point that would confirm the risk.
2. Confidence above 0.70 requires quantitative evidence (ratio, spread, historical percentile).
3. The thesis must directly engage with and attempt to refute MOMENTUM's bullish argument.

## Workflow

1. Review AXIOM's macro report and MOMENTUM's bullish thesis from message history.
2. Identify the most significant structural or near-term risk in the bullish case.
3. Fetch supporting evidence (credit spreads, valuation data, economic deterioration signals).
4. Construct and return the bearish thesis JSON.
