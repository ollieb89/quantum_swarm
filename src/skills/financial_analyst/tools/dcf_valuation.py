"""
DCF Valuation Tool

Discounted Cash Flow enterprise and equity valuation with sensitivity analysis.

Features:
- WACC calculation via CAPM
- Revenue and free cash flow projections (5-year default)
- Terminal value via perpetuity growth and exit multiple methods
- Enterprise value and equity value derivation
- Two-way sensitivity analysis (discount rate vs growth rate)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, List, Optional
from utils import math_helpers
from utils import validators


DESCRIPTION = "Discounted Cash Flow enterprise and equity valuation with sensitivity analysis"
REQUIRED_PARAMETERS = ["historical", "assumptions"]
OPTIONAL_PARAMETERS = ["projection_years", "format"]


def calculate_wacc(wacc_inputs: Dict[str, float]) -> float:
    """
    Calculate Weighted Average Cost of Capital using CAPM.

    Args:
        wacc_inputs: Dictionary containing:
            - risk_free_rate: Risk-free rate
            - equity_risk_premium: Market risk premium
            - beta: Beta coefficient
            - cost_of_debt: Cost of debt
            - tax_rate: Corporate tax rate
            - debt_weight: Weight of debt
            - equity_weight: Weight of equity

    Returns:
        WACC as decimal
    """
    # Calculate cost of equity using CAPM
    cost_of_equity = math_helpers.calculate_capm(
        risk_free_rate=wacc_inputs.get("risk_free_rate", 0.04),
        equity_risk_premium=wacc_inputs.get("equity_risk_premium", 0.06),
        beta=wacc_inputs.get("beta", 1.0)
    )

    # Get other inputs
    cost_of_debt = wacc_inputs.get("cost_of_debt", 0.05)
    tax_rate = wacc_inputs.get("tax_rate", 0.25)
    debt_weight = wacc_inputs.get("debt_weight", 0.30)
    equity_weight = wacc_inputs.get("equity_weight", 0.70)

    # Calculate WACC
    wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - tax_rate))

    return wacc


def project_revenue(revenue_history: List[float],
                   growth_rates: List[float],
                   default_growth: float = 0.05) -> List[float]:
    """
    Project future revenue based on growth rates.

    Args:
        revenue_history: Historical revenue values
        growth_rates: List of growth rates for each projection year
        default_growth: Default growth rate if not enough rates provided

    Returns:
        List of projected revenue values
    """
    last_revenue = revenue_history[-1] if revenue_history else 0
    projections = []

    for i, growth_rate in enumerate(growth_rates):
        projected = last_revenue * (1 + growth_rate)
        projections.append(projected)
        last_revenue = projected

    return projections


def project_free_cash_flow(revenue_projections: List[float],
                          fcf_margins: List[float],
                          default_margin: float = 0.10) -> List[float]:
    """
    Project free cash flow based on revenue and margin assumptions.

    Args:
        revenue_projections: Projected revenue values
        fcf_margins: Free cash flow margins for each year
        default_margin: Default margin if not enough margins provided

    Returns:
        List of projected free cash flow values
    """
    fcf_projections = []

    for i, revenue in enumerate(revenue_projections):
        margin = fcf_margins[i] if i < len(fcf_margins) else default_margin
        fcf = revenue * margin
        fcf_projections.append(fcf)

    return fcf_projections


def calculate_terminal_value(last_fcf: float,
                             wacc: float,
                             terminal_growth_rate: float,
                             exit_multiple: float = None,
                             terminal_ebitda_margin: float = None,
                             last_ebitda: float = None) -> Dict[str, float]:
    """
    Calculate terminal value using both perpetuity growth and exit multiple methods.

    Args:
        last_fcf: Last projected free cash flow
        wacc: Weighted average cost of capital
        terminal_growth_rate: Terminal growth rate
        exit_multiple: Exit EV/EBITDA multiple (optional)
        terminal_ebitda_margin: Terminal EBITDA margin (optional)
        last_ebitda: Last EBITDA for exit multiple calculation (optional)

    Returns:
        Dictionary with terminal values from both methods
    """
    # Perpetuity Growth Method
    # TV = FCF * (1 + g) / (WACC - g)
    if wacc > terminal_growth_rate:
        tv_perpetuity = (last_fcf * (1 + terminal_growth_rate)) / (wacc - terminal_growth_rate)
    else:
        tv_perpetuity = 0  # Invalid - growth rate must be less than WACC

    # Exit Multiple Method
    tv_exit_multiple = 0
    if exit_multiple and terminal_ebitda_margin and last_ebitda:
        # Project final year EBITDA
        final_ebitda = last_ebitda * (1 + terminal_growth_rate)
        tv_exit_multiple = final_ebitda * exit_multiple
    elif exit_multiple and last_ebitda:
        tv_exit_multiple = last_ebitda * exit_multiple

    return {
        "perpetuity_growth": tv_perpetuity,
        "exit_multiple": tv_exit_multiple
    }


def calculate_enterprise_value(projected_fcf: List[float],
                               terminal_value: float,
                               wacc: float) -> float:
    """
    Calculate enterprise value by discounting projected FCFs and terminal value.

    Args:
        projected_fcf: List of projected free cash flows
        terminal_value: Terminal value
        wacc: Discount rate

    Returns:
        Enterprise value
    """
    # Discount projected FCFs
    pv_fcf = 0
    for i, fcf in enumerate(projected_fcf, start=1):
        pv_fcf += fcf / ((1 + wacc) ** i)

    # Discount terminal value
    pv_terminal = terminal_value / ((1 + wacc) ** len(projected_fcf))

    return pv_fcf + pv_terminal


def calculate_sensitivity_analysis(wacc: float,
                                   terminal_growth_rate: float,
                                   projected_fcf: List[float],
                                   last_fcf: float,
                                   wacc_range: List[float] = None,
                                   growth_range: List[float] = None) -> Dict[str, Any]:
    """
    Perform two-way sensitivity analysis on WACC and terminal growth rate.

    Args:
        wacc: Base WACC
        terminal_growth_rate: Base terminal growth rate
        projected_fcf: List of projected FCFs
        last_fcf: Last projected FCF
        wacc_range: Range of WACC values to test
        growth_range: Range of growth rates to test

    Returns:
        Dictionary containing sensitivity analysis results
    """
    if wacc_range is None:
        wacc_range = [wacc - 0.02, wacc - 0.01, wacc, wacc + 0.01, wacc + 0.02]

    if growth_range is None:
        growth_range = [terminal_growth_rate - 0.01, terminal_growth_rate - 0.005,
                       terminal_growth_rate, terminal_growth_rate + 0.005,
                       terminal_growth_rate + 0.01]

    # Build enterprise value table
    ev_table = []
    for growth in growth_range:
        row = []
        for rate in wacc_range:
            if rate > growth:
                # Calculate TV with this combination
                tv = (last_fcf * (1 + growth)) / (rate - growth)
                ev = calculate_enterprise_value(projected_fcf, tv, rate)
                row.append(round(ev, 0))
            else:
                row.append(0)  # Invalid combination
        ev_table.append(row)

    # Calculate implied share prices (assuming 10M shares and no net debt)
    shares_outstanding = 10000000  # Default assumption
    share_price_table = []
    for row in ev_table:
        price_row = [round(ev / shares_outstanding, 2) for ev in row]
        share_price_table.append(price_row)

    return {
        "wacc_values": wacc_range,
        "growth_values": growth_range,
        "enterprise_value_table": ev_table,
        "share_price_table": share_price_table
    }


def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute DCF valuation.

    Args:
        parameters: Input parameters containing:
            - historical: Historical financial data
            - assumptions: Valuation assumptions
            - projection_years: Number of projection years (optional)

    Returns:
        Dictionary containing valuation results
    """
    # Validate input
    is_valid, error = validators.validate_dcf_valuation_input(parameters)
    if not is_valid:
        return {"error": error}

    historical = parameters.get("historical", {})
    assumptions = parameters.get("assumptions", {})

    # Extract historical data
    revenue_history = historical.get("revenue", [])
    net_debt = historical.get("net_debt", 0)
    shares_outstanding = historical.get("shares_outstanding", 10000000)

    # Extract assumptions
    projection_years = parameters.get("projection_years") or assumptions.get("projection_years", 5)
    revenue_growth_rates = assumptions.get("revenue_growth_rates", [0.05] * projection_years)
    fcf_margins = assumptions.get("fcf_margins", [0.10] * projection_years)
    default_revenue_growth = assumptions.get("default_revenue_growth", 0.05)
    default_fcf_margin = assumptions.get("default_fcf_margin", 0.10)
    terminal_growth_rate = assumptions.get("terminal_growth_rate", 0.025)
    terminal_ebitda_margin = assumptions.get("terminal_ebitda_margin", 0.20)
    exit_ev_ebitda_multiple = assumptions.get("exit_ev_ebitda_multiple", 12.0)
    wacc_inputs = assumptions.get("wacc_inputs", {})

    # Calculate WACC
    wacc = calculate_wacc(wacc_inputs)

    # Project revenue
    projected_revenue = project_revenue(
        revenue_history,
        revenue_growth_rates[:projection_years],
        default_revenue_growth
    )

    # Project free cash flow
    projected_fcf = project_free_cash_flow(
        projected_revenue,
        fcf_margins[:projection_years],
        default_fcf_margin
    )

    # Calculate terminal value
    last_fcf = projected_fcf[-1]
    terminal_value = calculate_terminal_value(
        last_fcf,
        wacc,
        terminal_growth_rate,
        exit_ev_ebitda_multiple,
        terminal_ebitda_margin,
        None  # We don't have EBITDA, so use simplified exit multiple
    )

    # Calculate enterprise value
    enterprise_value_perpetuity = calculate_enterprise_value(
        projected_fcf,
        terminal_value["perpetuity_growth"],
        wacc
    )

    enterprise_value_exit = calculate_enterprise_value(
        projected_fcf,
        terminal_value["exit_multiple"],
        wacc
    )

    # Calculate equity value (EV - Net Debt)
    equity_value_perpetuity = enterprise_value_perpetuity - net_debt
    equity_value_exit = enterprise_value_exit - net_debt

    # Calculate value per share
    value_per_share_perpetuity = math_helpers.safe_divide(equity_value_perpetuity, shares_outstanding)
    value_per_share_exit = math_helpers.safe_divide(equity_value_exit, shares_outstanding)

    # Perform sensitivity analysis
    sensitivity = calculate_sensitivity_analysis(
        wacc,
        terminal_growth_rate,
        projected_fcf,
        last_fcf
    )

    # Build results
    results = {
        "wacc": round(wacc, 4),
        "projected_revenue": [round(r, 0) for r in projected_revenue],
        "projected_fcf": [round(f, 0) for f in projected_fcf],
        "terminal_value": {
            "perpetuity_growth": round(terminal_value["perpetuity_growth"], 0),
            "exit_multiple": round(terminal_value["exit_multiple"], 0)
        },
        "enterprise_value": {
            "perpetuity_growth": round(enterprise_value_perpetuity, 0),
            "exit_multiple": round(enterprise_value_exit, 0)
        },
        "equity_value": {
            "perpetuity_growth": round(equity_value_perpetuity, 0),
            "exit_multiple": round(equity_value_exit, 0)
        },
        "value_per_share": {
            "perpetuity_growth": round(value_per_share_perpetuity, 2),
            "exit_multiple": round(value_per_share_exit, 2)
        },
        "sensitivity_analysis": sensitivity,
        "assumptions": {
            "projection_years": projection_years,
            "terminal_growth_rate": terminal_growth_rate,
            "exit_ev_ebitda_multiple": exit_ev_ebitda_multiple,
            "wacc_inputs": wacc_inputs
        }
    }

    return results


# For direct CLI execution
if __name__ == "__main__":
    import json

    # Example usage with sample data
    sample_data = {
        "historical": {
            "revenue": [38000000, 42000000, 45000000, 48000000, 50000000],
            "net_income": [3800000, 4200000, 4500000, 5000000, 5500000],
            "net_debt": 7000000,
            "shares_outstanding": 10000000
        },
        "assumptions": {
            "projection_years": 5,
            "revenue_growth_rates": [0.10, 0.09, 0.08, 0.07, 0.06],
            "fcf_margins": [0.12, 0.13, 0.13, 0.14, 0.14],
            "default_revenue_growth": 0.05,
            "default_fcf_margin": 0.10,
            "terminal_growth_rate": 0.025,
            "terminal_ebitda_margin": 0.20,
            "exit_ev_ebitda_multiple": 12.0,
            "wacc_inputs": {
                "risk_free_rate": 0.04,
                "equity_risk_premium": 0.06,
                "beta": 1.1,
                "cost_of_debt": 0.055,
                "tax_rate": 0.25,
                "debt_weight": 0.30,
                "equity_weight": 0.70
            }
        }
    }

    result = execute(sample_data)
    print(json.dumps(result, indent=2))
