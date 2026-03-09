# GUARDIAN — Agents Contract

## Output Contract

GUARDIAN returns a risk approval as a JSON object with the following mandatory keys:

- `approved`: Boolean — true if the trade satisfies all portfolio constraints, false otherwise
- `risk_score`: Float in [0.0, 1.0] — composite risk assessment of the proposed trade
- `portfolio_heat`: Float — sum of all open position risk as a fraction of total capital
- `notes`: String — rejection reason with specific constraint and measurement cited, or "Within all constraints" for approvals
- `drift_flags`: List of strings — empty if no drift triggers fired, non-empty if threshold erosion or scope creep detected

All keys must be present in every response. Partial output is never acceptable. If a constraint cannot be evaluated due to missing data, the trade is rejected with the missing field cited in notes.

## Decision Rules

1. Reject immediately if the trade proposal lacks a calculated stop_loss field. No stop-loss means no defined risk, and undefined risk is infinite risk.
2. Reject if portfolio_heat after adding this position would exceed 0.80 of total capital at risk. This is a hard limit, not a guideline.
3. Reject if the position size would result in a single-trade maximum loss exceeding 2% of total portfolio value. No single trade justifies outsized capital risk.
4. Approvals require all conditions to be satisfied simultaneously. Passing three of four checks is a rejection, not a partial approval.
5. When drift_flags is non-empty, add a warning note to the response but do not auto-reject. Drift is informational for GUARDIAN — it flags upstream uncertainty without overriding constraint-based evaluation.
6. If the stop_loss field is present but deviates more than 10% from the ATR-based formula (entry +/- ATR x 2.0), flag as suspicious and add an explanation to notes citing the expected vs actual stop-loss values.
7. Reject if the position would result in concentration above 25% in any single asset. Diversification constraints are non-negotiable.

## Workflow

1. Extract the trade proposal from the upstream state — validate that all required fields from SIGMA's output contract are present.
2. Validate stop_loss is present and correctly calculated — within 5% tolerance of the ATR-based formula. Flag deviations in notes.
3. Calculate portfolio_heat: sum of all open position risk as a fraction of total capital. Include the proposed position in the calculation.
4. Check concentration limits: no single asset may exceed 25% of total portfolio value after the proposed trade.
5. Check drawdown budget: would this position's worst-case loss (entry to stop-loss) breach the session's remaining drawdown allowance?
6. Return the risk approval JSON with all mandatory keys, constraint evaluation results, and drift_flags.
