# GUARDIAN — Agents Contract

## Output Contract

Returns a risk approval JSON with mandatory keys: `approved` (bool), `risk_score` (float in [0, 1]), `portfolio_heat` (float), `notes` (string — rejection reason or "Within all constraints").

## Decision Rules

1. Reject immediately if the trade proposal lacks a calculated stop_loss field.
2. Reject if portfolio_heat after adding this position would exceed 0.80 of total capital at risk.
3. Reject if the position size would result in a single-trade maximum loss exceeding 2% of total portfolio value.
4. Approvals require all three conditions to be satisfied simultaneously, not just one.

## Workflow

1. Extract the trade proposal from the upstream state.
2. Calculate portfolio_heat: sum of all open position risk as a fraction of total capital.
3. Verify stop_loss is present and calculated correctly (within 5% tolerance of ATR-based formula).
4. Return the risk approval JSON with all mandatory keys.
