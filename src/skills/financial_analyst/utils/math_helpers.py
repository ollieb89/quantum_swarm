"""
Math Helpers - Replicate financial math functions without numpy/pandas

Provides essential financial calculation functions using only Python standard library.
"""

import math
from typing import List, Optional, Tuple


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: The numerator
        denominator: The denominator
        default: Value to return if denominator is zero (default: 0.0)

    Returns:
        Result of division or default value
    """
    if denominator == 0:
        return default
    return numerator / denominator


def calculate_npv(rate: float, cash_flows: List[float], initial_investment: float = 0) -> float:
    """
    Calculate Net Present Value (NPV) using the discounting method.

    NPV = sum(CF_t / (1 + r)^t) - initial_investment

    Args:
        rate: Discount rate (e.g., 0.10 for 10%)
        cash_flows: List of future cash flows (CF_1, CF_2, ..., CF_n)
        initial_investment: Initial investment amount (default: 0)

    Returns:
        Net Present Value
    """
    npv = -initial_investment
    for t, cf in enumerate(cash_flows, start=1):
        npv += cf / ((1 + rate) ** t)
    return npv


def calculate_pv(rate: float, cash_flows: List[float]) -> float:
    """
    Calculate Present Value of cash flows (without initial investment).

    Args:
        rate: Discount rate
        cash_flows: List of future cash flows

    Returns:
        Present Value
    """
    pv = 0
    for t, cf in enumerate(cash_flows, start=1):
        pv += cf / ((1 + rate) ** t)
    return pv


def calculate_cagr(start_value: float, end_value: float, periods: int) -> float:
    """
    Calculate Compound Annual Growth Rate (CAGR).

    CAGR = (End Value / Start Value)^(1/periods) - 1

    Args:
        start_value: Starting value
        end_value: Ending value
        periods: Number of periods (years)

    Returns:
        CAGR as a decimal (e.g., 0.10 for 10%)
    """
    if start_value == 0 or periods <= 0:
        return 0.0
    return (end_value / start_value) ** (1 / periods) - 1


def calculate_mean(values: List[float]) -> float:
    """
    Calculate arithmetic mean.

    Args:
        values: List of numeric values

    Returns:
        Mean value
    """
    if not values:
        return 0.0
    return sum(values) / len(values)


def calculate_median(values: List[float]) -> float:
    """
    Calculate median value.

    Args:
        values: List of numeric values

    Returns:
        Median value
    """
    if not values:
        return 0.0

    sorted_values = sorted(values)
    n = len(sorted_values)

    if n % 2 == 0:
        return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
    else:
        return sorted_values[n // 2]


def calculate_std_dev(values: List[float]) -> float:
    """
    Calculate standard deviation.

    Args:
        values: List of numeric values

    Returns:
        Standard deviation
    """
    if len(values) < 2:
        return 0.0

    mean = calculate_mean(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def calculate_linear_regression(values: List[float]) -> Tuple[float, float, float]:
    """
    Perform simple linear regression using least squares method.

    Args:
        values: List of y-values (dependent variable)
                x-values are assumed to be 0, 1, 2, ..., n-1

    Returns:
        Tuple of (slope, intercept, r_squared)
    """
    n = len(values)
    if n < 2:
        return 0.0, values[0] if values else 0.0, 0.0

    # Calculate means
    x_mean = (n - 1) / 2  # Mean of 0, 1, 2, ..., n-1
    y_mean = calculate_mean(values)

    # Calculate slope and intercept
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0, y_mean, 0.0

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    # Calculate R-squared
    ss_res = sum((y - (slope * i + intercept)) ** 2 for i, y in enumerate(values))
    ss_tot = sum((y - y_mean) ** 2 for y in values)

    if ss_tot == 0:
        r_squared = 1.0 if ss_res == 0 else 0.0
    else:
        r_squared = 1 - (ss_res / ss_tot)

    return slope, intercept, r_squared


def calculate_growth_rate(previous: float, current: float) -> float:
    """
    Calculate period-over-period growth rate.

    Args:
        previous: Previous period value
        current: Current period value

    Returns:
        Growth rate as decimal (e.g., 0.10 for 10%)
    """
    if previous == 0:
        return 0.0
    return (current - previous) / previous


def calculate_average_growth_rate(values: List[float]) -> float:
    """
    Calculate average compound growth rate across periods.

    Args:
        values: List of values over time

    Returns:
        Average growth rate
    """
    if len(values) < 2:
        return 0.0

    # Calculate geometric mean of individual growth rates
    growth_rates = []
    for i in range(1, len(values)):
        rate = calculate_growth_rate(values[i - 1], values[i])
        if rate > -1:  # Exclude invalid negative growth beyond -100%
            growth_rates.append(1 + rate)

    if not growth_rates:
        return 0.0

    # Geometric mean
    product = 1.0
    for rate in growth_rates:
        product *= rate

    return product ** (1 / len(growth_rates)) - 1


def calculate_wacc(cost_of_equity: float, cost_of_debt: float,
                   equity_weight: float, debt_weight: float,
                   tax_rate: float = 0.0) -> float:
    """
    Calculate Weighted Average Cost of Capital (WACC).

    WACC = (E/V * Re) + (D/V * Rd * (1 - Tc))

    Args:
        cost_of_equity: Cost of equity (Re)
        cost_of_debt: Cost of debt (Rd)
        equity_weight: Weight of equity (E/V)
        debt_weight: Weight of debt (D/V)
        tax_rate: Corporate tax rate (Tc)

    Returns:
        WACC as decimal
    """
    return (equity_weight * cost_of_debt) + (debt_weight * cost_of_debt * (1 - tax_rate))


def calculate_capm(risk_free_rate: float, equity_risk_premium: float, beta: float) -> float:
    """
    Calculate Cost of Equity using Capital Asset Pricing Model (CAPM).

    Re = Rf + Beta * (Rm - Rf)

    Args:
        risk_free_rate: Risk-free rate (Rf)
        equity_risk_premium: Market risk premium (Rm - Rf)
        beta: Beta coefficient

    Returns:
        Cost of equity
    """
    return risk_free_rate + beta * equity_risk_premium


def round_value(value: float, decimals: int = 4) -> float:
    """
    Round a value to specified decimal places.

    Args:
        value: Value to round
        decimals: Number of decimal places

    Returns:
        Rounded value
    """
    return round(value, decimals)
