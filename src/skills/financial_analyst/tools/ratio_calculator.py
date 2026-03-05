"""
Ratio Calculator Tool

Calculate and interpret financial ratios from financial statement data.

Ratio Categories:
- Profitability: ROE, ROA, Gross Margin, Operating Margin, Net Margin
- Liquidity: Current Ratio, Quick Ratio, Cash Ratio
- Leverage: Debt-to-Equity, Interest Coverage, DSCR
- Efficiency: Asset Turnover, Inventory Turnover, Receivables Turnover, DSO
- Valuation: P/E, P/B, P/S, EV/EBITDA, PEG Ratio
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, Optional
from utils import math_helpers
from utils import validators


DESCRIPTION = "Calculate and interpret financial ratios from financial statement data"
REQUIRED_PARAMETERS = ["income_statement", "balance_sheet"]
OPTIONAL_PARAMETERS = ["cash_flow", "market_data", "category"]


def interpret_ratio(ratio_name: str, value: float, benchmark: Optional[Dict[str, float]] = None) -> str:
    """
    Provide interpretation for a ratio value.

    Args:
        ratio_name: Name of the ratio
        value: Calculated ratio value
        benchmark: Optional benchmark values

    Returns:
        Interpretation string
    """
    benchmarks = benchmark or {
        "roe": {"good": 0.15, "average": 0.10},
        "roa": {"good": 0.10, "average": 0.05},
        "gross_margin": {"good": 0.40, "average": 0.25},
        "operating_margin": {"good": 0.15, "average": 0.10},
        "net_margin": {"good": 0.10, "average": 0.05},
        "current_ratio": {"good": 2.0, "average": 1.5},
        "quick_ratio": {"good": 1.5, "average": 1.0},
        "debt_to_equity": {"good": 0.5, "average": 1.0},
        "interest_coverage": {"good": 5.0, "average": 3.0}
    }

    if ratio_name not in benchmarks:
        return "No benchmark available"

    b = benchmarks[ratio_name]
    if value >= b.get("good", float("inf")):
        return "Good - above average performance"
    elif value >= b.get("average", float("inf")):
        return "Acceptable - within normal range"
    else:
        return "Below average - needs attention"


def calculate_profitability_ratios(income_statement: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate profitability ratios.

    Args:
        income_statement: Income statement data

    Returns:
        Dictionary of profitability ratios
    """
    revenue = income_statement.get("revenue", 0)
    cogs = income_statement.get("cost_of_goods_sold", 0)
    operating_income = income_statement.get("operating_income", 0)
    ebitda = income_statement.get("ebitda", 0)
    net_income = income_statement.get("net_income", 0)

    gross_profit = revenue - cogs

    return {
        "roe": {
            "value": 0.0,  # Will be calculated with equity
            "formula": "Net Income / Total Equity",
            "name": "Return on Equity",
            "interpretation": ""
        },
        "roa": {
            "value": 0.0,  # Will be calculated with assets
            "formula": "Net Income / Total Assets",
            "name": "Return on Assets",
            "interpretation": ""
        },
        "gross_margin": {
            "value": math_helpers.safe_divide(gross_profit, revenue),
            "formula": "(Revenue - COGS) / Revenue",
            "name": "Gross Margin",
            "interpretation": interpret_ratio("gross_margin", math_helpers.safe_divide(gross_profit, revenue))
        },
        "operating_margin": {
            "value": math_helpers.safe_divide(operating_income, revenue),
            "formula": "Operating Income / Revenue",
            "name": "Operating Margin",
            "interpretation": interpret_ratio("operating_margin", math_helpers.safe_divide(operating_income, revenue))
        },
        "net_margin": {
            "value": math_helpers.safe_divide(net_income, revenue),
            "formula": "Net Income / Revenue",
            "name": "Net Margin",
            "interpretation": interpret_ratio("net_margin", math_helpers.safe_divide(net_income, revenue))
        }
    }


def calculate_liquidity_ratios(balance_sheet: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate liquidity ratios.

    Args:
        balance_sheet: Balance sheet data

    Returns:
        Dictionary of liquidity ratios
    """
    current_assets = balance_sheet.get("current_assets", 0)
    current_liabilities = balance_sheet.get("current_liabilities", 0)
    cash = balance_sheet.get("cash_and_equivalents", 0)
    receivables = balance_sheet.get("accounts_receivable", 0)
    inventory = balance_sheet.get("inventory", 0)

    current_ratio = math_helpers.safe_divide(current_assets, current_liabilities)
    quick_ratio = math_helpers.safe_divide(current_assets - inventory, current_liabilities)
    cash_ratio = math_helpers.safe_divide(cash, current_liabilities)

    return {
        "current_ratio": {
            "value": current_ratio,
            "name": "Current Ratio",
            "interpretation": interpret_ratio("current_ratio", current_ratio)
        },
        "quick_ratio": {
            "value": quick_ratio,
            "name": "Quick Ratio",
            "interpretation": interpret_ratio("quick_ratio", quick_ratio)
        },
        "cash_ratio": {
            "value": cash_ratio,
            "name": "Cash Ratio",
            "interpretation": "Cash ratio measures immediate liquidity"
        }
    }


def calculate_leverage_ratios(balance_sheet: Dict[str, float],
                              income_statement: Dict[str, float],
                              cash_flow: Optional[Dict[str, float]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Calculate leverage ratios.

    Args:
        balance_sheet: Balance sheet data
        income_statement: Income statement data
        cash_flow: Optional cash flow data

    Returns:
        Dictionary of leverage ratios
    """
    total_debt = balance_sheet.get("total_debt", 0)
    total_equity = balance_sheet.get("total_equity", 0)
    interest_expense = income_statement.get("interest_expense", 0)
    ebitda = income_statement.get("ebitda", 0)

    debt_to_equity = math_helpers.safe_divide(total_debt, total_equity)
    interest_coverage = math_helpers.safe_divide(ebitda, interest_expense)

    # Debt Service Coverage Ratio (DSCR)
    dscr = 0.0
    if cash_flow and cash_flow.get("total_debt_service"):
        operating_cash_flow = cash_flow.get("operating_cash_flow", 0)
        dscr = math_helpers.safe_divide(operating_cash_flow, cash_flow["total_debt_service"])

    return {
        "debt_to_equity": {
            "value": debt_to_equity,
            "name": "Debt-to-Equity Ratio",
            "interpretation": interpret_ratio("debt_to_equity", debt_to_equity)
        },
        "interest_coverage": {
            "value": interest_coverage,
            "name": "Interest Coverage Ratio",
            "interpretation": interpret_ratio("interest_coverage", interest_coverage)
        },
        "dscr": {
            "value": dscr,
            "name": "Debt Service Coverage Ratio",
            "interpretation": "DSCR measures ability to service debt"
        }
    }


def calculate_efficiency_ratios(income_statement: Dict[str, float],
                                 balance_sheet: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate efficiency ratios.

    Args:
        income_statement: Income statement data
        balance_sheet: Balance sheet data

    Returns:
        Dictionary of efficiency ratios
    """
    revenue = income_statement.get("revenue", 0)
    cogs = income_statement.get("cost_of_goods_sold", 0)
    total_assets = balance_sheet.get("total_assets", 0)
    inventory = balance_sheet.get("inventory", 0)
    receivables = balance_sheet.get("accounts_receivable", 0)

    asset_turnover = math_helpers.safe_divide(revenue, total_assets)
    inventory_turnover = math_helpers.safe_divide(cogs, inventory)
    receivables_turnover = math_helpers.safe_divide(revenue, receivables)
    dso = 365 / receivables_turnover if receivables_turnover > 0 else 0

    return {
        "asset_turnover": {
            "value": asset_turnover,
            "name": "Asset Turnover",
            "interpretation": "Measures asset efficiency"
        },
        "inventory_turnover": {
            "value": inventory_turnover,
            "name": "Inventory Turnover",
            "interpretation": "Measures inventory management efficiency"
        },
        "receivables_turnover": {
            "value": receivables_turnover,
            "name": "Receivables Turnover",
            "interpretation": "Measures collection efficiency"
        },
        "dso": {
            "value": dso,
            "name": "Days Sales Outstanding",
            "interpretation": "Average days to collect receivables"
        }
    }


def calculate_valuation_ratios(income_statement: Dict[str, float],
                               balance_sheet: Dict[str, float],
                               market_data: Optional[Dict[str, float]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Calculate valuation ratios.

    Args:
        income_statement: Income statement data
        balance_sheet: Balance sheet data
        market_data: Optional market data

    Returns:
        Dictionary of valuation ratios
    """
    if not market_data:
        return {}

    revenue = income_statement.get("revenue", 0)
    net_income = income_statement.get("net_income", 0)
    ebitda = income_statement.get("ebitda", 0)
    total_equity = balance_sheet.get("total_equity", 0)

    share_price = market_data.get("share_price", 0)
    shares_outstanding = market_data.get("shares_outstanding", 0)
    market_cap = market_data.get("market_cap", share_price * shares_outstanding)
    earnings_growth = market_data.get("earnings_growth_rate", 0)

    # Calculate enterprise value (simplified)
    total_debt = balance_sheet.get("total_debt", 0)
    cash = balance_sheet.get("cash_and_equivalents", 0)
    enterprise_value = market_cap + total_debt - cash

    pe_ratio = math_helpers.safe_divide(market_cap, net_income) if net_income > 0 else 0
    pb_ratio = math_helpers.safe_divide(market_cap, total_equity) if total_equity > 0 else 0
    ps_ratio = math_helpers.safe_divide(market_cap, revenue) if revenue > 0 else 0
    ev_ebitda = math_helpers.safe_divide(enterprise_value, ebitda) if ebitda > 0 else 0
    peg_ratio = math_helpers.safe_divide(pe_ratio, earnings_growth * 100) if earnings_growth > 0 else 0

    return {
        "pe_ratio": {
            "value": pe_ratio,
            "name": "Price-to-Earnings Ratio",
            "interpretation": "P/E ratio indicates market expectations"
        },
        "pb_ratio": {
            "value": pb_ratio,
            "name": "Price-to-Book Ratio",
            "interpretation": "P/B ratio compares market to book value"
        },
        "ps_ratio": {
            "value": ps_ratio,
            "name": "Price-to-Sales Ratio",
            "interpretation": "P/S ratio compares market cap to revenue"
        },
        "ev_ebitda": {
            "value": ev_ebitda,
            "name": "EV/EBITDA",
            "interpretation": "Enterprise value to EBITDA multiple"
        },
        "peg_ratio": {
            "value": peg_ratio,
            "name": "PEG Ratio",
            "interpretation": "P/E adjusted for growth"
        }
    }


def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute ratio calculator.

    Args:
        parameters: Input parameters containing:
            - income_statement: Income statement data
            - balance_sheet: Balance sheet data
            - cash_flow: Optional cash flow data
            - market_data: Optional market data
            - category: Optional category filter

    Returns:
        Dictionary containing calculated ratios
    """
    # Validate input
    is_valid, error = validators.validate_ratio_analysis_input(parameters)
    if not is_valid:
        return {"error": error}

    income_statement = parameters.get("income_statement", {})
    balance_sheet = parameters.get("balance_sheet", {})
    cash_flow = parameters.get("cash_flow", {})
    market_data = parameters.get("market_data", {})
    category_filter = parameters.get("category", "").lower()

    # Calculate ROE and ROA (need both income statement and balance sheet)
    net_income = income_statement.get("net_income", 0)
    total_equity = balance_sheet.get("total_equity", 0)
    total_assets = balance_sheet.get("total_assets", 0)

    # Build results
    results = {
        "categories": {}
    }

    # Calculate all categories
    profitability = calculate_profitability_ratios(income_statement)
    # Update ROE and ROA
    profitability["roe"]["value"] = math_helpers.safe_divide(net_income, total_equity)
    profitability["roe"]["interpretation"] = interpret_ratio("roe", profitability["roe"]["value"])
    profitability["roa"]["value"] = math_helpers.safe_divide(net_income, total_assets)
    profitability["roa"]["interpretation"] = interpret_ratio("roa", profitability["roa"]["value"])

    if category_filter and category_filter != "profitability":
        pass  # Skip profitability if not requested
    else:
        results["categories"]["profitability"] = profitability

    if not category_filter or category_filter == "liquidity":
        results["categories"]["liquidity"] = calculate_liquidity_ratios(balance_sheet)

    if not category_filter or category_filter == "leverage":
        results["categories"]["leverage"] = calculate_leverage_ratios(
            balance_sheet, income_statement, cash_flow
        )

    if not category_filter or category_filter == "efficiency":
        results["categories"]["efficiency"] = calculate_efficiency_ratios(
            income_statement, balance_sheet
        )

    if not category_filter or category_filter == "valuation":
        if market_data:
            results["categories"]["valuation"] = calculate_valuation_ratios(
                income_statement, balance_sheet, market_data
            )

    return results


# For direct CLI execution
if __name__ == "__main__":
    import json

    # Example usage with sample data
    sample_data = {
        "income_statement": {
            "revenue": 50000000,
            "cost_of_goods_sold": 30000000,
            "operating_income": 8000000,
            "ebitda": 10000000,
            "net_income": 5500000,
            "interest_expense": 1200000
        },
        "balance_sheet": {
            "total_assets": 40000000,
            "current_assets": 15000000,
            "cash_and_equivalents": 5000000,
            "accounts_receivable": 6000000,
            "inventory": 3500000,
            "total_equity": 22000000,
            "total_debt": 12000000,
            "current_liabilities": 8000000
        },
        "cash_flow": {
            "operating_cash_flow": 7500000,
            "total_debt_service": 3000000
        },
        "market_data": {
            "share_price": 45.00,
            "shares_outstanding": 10000000,
            "market_cap": 450000000,
            "earnings_growth_rate": 0.12
        }
    }

    result = execute(sample_data)
    print(json.dumps(result, indent=2))
