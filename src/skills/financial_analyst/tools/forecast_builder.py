"""
Forecast Builder Tool

Driver-based revenue forecasting with rolling cash flow projection and scenario modeling.

Features:
- Driver-based revenue forecast model
- 13-week rolling cash flow projection
- Scenario modeling (base/bull/bear cases)
- Trend analysis using simple linear regression
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, List, Optional
from utils import math_helpers
from utils import validators


DESCRIPTION = "Driver-based revenue forecasting with rolling cash flow and scenario modeling"
REQUIRED_PARAMETERS = ["historical_periods"]
OPTIONAL_PARAMETERS = ["drivers", "assumptions", "scenarios", "cash_flow_inputs", "forecast_periods"]


def calculate_trend_analysis(historical_periods: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Perform trend analysis on historical data.

    Args:
        historical_periods: List of historical period data

    Returns:
        Dictionary with trend analysis results
    """
    # Extract revenue values
    revenues = [period.get("revenue", 0) for period in historical_periods]

    if len(revenues) < 2:
        return {
            "trend": {
                "slope": 0,
                "intercept": revenues[0] if revenues else 0,
                "r_squared": 0,
                "direction": "stable"
            },
            "average_growth_rate": 0,
            "seasonality_index": []
        }

    # Calculate linear regression
    slope, intercept, r_squared = math_helpers.calculate_linear_regression(revenues)

    # Determine trend direction
    if slope > 0:
        direction = "upward"
    elif slope < 0:
        direction = "downward"
    else:
        direction = "stable"

    # Calculate average growth rate
    avg_growth = math_helpers.calculate_average_growth_rate(revenues)

    # Calculate seasonality index (quarterly)
    # Group by quarter (assuming data is quarterly)
    n_periods = len(historical_periods)
    if n_periods >= 4:
        # Simple seasonality: average of periods in same position
        num_quarters = min(4, n_periods)
        quarterly_totals = [0] * num_quarters
        quarterly_counts = [0] * num_quarters

        for i, revenue in enumerate(revenues):
            quarter_idx = i % num_quarters
            quarterly_totals[quarter_idx] += revenue
            quarterly_counts[quarter_idx] += 1

        # Calculate average for each quarter position
        quarterly_avgs = [totals / count if count > 0 else 0
                        for totals, count in zip(quarterly_totals, quarterly_counts)]

        # Calculate overall average
        overall_avg = sum(revenues) / len(revenues)

        # Calculate seasonality index (ratio to average)
        seasonality = [avg / overall_avg if overall_avg > 0 else 1.0
                     for avg in quarterly_avgs]
    else:
        seasonality = []

    return {
        "trend": {
            "slope": round(slope, 0),
            "intercept": round(intercept, 0),
            "r_squared": round(r_squared, 4),
            "direction": direction
        },
        "average_growth_rate": round(avg_growth, 4),
        "seasonality_index": [round(s, 2) for s in seasonality]
    }


def project_revenue_driver_based(historical_periods: List[Dict[str, Any]],
                                  drivers: Dict[str, Any],
                                  assumptions: Dict[str, Any],
                                  num_periods: int) -> List[Dict[str, Any]]:
    """
    Project revenue using driver-based model.

    Args:
        historical_periods: Historical period data
        drivers: Revenue drivers (units, pricing)
        assumptions: Assumptions (growth rate, margins)
        num_periods: Number of periods to forecast

    Returns:
        List of projected periods
    """
    # Get last period values
    last_period = historical_periods[-1]
    last_revenue = last_period.get("revenue", 0)
    last_gross_profit = last_period.get("gross_profit", 0)
    last_operating_income = last_period.get("operating_income", 0)

    # Calculate historical gross margin and operating margin
    gross_margin = math_helpers.safe_divide(last_gross_profit, last_revenue) if last_revenue > 0 else assumptions.get("gross_margin", 0.40)
    operating_margin = math_helpers.safe_divide(last_operating_income, last_revenue) if last_revenue > 0 else assumptions.get("gross_margin", 0.40) - assumptions.get("opex_pct_revenue", 0.25)

    # Get assumptions
    base_growth_rate = assumptions.get("revenue_growth_rate", 0.08)
    base_gross_margin = assumptions.get("gross_margin", gross_margin)
    base_opex_pct = assumptions.get("opex_pct_revenue", 0.25)

    # Get drivers if provided
    units_data = drivers.get("units", {})
    pricing_data = drivers.get("pricing", {})

    base_units = units_data.get("base_units", 0)
    units_growth = units_data.get("growth_rate", 0)
    base_price = pricing_data.get("base_price", 0)
    price_increase = pricing_data.get("annual_increase", 0)

    projections = []
    current_revenue = last_revenue

    # Determine if using driver-based or simple growth
    use_driver_based = base_units > 0 and base_price > 0

    for i in range(num_periods):
        if use_driver_based:
            # Driver-based projection
            units = base_units * ((1 + units_growth) ** (i + 1))
            price = base_price * ((1 + price_increase) ** (i + 1))
            projected_revenue = units * price

            # Adjust for growth assumption
            growth_factor = (1 + base_growth_rate) ** (i + 1)
            projected_revenue *= growth_factor
        else:
            # Simple growth projection
            projected_revenue = current_revenue * (1 + base_growth_rate)

        # Calculate gross profit and operating income
        projected_gross_profit = projected_revenue * base_gross_margin
        projected_opex = projected_revenue * base_opex_pct
        projected_operating_income = projected_gross_profit - projected_opex

        # Calculate quarter indicator
        quarter = (i % 4) + 1
        year = 2025 + (i // 4) + 1

        projections.append({
            "period": f"Q{quarter} {year}",
            "revenue": round(projected_revenue, 0),
            "gross_profit": round(projected_gross_profit, 0),
            "operating_income": round(projected_operating_income, 0),
            "growth_rate": base_growth_rate
        })

        current_revenue = projected_revenue

    return projections


def project_scenarios(historical_periods: List[Dict[str, Any]],
                     assumptions: Dict[str, Any],
                     scenarios: Dict[str, Any],
                     num_periods: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Project revenue under different scenarios.

    Args:
        historical_periods: Historical period data
        assumptions: Base assumptions
        scenarios: Scenario definitions (base, bull, bear)
        num_periods: Number of periods to forecast

    Returns:
        Dictionary with projections for each scenario
    """
    last_revenue = historical_periods[-1].get("revenue", 0)
    base_growth = assumptions.get("revenue_growth_rate", 0.08)
    base_margin = assumptions.get("gross_margin", 0.40)

    scenario_projections = {}

    for scenario_name, scenario_adj in scenarios.items():
        growth_adjustment = scenario_adj.get("growth_adjustment", 0)
        margin_adjustment = scenario_adj.get("margin_adjustment", 0)

        adjusted_growth = base_growth + growth_adjustment
        adjusted_margin = base_margin + margin_adjustment

        projections = []
        current_revenue = last_revenue
        total_revenue = 0

        for i in range(num_periods):
            current_revenue = current_revenue * (1 + adjusted_growth)
            gross_profit = current_revenue * adjusted_margin

            quarter = (i % 4) + 1
            year = 2025 + (i // 4) + 1

            projections.append({
                "period": f"Q{quarter} {year}",
                "revenue": round(current_revenue, 0),
                "gross_profit": round(gross_profit, 0)
            })

            total_revenue += current_revenue

        scenario_projections[scenario_name] = {
            "projections": projections,
            "total_revenue": round(total_revenue, 0),
            "growth_rate": adjusted_growth
        }

    return scenario_projections


def calculate_rolling_cash_flow(cash_flow_inputs: Dict[str, Any],
                                weeks: int = 13) -> Dict[str, Any]:
    """
    Calculate 13-week rolling cash flow projection.

    Args:
        cash_flow_inputs: Cash flow input parameters
        weeks: Number of weeks to project (default: 13)

    Returns:
        Dictionary with cash flow projections
    """
    # Extract inputs
    opening_cash = cash_flow_inputs.get("opening_cash_balance", 0)
    weekly_revenue = cash_flow_inputs.get("weekly_revenue", 0)
    collection_rate = cash_flow_inputs.get("collection_rate", 0.85)
    collection_lag = cash_flow_inputs.get("collection_lag_weeks", 2)
    weekly_payroll = cash_flow_inputs.get("weekly_payroll", 0)
    weekly_rent = cash_flow_inputs.get("weekly_rent", 0)
    weekly_operating = cash_flow_inputs.get("weekly_operating", 0)
    weekly_other = cash_flow_inputs.get("weekly_other", 0)
    one_time_items = cash_flow_inputs.get("one_time_items", [])

    # Build weekly projections
    weekly_projections = []
    current_cash = opening_cash

    # Create lookup for one-time items
    one_time_dict = {item.get("week"): item for item in one_time_items}

    total_inflows = 0
    total_outflows = 0
    min_balance = current_cash
    min_balance_week = 1

    for week in range(1, weeks + 1):
        # Calculate cash inflows (revenue collected)
        # Revenue from 'weeks - collection_lag' weeks ago becomes available
        if week > collection_lag:
            cash_inflow = weekly_revenue * collection_rate
        else:
            cash_inflow = 0

        # Calculate cash outflows
        cash_outflow = weekly_payroll + weekly_rent + weekly_operating + weekly_other

        # Add one-time items
        if week in one_time_dict:
            cash_outflow += one_time_dict[week].get("amount", 0)

        # Calculate net change
        net_change = cash_inflow - cash_outflow

        # Update cash balance
        current_cash += net_change

        # Track minimum
        if current_cash < min_balance:
            min_balance = current_cash
            min_balance_week = week

        # Track totals
        if cash_inflow > 0:
            total_inflows += cash_inflow
        if cash_outflow > 0:
            total_outflows += cash_outflow

        weekly_projections.append({
            "week": week,
            "opening_balance": round(current_cash - net_change, 0),
            "inflows": round(cash_inflow, 0),
            "outflows": round(cash_outflow, 0),
            "net_change": round(net_change, 0),
            "closing_balance": round(current_cash, 0)
        })

    # Calculate cash runway
    # Average weekly outflow
    avg_weekly_outflow = total_outflows / weeks if weeks > 0 else 0
    cash_runway = current_cash / avg_weekly_outflow if avg_weekly_outflow > 0 else float("inf")

    return {
        "weeks": weeks,
        "opening_balance": opening_cash,
        "closing_balance": round(current_cash, 0),
        "total_inflows": round(total_inflows, 0),
        "total_outflows": round(total_outflows, 0),
        "minimum_balance": round(min_balance, 0),
        "minimum_balance_week": min_balance_week,
        "cash_runway_weeks": round(cash_runway, 1),
        "weekly_projections": weekly_projections
    }


def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute forecast builder.

    Args:
        parameters: Input parameters containing:
            - historical_periods: Historical period data
            - drivers: Revenue drivers (optional)
            - assumptions: Forecast assumptions (optional)
            - scenarios: Scenario definitions (optional)
            - cash_flow_inputs: Cash flow inputs (optional)
            - forecast_periods: Number of periods to forecast (optional)

    Returns:
        Dictionary containing forecast results
    """
    # Validate input
    is_valid, error = validators.validate_forecast_input(parameters)
    if not is_valid:
        return {"error": error}

    historical_periods = parameters.get("historical_periods", [])
    drivers = parameters.get("drivers", {})
    assumptions = parameters.get("assumptions", {})
    scenarios = parameters.get("scenarios", {})
    cash_flow_inputs = parameters.get("cash_flow_inputs", {})
    forecast_periods = parameters.get("forecast_periods", assumptions.get("forecast_periods", 12))

    # Perform trend analysis
    trend_analysis = calculate_trend_analysis(historical_periods)

    # Generate base case projection
    if drivers or assumptions:
        revenue_forecast = project_revenue_driver_based(
            historical_periods, drivers, assumptions, forecast_periods
        )
    else:
        revenue_forecast = []

    # Generate scenario projections
    scenario_projections = {}
    if scenarios:
        scenario_projections = project_scenarios(
            historical_periods, assumptions, scenarios, forecast_periods
        )

    # Calculate rolling cash flow if inputs provided
    rolling_cash_flow = {}
    if cash_flow_inputs:
        rolling_cash_flow = calculate_rolling_cash_flow(cash_flow_inputs)

    # Build results
    results = {
        "trend_analysis": trend_analysis,
        "revenue_forecast": revenue_forecast,
        "scenario_comparison": {
            "comparison": [
                {
                    "scenario": name,
                    "total_revenue": data.get("total_revenue", 0),
                    "growth_rate": data.get("growth_rate", 0)
                }
                for name, data in scenario_projections.items()
            ]
        } if scenario_projections else {},
        "rolling_cash_flow": rolling_cash_flow
    }

    return results


# For direct CLI execution
if __name__ == "__main__":
    import json

    # Example usage with sample data
    sample_data = {
        "historical_periods": [
            {"period": "Q1 2024", "revenue": 10500000, "gross_profit": 4200000, "operating_income": 1575000},
            {"period": "Q2 2024", "revenue": 11200000, "gross_profit": 4480000, "operating_income": 1680000},
            {"period": "Q3 2024", "revenue": 11800000, "gross_profit": 4720000, "operating_income": 1770000},
            {"period": "Q4 2024", "revenue": 12500000, "gross_profit": 5000000, "operating_income": 1875000},
            {"period": "Q1 2025", "revenue": 12800000, "gross_profit": 5120000, "operating_income": 1920000},
            {"period": "Q2 2025", "revenue": 13500000, "gross_profit": 5400000, "operating_income": 2025000},
            {"period": "Q3 2025", "revenue": 14100000, "gross_profit": 5640000, "operating_income": 2115000},
            {"period": "Q4 2025", "revenue": 15700000, "gross_profit": 6280000, "operating_income": 2355000}
        ],
        "drivers": {
            "units": {
                "base_units": 5000,
                "growth_rate": 0.04
            },
            "pricing": {
                "base_price": 2800,
                "annual_increase": 0.03
            }
        },
        "assumptions": {
            "revenue_growth_rate": 0.08,
            "gross_margin": 0.40,
            "opex_pct_revenue": 0.25,
            "forecast_periods": 12
        },
        "scenarios": {
            "base": {
                "growth_adjustment": 0.0,
                "margin_adjustment": 0.0
            },
            "bull": {
                "growth_adjustment": 0.04,
                "margin_adjustment": 0.03
            },
            "bear": {
                "growth_adjustment": -0.03,
                "margin_adjustment": -0.02
            }
        },
        "cash_flow_inputs": {
            "opening_cash_balance": 2500000,
            "weekly_revenue": 350000,
            "collection_rate": 0.85,
            "collection_lag_weeks": 2,
            "weekly_payroll": 160000,
            "weekly_rent": 15000,
            "weekly_operating": 45000,
            "weekly_other": 20000,
            "one_time_items": [
                {"week": 3, "amount": -250000, "description": "Annual insurance premium"},
                {"week": 6, "amount": 500000, "description": "Customer prepayment"},
                {"week": 9, "amount": -180000, "description": "Equipment purchase"},
                {"week": 13, "amount": -75000, "description": "Quarterly tax payment"}
            ]
        }
    }

    result = execute(sample_data)
    print(json.dumps(result, indent=2))
