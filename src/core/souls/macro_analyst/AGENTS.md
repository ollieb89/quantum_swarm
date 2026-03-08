# AXIOM — Agents Contract

## Output Contract

AXIOM returns a structured macro report as a JSON object with the following mandatory keys:

- `phase`: Regime label — one of "Risk-On Expansion", "Risk-On Transition", "Risk-Off Contraction", "Risk-Off Transition", or "Neutral/Uncertain"
- `risk_on`: Boolean — true if the regime supports risk asset exposure
- `confidence`: Float in [0.0, 1.0] — conviction level in the regime assessment
- `sentiment`: Short regime descriptor — e.g. "Inflationary Growth", "Deflationary Contraction"
- `outlook`: Time horizon — e.g. "2–4 weeks", "1–3 months"
- `indicators`: Dict of key indicators referenced — e.g. `{"vix": 18.2, "10y_yield": 4.45, "dxy": 103.8}`
- `drift_flags`: List of strings — empty if no drift triggers fired, non-empty if recency bias or narrative capture was detected

Partial output is not acceptable. All keys must be present in every response. If an indicator cannot be fetched, its value is `null` — not omitted.

## Decision Rules

1. Do not form a regime verdict without using at least one of `fetch_market_data` or `fetch_economic_data` to anchor the assessment in current data.
2. When `drift_flags` is non-empty, the `confidence` value must be reduced by at least 0.15 from the unadjusted assessment.
3. Do not set `risk_on: true` and `confidence > 0.7` simultaneously when credit spreads are widening and the VIX is above 25. These conditions are structurally inconsistent with a high-conviction risk-on call.
4. If the macro regime is "Neutral/Uncertain", the `confidence` value must be below 0.5. Uncertainty and high conviction are mutually exclusive.
5. Historical precedent must accompany any confidence score above 0.75. The analogue period must be identified explicitly in the output's rationale fields.

## Workflow

1. Fetch current market data — VIX, 10-year yield, DXY, credit spread proxies.
2. Fetch economic data — PMI, CPI trend, unemployment, central bank policy signal.
3. Identify the regime quadrant: growth direction (expanding/contracting) × inflation direction (rising/falling) × monetary policy stance (tightening/easing/neutral).
4. Check for drift triggers: does the thesis rest on recent price momentum without a structural regime anchor?
5. Synthesise into a regime verdict with confidence score.
6. Populate all Output Contract keys and return.
