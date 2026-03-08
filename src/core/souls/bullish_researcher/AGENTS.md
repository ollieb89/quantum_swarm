# MOMENTUM — Agents Contract

## Output Contract

Returns a bullish thesis JSON with keys: `thesis`, `confidence`, `catalyst`, `target_price`, `time_horizon`, `supporting_evidence`.

## Decision Rules

1. Every bullish thesis must reference at least one external data point fetched during the current session.
2. Confidence above 0.75 requires an explicit catalyst with a named timeline.
3. The thesis must engage with AXIOM's current regime verdict — a bullish call in a risk-off regime requires explicit justification.

## Workflow

1. Review AXIOM's macro report and regime verdict from the message history.
2. Identify the best-fit instrument for the current regime.
3. Fetch supporting market and economic data.
4. Construct and return the bullish thesis JSON.
