"""
Budget Variance Analyzer Tool

Analyze actual vs budget vs prior year performance with materiality filtering.

Features:
- Dollar and percentage variance calculation
- Materiality threshold filtering (default: 10% or $50K)
- Favorable/unfavorable classification with revenue/expense logic
- Department and category breakdown
- Executive summary generation
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, List, Optional
from utils import math_helpers
from utils import validators


DESCRIPTION = "Analyze actual vs budget vs prior year performance with materiality filtering"
REQUIRED_PARAMETERS = ["line_items"]
OPTIONAL_PARAMETERS = ["company", "period", "threshold_pct", "threshold_amt"]


DEFAULT_THRESHOLD_PCT = 0.10  # 10%
DEFAULT_THRESHOLD_AMT = 50000  # $50,000


def calculate_variance(actual: float, budget: float, item_type: str) -> Dict[str, Any]:
    """
    Calculate budget variance for a single item.

    Args:
        actual: Actual amount
        budget: Budgeted amount
        item_type: "revenue" or "expense"

    Returns:
        Dictionary with variance calculations
    """
    variance_amount = actual - budget
    variance_pct = math_helpers.safe_divide(variance_amount, budget) if budget != 0 else 0

    # Determine favorability
    # Revenue: higher actual = favorable
    # Expense: lower actual = favorable
    if item_type == "revenue":
        is_favorable = variance_amount >= 0
    else:
        is_favorable = variance_amount <= 0

    return {
        "actual": actual,
        "budget": budget,
        "variance_amount": variance_amount,
        "variance_pct": variance_pct,
        "is_favorable": is_favorable,
        "favorability": "Favorable" if is_favorable else "Unfavorable"
    }


def calculate_yoy_variance(actual: float, prior_year: float, item_type: str) -> Dict[str, Any]:
    """
    Calculate year-over-year variance.

    Args:
        actual: Actual amount
        prior_year: Prior year amount
        item_type: "revenue" or "expense"

    Returns:
        Dictionary with YoY variance calculations
    """
    yoy_amount = actual - prior_year
    yoy_pct = math_helpers.safe_divide(yoy_amount, prior_year) if prior_year != 0 else 0

    # Determine favorability
    if item_type == "revenue":
        is_favorable = yoy_amount >= 0
    else:
        is_favorable = yoy_amount <= 0

    return {
        "prior_year": prior_year,
        "yoy_amount": yoy_amount,
        "yoy_pct": yoy_pct,
        "is_favorable": is_favorable,
        "favorability": "Favorable" if is_favorable else "Unfavorable"
    }


def is_material(variance_amount: float, variance_pct: float,
                threshold_pct: float, threshold_amt: float) -> bool:
    """
    Determine if a variance is material based on thresholds.

    Args:
        variance_amount: Dollar variance
        variance_pct: Percentage variance
        threshold_pct: Percentage threshold
        threshold_amt: Dollar threshold

    Returns:
        True if variance is material
    """
    # Material if either threshold is exceeded
    return abs(variance_pct) >= threshold_pct or abs(variance_amount) >= threshold_amt


def aggregate_by_department(line_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate variances by department.

    Args:
        line_items: List of line items with variance data

    Returns:
        Dictionary of department summaries
    """
    dept_summaries = {}

    for item in line_items:
        dept = item.get("department", "Unknown")
        variance = item.get("budget_variance_amount", 0)

        if dept not in dept_summaries:
            dept_summaries[dept] = {
                "total_variance": 0,
                "variance_pct": 0,
                "item_count": 0,
                "favorable_count": 0,
                "unfavorable_count": 0
            }

        dept_summaries[dept]["total_variance"] += variance
        dept_summaries[dept]["item_count"] += 1

        if item.get("is_favorable", True):
            dept_summaries[dept]["favorable_count"] += 1
        else:
            dept_summaries[dept]["unfavorable_count"] += 1

    # Calculate variance percentages
    for dept, summary in dept_summaries.items():
        # Use absolute values for percentage calculation
        total_actual = sum(item.get("actual", 0) for item in line_items
                         if item.get("department") == dept)
        summary["variance_pct"] = math_helpers.safe_divide(
            summary["total_variance"],
            total_actual - summary["total_variance"]
        ) if total_actual != summary["total_variance"] else 0

    return dept_summaries


def aggregate_by_category(line_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate variances by category.

    Args:
        line_items: List of line items with variance data

    Returns:
        Dictionary of category summaries
    """
    cat_summaries = {}

    for item in line_items:
        category = item.get("category", "Unknown")
        variance = item.get("budget_variance_amount", 0)

        if category not in cat_summaries:
            cat_summaries[category] = {
                "total_variance": 0,
                "variance_pct": 0,
                "item_count": 0,
                "favorable_count": 0,
                "unfavorable_count": 0
            }

        cat_summaries[category]["total_variance"] += variance
        cat_summaries[category]["item_count"] += 1

        if item.get("is_favorable", True):
            cat_summaries[category]["favorable_count"] += 1
        else:
            cat_summaries[category]["unfavorable_count"] += 1

    # Calculate variance percentages
    for cat, summary in cat_summaries.items():
        total_actual = sum(item.get("actual", 0) for item in line_items
                         if item.get("category") == cat)
        summary["variance_pct"] = math_helpers.safe_divide(
            summary["total_variance"],
            total_actual - summary["total_variance"]
        ) if total_actual != summary["total_variance"] else 0

    return cat_summaries


def generate_executive_summary(line_items: List[Dict[str, Any]],
                               company: str,
                               period: str) -> Dict[str, Any]:
    """
    Generate executive summary of variance analysis.

    Args:
        line_items: List of analyzed line items
        company: Company name
        period: Reporting period

    Returns:
        Executive summary dictionary
    """
    # Separate revenue and expense items
    revenue_items = [item for item in line_items if item.get("type") == "revenue"]
    expense_items = [item for item in line_items if item.get("type") == "expense"]

    # Calculate totals
    total_revenue_actual = sum(item.get("actual", 0) for item in revenue_items)
    total_revenue_budget = sum(item.get("budget", 0) for item in revenue_items)
    revenue_variance = total_revenue_actual - total_revenue_budget
    revenue_variance_pct = math_helpers.safe_divide(revenue_variance, total_revenue_budget)

    total_expense_actual = sum(item.get("actual", 0) for item in expense_items)
    total_expense_budget = sum(item.get("budget", 0) for item in expense_items)
    expense_variance = total_expense_actual - total_expense_budget
    expense_variance_pct = math_helpers.safe_divide(expense_variance, total_expense_budget)

    # Calculate net impact (Revenue variance - Expense variance)
    # Note: Expense variance is positive when over budget (unfavorable)
    net_impact = revenue_variance - expense_variance

    # Count favorable/unfavorable
    favorable_count = sum(1 for item in line_items if item.get("is_favorable", False))
    unfavorable_count = len(line_items) - favorable_count

    # Count material variances
    material_variances = [item for item in line_items if item.get("is_material", False)]

    return {
        "period": period,
        "company": company,
        "total_line_items": len(line_items),
        "material_variances_count": len(material_variances),
        "favorable_count": favorable_count,
        "unfavorable_count": unfavorable_count,
        "revenue": {
            "actual": total_revenue_actual,
            "budget": total_revenue_budget,
            "variance_amount": revenue_variance,
            "variance_pct": revenue_variance_pct
        },
        "expenses": {
            "actual": total_expense_actual,
            "budget": total_expense_budget,
            "variance_amount": expense_variance,
            "variance_pct": expense_variance_pct
        },
        "net_impact": net_impact
    }


def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute budget variance analysis.

    Args:
        parameters: Input parameters containing:
            - line_items: List of line items with actual, budget, prior year values
            - company: Company name (optional)
            - period: Reporting period (optional)
            - threshold_pct: Materiality threshold percentage (optional)
            - threshold_amt: Materiality threshold dollar amount (optional)

    Returns:
        Dictionary containing variance analysis results
    """
    # Validate input
    is_valid, error = validators.validate_budget_variance_input(parameters)
    if not is_valid:
        return {"error": error}

    line_items = parameters.get("line_items", [])
    company = parameters.get("company", "Company")
    period = parameters.get("period", "Period")
    threshold_pct = parameters.get("threshold_pct", DEFAULT_THRESHOLD_PCT)
    threshold_amt = parameters.get("threshold_amt", DEFAULT_THRESHOLD_AMT)

    # Process each line item
    analyzed_items = []

    for item in line_items:
        name = item.get("name", "Unknown")
        item_type = item.get("type", "expense")
        actual = item.get("actual", 0)
        budget = item.get("budget", 0)
        prior_year = item.get("prior_year")

        # Calculate budget variance
        budget_variance = calculate_variance(actual, budget, item_type)

        # Calculate YoY variance if prior year data exists
        yoy_variance = {}
        if prior_year is not None:
            yoy_variance = calculate_yoy_variance(actual, prior_year, item_type)

        # Determine materiality
        material = is_material(
            budget_variance["variance_amount"],
            budget_variance["variance_pct"],
            threshold_pct,
            threshold_amt
        )

        # Build analyzed item
        analyzed_item = {
            "name": name,
            "type": item_type,
            "department": item.get("department"),
            "category": item.get("category"),
            "actual": actual,
            "budget": budget,
            "budget_variance_amount": budget_variance["variance_amount"],
            "budget_variance_pct": budget_variance["variance_pct"],
            "is_favorable": budget_variance["is_favorable"],
            "favorability": budget_variance["favorability"],
            "is_material": material
        }

        # Add YoY data if available
        if yoy_variance:
            analyzed_item["prior_year"] = prior_year
            analyzed_item["yoy_amount"] = yoy_variance["yoy_amount"]
            analyzed_item["yoy_pct"] = yoy_variance["yoy_pct"]

        analyzed_items.append(analyzed_item)

    # Get material variances only
    material_variances = [item for item in analyzed_items if item["is_material"]]

    # Generate summaries
    department_summary = aggregate_by_department(analyzed_items)
    category_summary = aggregate_by_category(analyzed_items)

    # Generate executive summary
    executive_summary = generate_executive_summary(analyzed_items, company, period)

    # Build results
    results = {
        "executive_summary": executive_summary,
        "material_variances": material_variances,
        "department_summary": department_summary,
        "category_summary": category_summary,
        "all_items": analyzed_items,
        "thresholds_used": {
            "percentage": threshold_pct,
            "amount": threshold_amt
        }
    }

    return results


# For direct CLI execution
if __name__ == "__main__":
    import json

    # Example usage with sample data
    sample_data = {
        "company": "Acme Corp",
        "period": "Q4 2025",
        "line_items": [
            {
                "name": "Product Revenue",
                "type": "revenue",
                "department": "Sales",
                "category": "Revenue",
                "actual": 12500000,
                "budget": 12000000,
                "prior_year": 10800000
            },
            {
                "name": "Service Revenue",
                "type": "revenue",
                "department": "Sales",
                "category": "Revenue",
                "actual": 3200000,
                "budget": 3500000,
                "prior_year": 2900000
            },
            {
                "name": "Cost of Goods Sold",
                "type": "expense",
                "department": "Operations",
                "category": "COGS",
                "actual": 7800000,
                "budget": 7200000,
                "prior_year": 6700000
            },
            {
                "name": "Salaries & Wages",
                "type": "expense",
                "department": "Human Resources",
                "category": "Personnel",
                "actual": 2100000,
                "budget": 2200000,
                "prior_year": 1950000
            },
            {
                "name": "Marketing & Advertising",
                "type": "expense",
                "department": "Marketing",
                "category": "Sales & Marketing",
                "actual": 850000,
                "budget": 750000,
                "prior_year": 680000
            },
            {
                "name": "Software & Technology",
                "type": "expense",
                "department": "Engineering",
                "category": "Technology",
                "actual": 420000,
                "budget": 400000,
                "prior_year": 350000
            },
            {
                "name": "Office & Facilities",
                "type": "expense",
                "department": "Operations",
                "category": "G&A",
                "actual": 180000,
                "budget": 200000,
                "prior_year": 175000
            },
            {
                "name": "Travel & Entertainment",
                "type": "expense",
                "department": "Sales",
                "category": "Sales & Marketing",
                "actual": 95000,
                "budget": 120000,
                "prior_year": 88000
            },
            {
                "name": "Professional Services",
                "type": "expense",
                "department": "Finance",
                "category": "G&A",
                "actual": 310000,
                "budget": 250000,
                "prior_year": 220000
            },
            {
                "name": "R&D Expenses",
                "type": "expense",
                "department": "Engineering",
                "category": "R&D",
                "actual": 1500000,
                "budget": 1400000,
                "prior_year": 1200000
            }
        ]
    }

    result = execute(sample_data)
    print(json.dumps(result, indent=2))
